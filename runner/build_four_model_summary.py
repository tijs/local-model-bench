"""Validate fresh selected cohorts and export quality/cost figures and summary."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bench_common import REPO
from build_agent_leaderboard import render_campaign, within_resource_policy
from matplotlib.lines import Line2D

GIB = 1024**3
COLORS = {
    "Base Qwen3.6": "#2378b5",
    "Ornith1.5": "#c87918",
    "Groot": "#138675",
    "Logics-SWE": "#8554a4",
}
MARKERS = {"mei": "o", "llama.cpp": "D"}
ENGINES = {"mei": "Mei (Swift/MLX)", "llama.cpp": "llama.cpp (GGUF)"}


@dataclass(frozen=True)
class Point:
    label: str
    engine: str
    seed: int
    household: int
    python: int
    wall_minutes: float
    wired_increase_gib: float | None
    baseline_wired_gib: float
    peak_host_wired_gib: float
    weight_gib: float
    household_run: str
    python_run: str
    supervision: str


@dataclass(frozen=True)
class ModelAverage:
    label: str
    engine: str
    runs: int
    seeds: tuple[int, ...]
    run_weights: tuple[float, ...]
    household_passed: int
    household_attempts: int
    household_success_percent: float
    python_passed: int
    python_attempts: int
    python_success_percent: float
    wall_minutes: float
    wired_increase_gib: float | None
    weight_gib: float


def aggregate_points(points: list[Point]) -> list[ModelAverage]:
    """Pool task success; equally weight the two complete, equal-coverage runs."""
    if len(points) != 8 or {p.label for p in points} != set(COLORS):
        raise ValueError("Averages require all eight selected latest-release runs")
    averages = []
    for label in COLORS:
        group = sorted((p for p in points if p.label == label), key=lambda p: p.seed)
        if [p.seed for p in group] != [17, 29]:
            raise ValueError("Averages require exactly one run for each declared seed")
        if (
            len({p.engine for p in group}) != 1
            or len({p.weight_gib for p in group}) != 1
        ):
            raise ValueError("Averages cannot combine different serving profiles")
        house = sum(p.household for p in group)
        python = sum(p.python for p in group)
        memory = [p.wired_increase_gib for p in group]
        averages.append(
            ModelAverage(
                label=label,
                engine=group[0].engine,
                runs=len(group),
                seeds=tuple(p.seed for p in group),
                run_weights=(0.5, 0.5),
                household_passed=house,
                household_attempts=12 * len(group),
                household_success_percent=100 * house / (12 * len(group)),
                python_passed=python,
                python_attempts=3 * len(group),
                python_success_percent=100 * python / (3 * len(group)),
                wall_minutes=fmean(p.wall_minutes for p in group),
                # Missing memory in either run must not silently reweight the other.
                wired_increase_gib=None
                if None in memory
                else fmean(x for x in memory if x is not None),
                weight_gib=group[0].weight_gib,
            )
        )
    return averages


def wired_bytes(sample: dict[str, Any]) -> int:
    text = sample["host_vm_stat"]
    page = re.search(r"page size of (\d+) bytes", text)
    wired = re.search(r"Pages wired down:\s+(\d+)\.", text)
    if not page or not wired:
        raise ValueError("Missing recorded VM page size/wired counter")
    return int(page[1]) * int(wired[1])


def memory_cost(
    baseline: list[dict[str, Any]], samples: list[dict[str, Any]]
) -> tuple[float, float, float | None]:
    if not baseline or not samples:
        raise ValueError("Memory figures require both baseline and run samples")
    base = median(wired_bytes(x) for x in baseline) / GIB
    peak = max(wired_bytes(x) for x in samples) / GIB
    # A negative host delta is background variation, not a zero-cost model.
    delta = peak - base
    return base, peak, delta if delta >= 0 else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def load_points(root: Path, specification: dict[str, Any]) -> list[Point]:
    labels = specification["models"]
    if (
        len(labels) != 4
        or set(specification["seeds"]) != {17, 29}
        or len(specification["cohorts"]) != 2
    ):
        raise ValueError("Require four retained profiles and two declared seed cohorts")
    points = []
    seen = set()
    runtime_ids: dict[str, dict[str, Any]] = {}
    for path in specification["cohorts"]:
        cohort = json.loads((root / path).read_text())
        if (
            cohort["benchmark_release"] != specification["benchmark_release"]
            or cohort["release_commit"] != specification["release_commit"]
            or cohort["trials"] != 1
        ):
            raise ValueError("Cohorts must use the same frozen released method")
        render_campaign(
            root, cohort
        )  # Full source/config/coverage/resource provenance validation.
        if {x["model"] for x in cohort["models"]} != set(labels):
            raise ValueError("Cohort is missing a requested contender")
        for entry in cohort["models"]:
            label = labels[entry["model"]]
            if label not in COLORS or entry["engine"] not in ENGINES:
                raise ValueError("Unknown model/engine label")
            tracks = []
            manifests = []
            for folder, key in (
                ("standin", "household_run"),
                ("automation", "python_run"),
            ):
                directory = root / "results" / folder / "runs" / entry[key]
                manifest = json.loads((directory / "manifest.json").read_text())
                if manifest["status"] != "completed":
                    raise ValueError(
                        "Partial/unadmitted runs cannot become completed plot points"
                    )
                rows = [
                    x
                    for x in read_jsonl(root / "results" / folder / "log.jsonl")
                    if x["run_id"] == entry[key]
                ]
                expected = 12 if folder == "standin" else 3
                if len(rows) != expected or any(x.get("harness_error") for x in rows):
                    raise ValueError("Incomplete/unusable task coverage")
                if folder == "standin" and any(
                    x.get("critical_safety_failure") for x in rows
                ):
                    raise ValueError(
                        "Critical boundary failure cannot be plotted as a qualified point"
                    )
                tracks.append(sum(x["pass"] for x in rows))
                manifests.append(manifest)
            seed = manifests[0]["generation_overrides"]["seed"]
            if (
                seed not in specification["seeds"]
                or manifests[1]["generation_overrides"]["seed"] != seed
                or (entry["model"], seed) in seen
            ):
                raise ValueError("Missing, duplicate or mismatched seed")
            seen.add((entry["model"], seed))
            identity = manifests[0]["runtime_identity"]
            if identity != manifests[1]["runtime_identity"]:
                raise ValueError("Tracks differ in runtime identity")
            previous = runtime_ids.setdefault(entry["model"], identity)
            if previous != identity:
                raise ValueError("A contender changed binary/runtime between seeds")
            directory = root / entry["supervision"]
            outcome = json.loads((directory / "outcome.json").read_text())
            if outcome["returncode"] != 0 or outcome["stop_reason"] is not None:
                raise ValueError(
                    "Interrupted supervisor cannot yield a qualified point"
                )
            baseline = read_jsonl(directory / "baseline.jsonl")
            samples = read_jsonl(directory / "resources.jsonl")
            import yaml

            cfg = yaml.safe_load((root / entry["config"]).read_text())
            initial = json.loads((directory / "invocation.json").read_text())["initial"]
            if not within_resource_policy(
                samples,
                initial,
                capacity=cfg.get("resource_monitor_policy", {}).get("admission_mode")
                == "capacity",
            ):
                raise ValueError("Resource-ineligible run cannot be a qualified point")
            base, peak, delta = memory_cost(baseline, samples)
            points.append(
                Point(
                    label,
                    entry["engine"],
                    seed,
                    tracks[0],
                    tracks[1],
                    outcome["elapsed_seconds"] / 60,
                    delta,
                    base,
                    peak,
                    cfg["model_bytes"] / GIB,
                    entry["household_run"],
                    entry["python_run"],
                    entry["supervision"],
                )
            )
    if seen != {(model, seed) for model in labels for seed in specification["seeds"]}:
        raise ValueError("Not all eight predeclared observations are present")
    return sorted(points, key=lambda x: (list(COLORS).index(x.label), x.seed))


def figures(
    points: list[ModelAverage], output: Path, title_prefix: str = ""
) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    names = []
    # Offsets move labels, never observations. Leader lines retain the exact
    # position of the tightly clustered memory measurements.
    memory_labels = {
        "Base Qwen3.6": (-130, -25),
        "Ornith1.5": (18, 10),
        "Groot": (8, 10),
        "Logics-SWE": (-100, 15),
    }
    for metric, xlabel, name in (
        (
            "wall_minutes",
            "Average full 15-task run time (minutes) · lower is better",
            "quality-time",
        ),
        (
            "wired_increase_gib",
            "Average per-run peak host wired increase (GiB) · lower is better",
            "quality-memory",
        ),
    ):
        fig, ax = plt.subplots(figsize=(10.5, 6.5), layout="constrained")
        for point in points:
            x = getattr(point, metric)
            if x is None:
                continue
            y = point.household_success_percent
            ax.scatter(
                x,
                y,
                s=110,
                facecolors="none",
                marker=MARKERS[point.engine],
                edgecolors=COLORS[point.label],
                linewidths=1.8,
                zorder=3,
            )
            offset = (
                memory_labels[point.label]
                if metric == "wired_increase_gib"
                else (7, -17)
                if point.label == "Ornith1.5"
                else (7, 9)
            )
            ax.annotate(
                point.label,
                (x, y),
                xytext=offset,
                textcoords="offset points",
                fontsize=8,
                color=COLORS[point.label],
                arrowprops={"arrowstyle": "-", "color": COLORS[point.label], "lw": 0.65}
                if metric == "wired_increase_gib"
                else None,
            )
        ax.set_title(
            title_prefix + "Household task quality versus resource cost",
            loc="left",
            fontweight="bold",
            pad=14,
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Household task success (%) · 24 attempts across two runs")
        ax.set_ylim(-5, 110)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.margins(x=0.2)
        ax.grid(alpha=0.18)
        legend = [
            Line2D(
                [],
                [],
                color="#555",
                marker=MARKERS[k],
                markerfacecolor="none",
                linestyle="none",
                markersize=8,
                label=v,
            )
            for k, v in ENGINES.items()
        ]
        ax.legend(handles=legend, loc="lower left", frameon=False)
        note = "One point per model: latest v9.10 repeats, 50% weight each. Quality pools task attempts; costs average runs."
        if metric == "wired_increase_gib":
            note += "\nMean of per-run (host peak minus median baseline); partial system-wide accounting, not exact model RAM."
        fig.text(0.01, -0.035, note, fontsize=8, color="#555")
        for extension in ("png", "svg"):
            fig.savefig(output / f"{name}.{extension}", dpi=180, bbox_inches="tight")
        plt.close(fig)
        names.append(name)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, field, title in zip(
        axes,
        ("household_success_percent", "python_success_percent"),
        ("Household quality", "Python automation quality"),
        strict=True,
    ):
        for i, p in enumerate(points):
            value = getattr(p, field)
            ax.scatter(
                i, value, c=COLORS[p.label], marker=MARKERS[p.engine], s=90, zorder=3
            )
            ax.annotate(
                f"{value:.1f}%",
                (i, value),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
        ax.set_xticks(range(4), list(COLORS), rotation=18)
        ax.set_ylim(-3, 113)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_ylabel("Task success (%) across both repeats")
        ax.set_title(title_prefix + title, loc="left", fontweight="bold")
        ax.grid(axis="y", alpha=0.18)
    fig.text(
        0.01,
        -0.05,
        "Latest v9.10 repeats, 50% weight each; quality tracks remain separate. Circles: Mei; diamonds: llama.cpp.",
        fontsize=8,
    )
    for extension in ("png", "svg"):
        fig.savefig(
            output / f"quality-tracks.{extension}", dpi=180, bbox_inches="tight"
        )
    plt.close(fig)
    return [*names, "quality-tracks"]


def export(root: Path, spec: dict[str, Any], summary: Path, output: Path) -> None:
    points = load_points(root, spec)
    averages = aggregate_points(points)
    names = figures(averages, output)
    data = [asdict(p) for p in points]
    (output / "metrics.json").write_text(
        json.dumps(
            {
                "specification": spec,
                "observations": data,
                "model_averages": [asdict(p) for p in averages],
                "aggregation": {
                    "scope": "Only the explicitly selected complete runs on the frozen benchmark release",
                    "quality": "Total passed / total task attempts, separately for household and Python",
                    "costs": "Equal-weight mean of full-run time and per-run peak wired increase; both runs have identical coverage",
                    "run_weights": {"17": 0.5, "29": 0.5},
                    "missing_memory": "Unavailable if either selected run lacks a usable memory delta",
                },
                "report_program_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    with (output / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    with (output / "model-averages.csv").open("w", newline="") as stream:
        rows = [asdict(p) for p in averages]
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    relative = output.relative_to(summary.parent)
    lines = [
        "# Four-model local agent comparison",
        "",
        f"Frozen benchmark **{spec['benchmark_release']}**; two fresh declared seeds per profile, eight complete runs.",
        "",
        "All four remain retained contenders. These compare serving profiles, not pure model weights or Peixinho application acceptance.",
        "",
        "Each graph shows one weighted-average point per model, using only its two fresh v9.10 repeats. Each run has identical coverage and receives 50% weight. Quality pools task attempts separately for household and Python; time and memory are means across runs. Individual observations remain below.",
        "",
    ]
    for name in names:
        lines.extend([f"![{name.replace('-', ' ')}]({relative}/{name}.png)", ""])
    lines.extend(
        [
            "## Model averages",
            "",
            "| Model / engine | Household | Python | Average full time | Average peak wired increase |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for p in averages:
        memory = (
            "unavailable"
            if p.wired_increase_gib is None
            else f"{p.wired_increase_gib:.2f} GiB"
        )
        lines.append(
            f"| {p.label} / {ENGINES[p.engine]} | {p.household_passed}/{p.household_attempts} ({p.household_success_percent:.1f}%) | {p.python_passed}/{p.python_attempts} ({p.python_success_percent:.1f}%) | {p.wall_minutes:.2f} min | {memory} |"
        )
    lines.extend(
        [
            "",
            "## Individual run evidence",
            "",
            "| Model / engine | Seed | Household | Python | Full time | Wired increase (GiB) | Weight storage (GiB) | Audit |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for p in points:
        memory = (
            "unavailable"
            if p.wired_increase_gib is None
            else f"{p.wired_increase_gib:.2f}"
        )
        lines.append(
            f"| {p.label} / {ENGINES[p.engine]} | {p.seed} | {p.household}/12 | {p.python}/3 | {p.wall_minutes:.2f} min | {memory} | {p.weight_gib:.2f} | [review](../{p.supervision}/README.md) |"
        )
    lines.extend(
        [
            "",
            "## Reading the costs and quality",
            "",
            "Time includes startup/native admission and both tracks, excluding the separate 30-second baseline. Memory is the peak observed system-wide wired-byte increase over median baseline; background activity can affect it. It is partial accounting, not total model memory. GPU allocations are not reliably captured by process RSS/footprint. Weight storage is separate; no counters are added together.",
            "",
            "The graph averages the two per-run peak memory increases; it is not the maximum across both runs. Each repeat has 12 household and 3 Python tasks, so pooled task weighting gives each run 50% weight. All attempts, including failed tasks and missing script submissions, count. There is no weighting by success, response count, tokens, telemetry sample count or duration, and no composite quality score. Two repeats do not establish independence or statistical superiority.",
            "",
            "Qwen/Ornith retain their T0.6 sampler; Groot/Logics retain T1 and their declared penalties. Quants, engines and cache settings differ explicitly. No best-run selection or universal winner is implied.",
            "",
            "## Provenance and failures",
            "",
        ]
    )
    for path in spec["cohorts"]:
        cohort = json.loads((root / path).read_text())
        seed = json.loads(
            (
                root
                / "results/standin/runs"
                / cohort["models"][0]["household_run"]
                / "manifest.json"
            ).read_text()
        )["generation_overrides"]["seed"]
        report = spec["benchmark_release"].replace("benchmark-", "").upper()
        lines.extend(
            [
                f"- Seed {seed}: [validated report](FOUR_MODEL_{report}_SEED{seed}.md), [exact selection](../{path}).",
            ]
        )
    lines.extend(
        [
            "",
            "Each per-run review records the frozen grade/tool-journal audit, submitted-script replay and missing submissions. Execution replay is not applicable when no script was submitted. Denied attempts and invalid calls still fail their tasks, even when containment holds or a corrected script later works.",
            "",
            "All eight selected supervisors exited normally. The linked cohort reports retain pressure, swap and disk eligibility; each audit retains post-run model/runtime hashes and owned-cache cleanup receipts. These short tasks do not establish near-64K quality or maximum context capacity.",
            "",
            "[Interpretation, failed checks and serving profiles](../docs/FOUR_MODEL_COMPARISON.md) · [Original v9.9 attempts](FOUR_MODEL_V9.9_INTERRUPTED.md) · [Historical v8.3.1 summary](AGENT_SUMMARY_V8.3.1.md).",
        ]
    )
    lines.extend(
        [
            "[Metric data]("
            + str(relative)
            + "/metrics.json) · [CSV]("
            + str(relative)
            + "/metrics.csv) · [Model averages]("
            + str(relative)
            + "/model-averages.csv). PNG and SVG exports are kept beside the data.",
            "",
        ]
    )
    summary.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument(
        "--summary", type=Path, default=REPO / "results/AGENT_SUMMARY.md"
    )
    parser.add_argument(
        "--figures", type=Path, default=REPO / "results/charts/four-model-v9.10"
    )
    args = parser.parse_args()
    export(
        REPO,
        json.loads(args.spec.read_text()),
        args.summary.resolve(),
        args.figures.resolve(),
    )


if __name__ == "__main__":
    main()

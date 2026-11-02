"""Validate fresh selected cohorts and export quality/cost figures and summary."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bench_common import REPO
from build_agent_leaderboard import render_campaign
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
            base, peak, delta = memory_cost(
                read_jsonl(directory / "baseline.jsonl"),
                read_jsonl(directory / "resources.jsonl"),
            )
            import yaml

            cfg = yaml.safe_load((root / entry["config"]).read_text())
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


def figures(points: list[Point], output: Path, title_prefix: str = "") -> list[str]:
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
    for metric, xlabel, name in (
        (
            "wall_minutes",
            "Full 15-task run time (minutes) · lower is better",
            "quality-time",
        ),
        (
            "wired_increase_gib",
            "Peak host wired-memory increase (GiB) · lower is better",
            "quality-memory",
        ),
    ):
        fig, ax = plt.subplots(figsize=(10.5, 6.5), layout="constrained")
        for point in points:
            x = getattr(point, metric)
            if x is None:
                continue
            y = 100 * point.household / 12
            ax.scatter(
                x,
                y,
                s=95,
                c=COLORS[point.label],
                marker=MARKERS[point.engine],
                edgecolors="white",
                linewidths=0.8,
                zorder=3,
            )
            ax.annotate(
                f"{point.label} s{point.seed}",
                (x, y),
                xytext=(5, 8 if point.seed == 17 else -14),
                textcoords="offset points",
                fontsize=8,
                color=COLORS[point.label],
            )
        ax.set_title(
            title_prefix + "Household task quality versus resource cost",
            loc="left",
            fontweight="bold",
            pad=14,
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Household task success (%) · 12 tasks per run")
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
                linestyle="none",
                markersize=8,
                label=v,
            )
            for k, v in ENGINES.items()
        ]
        ax.legend(handles=legend, loc="lower left", frameon=False)
        note = "Each point is one declared seed; no composite intelligence index or confidence interval."
        if metric == "wired_increase_gib":
            note += "\nSystem-wide peak minus median pre-run baseline; partial memory accounting, not exact model RAM."
        fig.text(0.01, -0.035, note, fontsize=8, color="#555")
        for extension in ("png", "svg"):
            fig.savefig(output / f"{name}.{extension}", dpi=180, bbox_inches="tight")
        plt.close(fig)
        names.append(name)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, field, maximum, title in zip(
        axes,
        ("household", "python"),
        (12, 3),
        ("Household quality", "Python automation quality"),
        strict=True,
    ):
        for i, label in enumerate(COLORS):
            group = [p for p in points if p.label == label]
            ys = [getattr(p, field) for p in group]
            if ys:
                ax.plot(
                    [i, i],
                    [min(ys), max(ys)],
                    color=COLORS[label],
                    alpha=0.5,
                    linewidth=4,
                )
            for p in group:
                ax.scatter(
                    i + (-0.06 if p.seed == 17 else 0.06),
                    getattr(p, field),
                    c=COLORS[label],
                    marker=MARKERS[p.engine],
                    s=80,
                    zorder=3,
                )
        ax.set_xticks(range(4), list(COLORS), rotation=18)
        ax.set_ylim(-0.2, maximum + 0.6)
        ax.set_yticks(range(maximum + 1))
        ax.set_ylabel(f"Tasks passed / {maximum}")
        ax.set_title(title_prefix + title, loc="left", fontweight="bold")
        ax.grid(axis="y", alpha=0.18)
    fig.text(
        0.01,
        -0.05,
        "Left/right points: seeds 17/29. Line shows observed range, not uncertainty. Circles: Mei; diamonds: llama.cpp.",
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
    names = figures(points, output)
    data = [asdict(p) for p in points]
    (output / "metrics.json").write_text(
        json.dumps(
            {
                "specification": spec,
                "observations": data,
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
    relative = output.relative_to(summary.parent)
    lines = [
        "# Four-model local agent comparison",
        "",
        f"Frozen benchmark **{spec['benchmark_release']}**; two fresh declared seeds per profile, eight complete runs.",
        "",
        "All four remain retained contenders. These compare serving profiles, not pure model weights or Peixinho application acceptance.",
        "",
    ]
    for name in names:
        lines.extend([f"![{name.replace('-', ' ')}]({relative}/{name}.png)", ""])
    lines.extend(
        [
            "## Exact observations",
            "",
            "| Model / engine | Seed | Household | Python | Full time | Wired increase (GiB) | Weight storage (GiB) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for p in points:
        memory = (
            "unavailable"
            if p.wired_increase_gib is None
            else f"{p.wired_increase_gib:.2f}"
        )
        lines.append(
            f"| {p.label} / {ENGINES[p.engine]} | {p.seed} | {p.household}/12 | {p.python}/3 | {p.wall_minutes:.2f} min | {memory} | {p.weight_gib:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Reading the costs and quality",
            "",
            "Time includes startup/native admission and both tracks, excluding the separate 30-second baseline. Memory is the peak observed system-wide wired-byte increase over median baseline; background activity can affect it. It is partial accounting, not total model memory. GPU allocations are not reliably captured by process RSS/footprint. Weight storage is separate; no counters are added together.",
            "",
            "Household and Python quality remain separate. Seeds 17/29 and observed ranges are not confidence intervals or an independence guarantee. Qwen/Ornith retain their T0.6 sampler; Groot/Logics retain T1 and their declared penalties. Quants, engines and cache settings differ explicitly. No best-run selection or universal winner is implied.",
            "",
            "## Provenance and failures",
            "",
        ]
    )
    for path in spec["cohorts"]:
        cohort = json.loads((root / path).read_text())
        lines.extend([render_campaign(root, cohort), ""])
    lines.extend(
        [
            "[Metric data]("
            + str(relative)
            + "/metrics.json) · [CSV]("
            + str(relative)
            + "/metrics.csv). PNG and SVG exports are kept beside the data.",
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

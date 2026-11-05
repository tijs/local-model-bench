"""Plot completed repeated task coverage, marking critical failures as unranked."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from bench_common import REPO
from build_agent_leaderboard import git_reader, render_campaign, resources, track_result
from run_mei_acceptance import split_launch_command
from verify_combined_cohorts import declared_profile, model_files


def aggregate(model, label, runs):
    """Pool equal-coverage runs without hiding critical failures."""
    if (
        len(runs) != 2
        or runs[0][0]["runtime_identity"] != runs[1][0]["runtime_identity"]
        or runs[0][2:] != runs[1][2:]
    ):
        raise ValueError("expected two runs of the same runtime")
    rows = [row for h, p, _, _ in runs for row in h["rows"] + p["rows"]]
    if len(rows) != 30:
        raise ValueError("expected complete two-seed task coverage")
    return {
        "model": model,
        "label": label,
        "household_passes": sum(h["passed"] for h, _, _, _ in runs),
        "household_attempts": 24,
        "python_passes": sum(p["passed"] for _, p, _, _ in runs),
        "python_attempts": 6,
        "mean_task_seconds": fmean(row["wall_seconds"] for row in rows),
        "critical_failures": sum(h["critical"] for h, _, _, _ in runs),
    }


def collect(root, spec):
    """Validate both cohorts and retain every completed observation, including failures."""
    labels = spec["models"]
    if len(spec["cohorts"]) != 2 or set(spec["seeds"]) != {17, 29}:
        raise ValueError("two declared seed cohorts required")
    records = {model: [] for model in labels}
    seen_seeds = set()
    for path in spec["cohorts"]:
        campaign = json.loads((root / path).read_text())
        if (
            campaign["release_commit"] != spec["release_commit"]
            or campaign["benchmark_release"] != spec["benchmark_release"]
        ):
            raise ValueError("cohort method differs")
        render_campaign(root, campaign)
        if {e["model"] for e in campaign["models"]} != set(labels):
            raise ValueError("cohort model set differs")
        reader = lambda commit, name: git_reader(root, commit, name)
        cohort_seed = None
        for entry in campaign["models"]:
            house = track_result(root, entry, campaign, "household", reader)
            python = track_result(root, entry, campaign, "python", reader)
            monitor = resources(root, entry, campaign, reader, [house, python])
            if not (
                house["complete"]
                and python["complete"]
                and monitor["completed"]
                and monitor["within_policy"]
            ):
                raise ValueError("incomplete or resource-ineligible run")
            if house["runtime_identity"] != python["runtime_identity"]:
                raise ValueError("runtime changed across tracks")
            manifests = [
                json.loads(
                    (
                        root
                        / "results"
                        / folder
                        / "runs"
                        / entry[key]
                        / "manifest.json"
                    ).read_text()
                )
                for folder, key in (
                    ("standin", "household_run"),
                    ("automation", "python_run"),
                )
            ]
            seed = manifests[0]["generation_overrides"]["seed"]
            if (
                seed not in spec["seeds"]
                or manifests[1]["generation_overrides"]["seed"] != seed
            ):
                raise ValueError("seed mismatch across tracks")
            if cohort_seed is None:
                cohort_seed = seed
            elif cohort_seed != seed:
                raise ValueError("cohort mixes seeds")
            cfg = yaml.safe_load((root / entry["config"]).read_text())
            command = split_launch_command(cfg["benchmark_launch_command"])
            flag = "--model-dir" if entry["engine"] == "mei" else "--model"
            path = Path(command[command.index(flag) + 1])
            directory = path if flag == "--model-dir" else path.parent
            hashes = json.loads(
                (root / entry["supervision"] / "post-run-model-hashes.json").read_text()
            )
            files = model_files(hashes, directory=str(directory))
            records[entry["model"]].append(
                (house, python, declared_profile(cfg), files)
            )
        if cohort_seed in seen_seeds:
            raise ValueError("duplicate seed cohort")
        seen_seeds.add(cohort_seed)
    return [aggregate(model, labels[model], runs) for model, runs in records.items()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if any(args.output.with_suffix(x).exists() for x in (".png", ".svg", ".json")):
        raise FileExistsError("refuse to overwrite evidence")
    points = collect(REPO, json.loads(args.spec.read_text()))
    fig, ax = plt.subplots(figsize=(10, 6))
    for point in points:
        bad = point["critical_failures"] > 0
        ax.scatter(
            point["mean_task_seconds"],
            100 * point["household_passes"] / 24,
            marker="X" if bad else "o",
            s=160,
            color="#ad3b35" if bad else "#2378b5",
            zorder=3,
        )
        ax.annotate(
            point["label"] + (" · UNRANKED: safety failure" if bad else ""),
            (point["mean_task_seconds"], 100 * point["household_passes"] / 24),
            xytext=(9, 8),
            textcoords="offset points",
            fontsize=9,
        )
    ax.set_xlabel("Mean task time, seconds (all attempts)")
    ax.set_ylabel("Household attempts passed (%)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.2)
    ax.set_title("Repeated task results — safety failure shown unranked")
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for ext in (".png", ".svg"):
        fig.savefig(args.output.with_suffix(ext), dpi=160)
    plt.close(fig)
    args.output.with_suffix(".json").write_text(
        json.dumps(
            {
                "points": points,
                "scope": "Two declared runs, equal task coverage; unranked critical failures are descriptive, not eligible quality points.",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

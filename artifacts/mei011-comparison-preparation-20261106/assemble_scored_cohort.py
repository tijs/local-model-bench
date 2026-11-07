"""Build publication inputs from terminal, audited task runs, without launching anything."""

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runner"))
from build_agent_leaderboard import render_campaign
from run_scored_cohort import PROGRESS, READBACKS, cell_paths

TRACKS = ("peixinho-standin-v1", "python-automation-v1")


def load(path):
    return json.loads(path.read_text())


def checked_run(root, row, config):
    directory = root / row["output"]
    outcome = load(directory / "outcome.json")
    audit = load(directory / "audit.json")
    ids = outcome["run_ids"]
    if (
        outcome["returncode"] != 0
        or outcome["stop_reason"] is not None
        or ids != row["run_ids"]
        or set(ids) != set(TRACKS)
        or any(len(ids[track]) != 1 for track in TRACKS)
        or len(audit["household"]) != 12
        or len(audit["python"]) != 3
        or not (directory / "README.md").is_file()
    ):
        raise ValueError(f"incomplete run evidence: {row['output']}")
    raw = (root / config).read_bytes()
    if raw != (directory / "config.yaml").read_bytes():
        raise ValueError("selected launch config differs from archived snapshot")
    cfg = yaml.safe_load(raw)
    readback = READBACKS / f"{row['model']}-seed{row['seed']}.json"
    if row["pre_run_readback"] != str(readback.relative_to(ROOT)):
        raise ValueError("run is missing its declared checkpoint readback")
    before = load(root / row["pre_run_readback"])
    after = load(directory / "post-run-model-hashes.json")
    pre = sorted((f["bytes"], f["sha256"]) for f in before["files"])
    post = sorted((f["bytes"], f["sha256"]) for f in after["files"])
    if (
        not pre
        or pre != post
        or after["all_match"] is not True
        or not math.isfinite(before["elapsed_seconds"])
        or before["elapsed_seconds"] <= 0
    ):
        raise ValueError("pre-run and post-run checkpoint evidence differs")
    if (
        cfg["generation_profiles"][cfg["standin_generation_profile"]]["seed"]
        != row["seed"]
    ):
        raise ValueError("selected run uses a different seed")
    return {
        "model": cfg["model"],
        "engine": cfg["inference_engine"],
        "config": config,
        "household_run": ids[TRACKS[0]][0],
        "python_run": ids[TRACKS[1]][0],
        "supervision": row["output"],
    }


def prepare():
    declaration = load(PREP / "campaign.json")
    progress = load(PROGRESS)
    if progress["status"] != "complete" or progress["current"] is not None:
        raise ValueError("the eight-run campaign has not reached terminal completion")
    cells = [(row["model"], row["seed"]) for row in declaration["cells"]]
    completed = progress["completed"]
    if [(row["model"], row["seed"]) for row in completed] != cells or len(
        set(cells)
    ) != 8:
        raise ValueError("missing, duplicate, or undeclared trajectory")
    old = load(ROOT / "results/four-model-mei010-comparison.json")
    if old["benchmark_release"] != declaration["method"] or not old[
        "release_commit"
    ].startswith(declaration["method_commit_prefix"]):
        raise ValueError("prior and current cohorts must use the same released method")
    spec = {
        **old,
        "cohorts": [],
        "reports": [],
        "alternative_note": (
            "MiniCPM is a previously tested alternative. Its two Mei 0.10 comparison "
            "runs passed 23/24 household and 5/6 Python tasks, with one critical "
            "safety failure; it was unranked. It was not rerun for this four-model "
            "comparison. [Full MiniCPM evidence](MINICPM_MEI010.md). "
            "ThinkingCap remains in the [historical v9.5 report](AGENT_V9.md)."
        ),
    }
    outputs = {}
    for seed in (17, 29):
        entries = []
        for row in (item for item in completed if item["seed"] == seed):
            model = row["model"]
            config, output = cell_paths(model, seed)
            if row["output"] != str(output.relative_to(ROOT)):
                raise ValueError("unexpected owned output")
            entries.append(checked_run(ROOT, row, str(config.relative_to(ROOT))))
        if len(entries) != 4 or {x["model"] for x in entries} != set(spec["models"]):
            raise ValueError(
                "the complete seed must include all four pinned contenders"
            )
        cohort = {
            "benchmark_release": spec["benchmark_release"],
            "release_commit": spec["release_commit"],
            "partition": "heldout",
            "trials": 1,
            "status": "fresh_seed_cohort_complete",
            "sampling_plan": "Two declared seeds, 17 and 29; configs committed before launch. Every audited task is retained.",
            "method_notes": [
                "Qwen, Ornith and Groot use the verified Mei 0.11.0 install; Logics is an unchanged llama.cpp control.",
                "Scores compare serving profiles. Groot's allocator budget differs from its previous scored profile. Two seeds do not establish confidence intervals or isolate runtime code.",
            ],
            "models": entries,
            "config_source": "run_commit",
        }
        base = f"four-model-mei011-seed{seed}"
        path = f"results/{base}.json"
        report = f"FOUR_MODEL_MEI011_SEED{seed}.md"
        spec["cohorts"].append(path)
        spec["reports"].append(report)
        outputs[path] = json.dumps(cohort, indent=2) + "\n"
        outputs[f"results/{report}"] = render_campaign(ROOT, cohort)
    outputs["results/four-model-mei011-comparison.json"] = (
        json.dumps(spec, indent=2) + "\n"
    )
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write new, never replace existing, publication files",
    )
    args = parser.parse_args()
    outputs = prepare()
    if args.write and any((ROOT / path).exists() for path in outputs):
        raise ValueError("refuse to replace existing publication evidence")
    for path, content in outputs.items():
        if args.write:
            with (ROOT / path).open("x") as f:
                f.write(content)
        print(path)


if __name__ == "__main__":
    main()

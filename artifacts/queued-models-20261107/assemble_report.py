"""Compare the two completed challengers with the unchanged four-model baseline."""

import argparse
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from build_agent_leaderboard import git_reader, render_campaign, track_result
from build_four_model_summary import COLORS, export, load_points
from mei_provenance import sha256

CHALLENGERS = {
    "toolspace": ("ToolSpace IQ4_XS", "#a44770"),
    "gemma-ram13": ("Gemma RAM13GB", "#466d42"),
}
TRACKS = {"peixinho-standin-v1": "household_run", "python-automation-v1": "python_run"}


def read(path):
    return json.loads(path.read_text())


def read_challenger(model, seed):
    retry = "-alias-retry" if (model, seed) == ("toolspace", 17) else ""
    label = f"{model}-seed{seed}{retry}"
    run = Path(f"artifacts/queued-{label}-20261107")
    directory = ROOT / run
    if not (directory / "README.md").is_file():
        raise ValueError(f"await a completed and audited run: {run}")
    config = Path(f"configs/queued-models-20261107/{label}.yaml")
    cfg = yaml.safe_load((ROOT / config).read_bytes())
    outcome, audit = (read(directory / name) for name in ("outcome.json", "audit.json"))
    proof = read(directory / "native-admission-evidence.json")
    native = (ROOT / proof["directory"]).resolve()
    before = read(HERE / f"{label}-readback.json")["files"]
    after = read(directory / "post-run-model-hashes.json")
    ids = outcome["run_ids"]
    if (
        outcome["returncode"] != 0
        or outcome["stop_reason"] is not None
        or set(ids) != TRACKS.keys()
        or any(len(ids[track]) != 1 for track in TRACKS)
        or (directory / "config.yaml").read_bytes() != (ROOT / config).read_bytes()
        or audit["runtime"]["request_seed"] != seed
        or len(audit["household"]) != 12
        or len(audit["python"]) != 3
        or not native.is_relative_to(ROOT / "artifacts")
        or not all(
            sha256(native / name) == digest for name, digest in proof["sha256"].items()
        )
        or read(native / "outcome.json")["status"] != "passed"
        or not before
        or after["all_match"] is not True
        or sorted((f["bytes"], f["sha256"]) for f in before)
        != sorted((f["bytes"], f["sha256"]) for f in after["files"])
    ):
        raise ValueError(f"incomplete or mismatched proof: {run}")
    return {
        "model": cfg["model"],
        "engine": cfg["inference_engine"],
        "config": str(config),
        "supervision": str(run),
    } | {key: ids[track][0] for track, key in TRACKS.items()}


def prepare():
    base = read(ROOT / "results/four-model-mei011-comparison.json")
    load_points(
        ROOT, base
    )  # Verify that the baseline still reconstructs from released evidence.
    spec = base | {
        "models": dict(base["models"]),
        "colors": dict(COLORS),
        "cohorts": [],
        "reports": [],
        "alternative_note": base["alternative_note"].replace(
            "for this four-model comparison", "for this comparison"
        ),
    }
    full, critical, outputs = {}, set(), {}
    reader = lambda commit, path: git_reader(ROOT, commit, path)
    for seed, path in zip(base["seeds"], base["cohorts"], strict=True):
        cohort = read(ROOT / path)
        for model, (label, color) in CHALLENGERS.items():
            entry = read_challenger(model, seed)
            cohort["models"].append(entry)
            spec["models"][entry["model"]] = label
            spec["colors"][label] = color
            house = track_result(ROOT, entry, cohort, "household", reader)
            python = track_result(ROOT, entry, cohort, "python", reader)
            if (
                not house
                or not python
                or not house["complete"]
                or not python["complete"]
            ):
                raise ValueError(f"unusable scored coverage: {model} seed {seed}")
            if house["critical"]:
                critical.add(entry["model"])
        cohort["method_notes"].append(
            "ToolSpace and Gemma ran as challengers on the same frozen task method. Original control trajectories are reused unchanged from the previous comparison."
        )
        full[seed] = cohort
        report = f"QUEUED_CHALLENGERS_SEED{seed}.md"
        outputs[ROOT / "results" / report] = render_campaign(ROOT, cohort)
        spec["reports"].append(report)
    if critical:
        names = ", ".join(spec["models"].pop(model) for model in sorted(critical))
        spec["alternative_note"] = (
            f"{names} completed testing but had a critical household boundary failure and is excluded from qualified averages. The linked seed reports retain those scores. "
            + spec["alternative_note"]
        )
    for seed, cohort in full.items():
        path = f"results/queued-challengers-seed{seed}.json"
        spec["cohorts"].append(path)
        eligible = cohort | {
            "models": [
                entry for entry in cohort["models"] if entry["model"] not in critical
            ]
        }
        outputs[ROOT / path] = json.dumps(eligible, indent=2) + "\n"
    outputs[ROOT / "results/queued-challengers-comparison.json"] = (
        json.dumps(spec, indent=2) + "\n"
    )
    return outputs, spec


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    files, specification = prepare()
    if args.write:
        summary = ROOT / "results/QUEUED_CHALLENGERS_FINAL.md"
        charts = ROOT / "results/charts/queued-challengers"
        if any(path.exists() for path in (*files, summary, charts)):
            raise FileExistsError("refuse to overwrite any existing challenger report")
        for path, data in files.items():
            with path.open("x") as f:
                f.write(data)
        export(ROOT, specification, summary, charts)
    print("Both challengers audited against the frozen baseline")

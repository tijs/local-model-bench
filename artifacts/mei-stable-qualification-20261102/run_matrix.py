"""Sequential qualification cells with terminal preservation and parity audit."""

import argparse
import hashlib
import json
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent


def observable_by_context(result):
    rows = result["rows"]
    expected = {
        (context, phase, repeat)
        for context in ("short", "loaded")
        for phase, repeats in (
            ("cold" if context == "short" else "cold_status", (0,)),
            ("warmup", (0,)),
            ("measured", range(1, 6)),
        )
        for repeat in repeats
    }
    actual = {(row["context"], row["phase"], row["repeat"]) for row in rows}
    if actual != expected or len(rows) != len(expected):
        raise ValueError(
            "missing/duplicate cold, warmup or five-repeat context observations"
        )
    reference = {
        row["context"]: row["observable"]
        for row in rows
        if row["phase"] in ("cold", "cold_status")
    }
    if any(row["observable"] != reference[row["context"]] for row in rows):
        raise ValueError(
            "greedy byte/count/finish output changed within the same process"
        )
    return reference


def audit(output, baseline):
    q = json.loads((output / "qualification.json").read_text())
    outcome = json.loads((output / "outcome.json").read_text())
    if q["status"] != "passed" or outcome["status"] != "passed":
        raise ValueError("cell did not complete its guarded qualification")
    reference = observable_by_context(q)
    if baseline is not None and reference != baseline:
        raise ValueError(
            "greedy byte/count/finish parity differs from the predeclared A1 control"
        )
    resources = [
        json.loads(line)
        for line in (output / "resources.jsonl").read_text().splitlines()
    ]
    return {
        "passed": True,
        "reference": reference,
        "resource_samples": len(resources),
        "all_normal_pressure": all(
            row["kernel_pressure_level"] == 1 for row in resources
        ),
        "swap_min_mib": min(row["swap_used_mib"] for row in resources),
        "swap_max_mib": max(row["swap_used_mib"] for row in resources),
        "normal_output_budget": q["normal_output_budget"],
        "median_decode_tps": {
            context: statistics.median(
                row["decode_tps"]
                for row in q["rows"]
                if row["phase"] == "measured" and row["context"] == context
            )
            for context in ("short", "loaded")
        },
        "swift_acceptance": q.get("swift_acceptance"),
    }


def save_progress(progress, destination):
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(progress, indent=2) + "\n")
    temporary.replace(destination)


def baseline_references(matrix):
    """Reuse explicit audited greedy controls, never their old timing values."""
    declared = matrix.get("baselines", {})
    if not isinstance(declared, dict):
        raise TypeError("baselines must be an explicit model-to-audit mapping")
    models = {cell["model"] for cell in matrix["cells"]}
    if declared and declared.keys() != models:
        raise ValueError("declare a saved control for every model or none")
    references = {}
    for model, spec in declared.items():
        path = (ROOT / spec["audit"]).resolve()
        if (
            not path.is_relative_to(ROOT.resolve())
            or path.name != "qualification-audit.json"
        ):
            raise ValueError("saved control must be a contained qualification audit")
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
            raise ValueError("saved control audit hash mismatch")
        stored = json.loads(path.read_text())
        checked = audit(path.parent, None)
        if stored != checked:
            raise ValueError("saved control does not reproduce its complete raw audit")
        snapshot = (path.parent / "config.yaml").read_bytes()
        config_sha = hashlib.sha256(snapshot).hexdigest()
        invocation = json.loads((path.parent / "invocation.json").read_text())
        if (
            config_sha != spec["config_sha256"]
            or config_sha != invocation["config_sha256"]
        ):
            raise ValueError("saved control configuration hash mismatch")
        control = yaml.safe_load(snapshot)
        result = json.loads((path.parent / "qualification.json").read_text())
        if result["model"] != control["orchestration"]["served_model_id"] or result[
            "command"
        ] != shlex.split(control["benchmark_launch_command"]):
            raise ValueError("saved control served model/command identity mismatch")
        expected = {
            "mei_source_commit": control["mei_source_commit"],
            "vmlx_commit": control["vmlx_commit"],
            "binary_sha256": control["mei_release_artifact"]["binary_sha256"],
            "metallib_sha256": control["mei_release_artifact"]["metallib_sha256"],
        }
        post = json.loads(
            (path.parent / "post-run-runtime-verification.json").read_text()
        )
        if any(
            any(observed.get(key) != value for key, value in expected.items())
            for observed in (result["runtime_identity"], post)
        ):
            raise ValueError("saved control runtime identity mismatch")
        for cell in matrix["cells"]:
            if cell["model"] != model:
                continue
            candidate = yaml.safe_load((ROOT / cell["config"]).read_text())
            if any(control[k] != candidate[k] for k in ("model", "source_revision")):
                raise ValueError("saved control model/revision differs from candidate")
        references[model] = checked["reference"]
    return references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=PREP / "matrix.json")
    parser.add_argument("--progress", type=Path, default=PREP / "matrix-progress.json")
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    if args.progress.exists():
        raise ValueError(
            "do not restart a live or interrupted campaign; inspect its exact process/output first"
        )
    progress = {
        "status": "running",
        "started_epoch": time.time(),
        "completed": [],
        "current": None,
    }
    baseline = baseline_references(matrix)
    save_progress(progress, args.progress)
    for cell in matrix["cells"]:
        progress["current"] = cell
        save_progress(progress, args.progress)
        print(f"START {cell['model']} {cell['cell']}", flush=True)
        output = ROOT / cell["output"]
        run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "runner/qualify_mei_release.py"),
                "--config",
                str(ROOT / cell["config"]),
                "--output",
                str(output),
                "--deadline",
                "3600",
            ],
            cwd=ROOT,
            check=False,
        )
        try:
            outcome = json.loads((output / "outcome.json").read_text())
            if outcome.get("returncode") is not None:
                subprocess.run(
                    [
                        sys.executable,
                        str(PREP / "preserve_run.py"),
                        "--output",
                        str(output),
                        "--model-manifest",
                        str(PREP / f"{cell['model']}-pre-run-model-hashes.json"),
                    ],
                    cwd=ROOT,
                    check=True,
                )
            if run.returncode:
                raise ValueError(
                    f"guarded cell exited {run.returncode}; review before any retry or next model"
                )
            checked = audit(output, baseline.get(cell["model"]))
            with (output / "qualification-audit.json").open("x") as stream:
                json.dump(checked, stream, indent=2)
                stream.write("\n")
            baseline.setdefault(cell["model"], checked["reference"])
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as exc:
            progress.update(
                status="stopped_for_review", error=f"{type(exc).__name__}: {exc}"
            )
            save_progress(progress, args.progress)
            print(progress["error"], flush=True)
            return 1
        progress["completed"].append(
            cell | {"audit": str(output / "qualification-audit.json")}
        )
        save_progress(progress, args.progress)
        print(
            f"PASS {cell['model']} {cell['cell']}: {checked['median_decode_tps']}",
            flush=True,
        )
    progress.update(
        status="measurement_cells_complete", current=None, finished_epoch=time.time()
    )
    save_progress(progress, args.progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

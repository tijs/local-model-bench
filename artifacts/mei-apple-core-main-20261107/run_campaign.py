"""Run committed native and timing cells one at a time under the normal guards."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from prepare import HERE, ROOT, digest, option

PRESERVER = ROOT / "artifacts/mei-upstream-qualification-20261106"
sys.path.insert(0, str(PRESERVER))
from run_mei_acceptance import (
    committed_native_config,
    probe_succeeded,
    split_launch_command,
)
from run_speed_matrix import audit


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def git_file(path):
    expected = subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT)}"], cwd=ROOT
    )
    if path.read_bytes() != expected:
        raise ValueError(f"campaign input differs from HEAD: {path}")
    return expected


def verify_files(config, manifest):
    argv = split_launch_command(config["benchmark_launch_command"])
    root = Path(argv[option(argv, "--model-dir")]).resolve(strict=True)
    root.relative_to("/Volumes/Expansion/local-model-bench/mei-models")
    inventory = json.loads(git_file(manifest))
    if Path(inventory["directory"]).resolve(strict=True) != root:
        raise ValueError("wrong model manifest")
    seen = set()
    for row in inventory["files"]:
        relative = Path(row["file"])
        if relative.is_absolute() or ".." in relative.parts or relative in seen:
            raise ValueError(f"invalid model path: {relative}")
        seen.add(relative)
        path = (root / relative).resolve(strict=True)
        path.relative_to("/Volumes/Expansion/local-model-bench")
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"model hash mismatch: {path}")
    if not seen:
        raise ValueError("empty model manifest")
    return {
        "directory": str(root),
        "files": len(seen),
        "manifest_sha256": digest(manifest),
    }


def check_native(path, native_config):
    _, pinned = committed_native_config(native_config)
    outcome = json.loads((path / "outcome.json").read_bytes())
    if (
        (path / "config.yaml").read_bytes() != pinned
        or outcome.get("status") != "passed"
        or outcome.get("returncode") != 0
        or not outcome.get("full_native_admission")
        or not probe_succeeded(path, skip_context=False, skip_cache=False)
        or not json.loads((path / "post-run-model-hashes.json").read_bytes())[
            "all_match"
        ]
    ):
        raise ValueError(f"full native admission missing or mismatched: {path}")


def campaign(phase, matrix_path=HERE / "matrix.json"):
    matrix_path = matrix_path.resolve()
    if matrix_path not in {
        HERE / "matrix.json",
        HERE.parent / "mei-apple-core-ndebug-20261108" / "matrix.json",
        HERE.parent / "mei-0111-qualification-20261108" / "matrix.json",
    }:
        raise ValueError("only the predeclared Apple core matrices are supported")
    label = matrix_path.parent.name
    matrix = json.loads(git_file(matrix_path))
    reference = {}
    cells = matrix["native" if phase == "native" else "cells"]
    program = "run_mei_acceptance.py" if phase == "native" else "qualify_mei_release.py"
    env = {"HOME": str(Path.home()), "PATH": os.defpath + ":/usr/sbin:/sbin"}
    if phase == "timing":
        for cell in matrix["native"]:
            check_native(ROOT / cell["output"], ROOT / cell["config"])
    progress = matrix_path.parent / f"{phase}-progress.jsonl"
    with progress.open("x", buffering=1) as journal:
        for cell in cells:
            path = ROOT / cell["config"]
            cfg, _ = committed_native_config(path)
            output = ROOT / cell["output"]
            expected = f"{cell['model']}-{label}-{cell['cell']}"
            runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
            owned = (
                Path.home() / ".local/share/local-model-bench/mei-runtime" / expected
            )
            if (
                output != ROOT / "artifacts" / expected
                or runtime != owned
                or runtime.exists()
                or runtime.is_symlink()
                or output.exists()
                or output.is_symlink()
            ):
                raise ValueError("requires a fresh owned output and runtime")
            manifest = ROOT / matrix["model_manifests"][cell["model"]]
            before = verify_files(cfg, manifest)
            journal.write(
                json.dumps({"state": "started", **cell, "model_readback": before})
                + "\n"
            )
            print(f"START {cell['model']} {cell['cell']}", flush=True)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "runner" / program),
                    "--config",
                    str(path),
                    "--output",
                    str(output),
                    "--deadline",
                    "3600",
                ],
                cwd=ROOT,
                env=env,
                check=False,
            )
            outcome = json.loads((output / "outcome.json").read_bytes())
            if (
                outcome.get("returncode") is not None
                and (runtime / "logs/server.log").is_file()
            ):
                subprocess.run(
                    [
                        sys.executable,
                        str(PRESERVER / "preserve_native.py"),
                        "--output",
                        str(output),
                        "--model-manifest",
                        str(manifest),
                    ],
                    cwd=ROOT,
                    env=env,
                    check=True,
                )
                save(output / "pre-run-readback.json", before)
            if result.returncode:
                raise ValueError(f"cell stopped; review before continuing: {output}")
            if phase == "native":
                check_native(output, path)
            else:
                if not json.loads((output / "post-run-model-hashes.json").read_bytes())[
                    "all_match"
                ]:
                    raise ValueError("timing model provenance missing")
                checked = audit(output, reference.get(cell["model"]))
                reference.setdefault(cell["model"], checked["reference"])
                save(output / "qualification-audit.json", checked)
            journal.write(json.dumps({"state": "passed", **cell}) + "\n")
            print(f"PASS {cell['model']} {cell['cell']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("native", "timing"))
    parser.add_argument("--matrix", type=Path, default=HERE / "matrix.json")
    args = parser.parse_args()
    campaign(args.phase, args.matrix)

"""Check whether validated task scores and speed observations describe one profile.

This separate publication gate checks declared launch settings and saved post-run
model identities. It cannot attest to undeclared inherited environment or make
native engine TPS conventions identical. Both source cohorts must independently
pass their existing complete-evidence validators first.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from bench_common import REPO
from build_context_speed_cohort import contained, load_cohort
from build_four_model_summary import load_points
from run_mei_acceptance import split_launch_command

OWNED_FLAGS = {
    "--mei-binary",
    "--mei-repo",
    "--request-log",
    "--runtime-base",
    "--kv-cache-dir",
}


def declared_profile(cfg: dict[str, Any]) -> tuple[Any, ...]:
    """Compare declared launch/config values, ignoring only owned paths.

    Retain argument order and all other flags: unknown options and differences in
    defaults must be reviewed instead of being silently assumed equivalent.
    """
    engine = cfg["inference_engine"]
    if engine not in {"mei", "llama.cpp"}:
        raise ValueError("unsupported engine")
    command = split_launch_command(cfg["benchmark_launch_command"])
    if engine == "llama.cpp":
        if not command:
            raise ValueError("empty llama.cpp command")
        command[0] = "<runtime-binary>"
    else:
        if command[:2] != ["bash", "runner/start_mei_server.sh"]:
            raise ValueError("unsupported Mei launcher")
        for required in ("--mei-binary", "--mei-repo"):
            if command.count(required) != 1:
                raise ValueError("Mei binary and source paths must be explicit")
    for flag in OWNED_FLAGS:
        count = command.count(flag)
        if count > 1:
            raise ValueError(f"duplicate {flag}")
        if count:
            index = command.index(flag)
            if index + 1 >= len(command) or command[index + 1].startswith("--"):
                raise ValueError(f"missing value for {flag}")
            command[index + 1] = "<owned-path>"
    env = dict(cfg.get("required_runner_environment", {}))
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError("environment must be a string mapping")
    env.pop("MEI_RUNTIME_BASE", None)
    if engine == "mei":
        artifact = cfg["mei_release_artifact"]
        runtime = (
            artifact["binary_sha256"],
            artifact["metallib_sha256"],
            cfg["mei_source_commit"],
            cfg["vmlx_commit"],
        )
    else:
        details = cfg["runtime"]
        runtime = (
            details["binary_sha256"],
            details["revision"],
            tuple(sorted(details["shared_libraries"].items())),
        )
    return (
        cfg["model"],
        cfg["source_revision"],
        engine,
        cfg["context_cap"],
        tuple(command),
        tuple(sorted(env.items())),
        runtime,
    )


def model_files(record: dict[str, Any], *, directory: str | None = None) -> tuple:
    """Compare complete saved model lists by relative file, size and digest."""
    if record.get("all_match") is not True or not record.get("files"):
        raise ValueError("missing successful model hash evidence")
    if directory is None:
        directory = record.get("directory")
    if not isinstance(directory, str) or not Path(directory).is_absolute():
        raise ValueError("model directory must be absolute")
    base = Path(directory)
    rows = []
    for item in record["files"]:
        path = Path(item["file"])
        relative = path.relative_to(base) if path.is_absolute() else path
        if not relative.parts or any(p in (".", "..") for p in relative.parts):
            raise ValueError("invalid model file path")
        digest, size = item["sha256"], item["bytes"]
        if (
            item.get("matches") is not True
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("invalid model file identity")
        rows.append((relative.as_posix(), size, digest))
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("duplicate model file identity")
    return tuple(sorted(rows))


def matching_speed_profile(expected: tuple, candidate: tuple, task_cfg: dict) -> bool:
    """Allow different Mei source commits only when build inputs are identical.

    The binary, Metal library, dependency pin, flags and environment must still
    match exactly. Resolve the runtime source tree and package files directly
    from both commits, rather than relying on a claim in either configuration.
    """
    if candidate == expected:
        return True
    if expected[:6] != candidate[:6] or expected[2] != "mei":
        return False
    left, right = expected[6], candidate[6]
    if left[:2] != right[:2] or left[3] != right[3]:
        return False
    commits = (left[2], right[2])
    if any(not re.fullmatch(r"[0-9a-f]{40}", c) for c in commits):
        return False
    command = split_launch_command(task_cfg["benchmark_launch_command"])
    repo = command[command.index("--mei-repo") + 1]
    for path in ("Sources", "Package.swift", "Package.resolved"):
        ids = []
        for commit in commits:
            result = subprocess.run(
                ["git", "-C", repo, "rev-parse", "--verify", f"{commit}:{path}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                return False
            ids.append(result.stdout.strip())
        if ids[0] != ids[1]:
            return False
    return True


def verify_task_runtime(cfg: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Bind observed task runtime fields to the config being compared."""
    actual = manifest["runtime_identity"]
    if cfg["inference_engine"] == "mei":
        artifact = cfg["mei_release_artifact"]
        expected = {
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
            "binary_sha256": artifact["binary_sha256"],
            "metallib_sha256": artifact["metallib_sha256"],
        }
    elif cfg["inference_engine"] == "llama.cpp":
        runtime = cfg["runtime"]
        expected = {
            key: runtime[key]
            for key in ("revision", "binary_sha256", "shared_libraries")
        }
    else:
        raise ValueError("unsupported engine")
    if not isinstance(actual, dict) or any(
        actual.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("observed task runtime differs from declared config")


def compare(root: Path, score_spec: dict, speed_spec: dict) -> dict:
    """Validate both cohorts, then compare their source configurations."""
    root = root.resolve()
    load_points(root, score_spec)
    load_cohort(root, speed_spec)
    labels = score_spec["models"]
    speed = speed_spec["profiles"]
    by_label = {item["model"]: item for item in speed}
    if len(by_label) != len(speed) or set(by_label) != set(labels.values()):
        raise ValueError("score and speed cohorts must contain the same labels")
    checked = []
    for model_id, label in labels.items():
        item = by_label[label]
        if item["model_id"] != model_id:
            raise ValueError(f"{label}: model id mismatch")
        expected = None
        expected_files = None
        for cohort_path in score_spec["cohorts"]:
            cohort = json.loads(contained(root, cohort_path, "results").read_text())
            entry = next(
                entry for entry in cohort["models"] if entry["model"] == model_id
            )
            directory = contained(root, entry["supervision"], "artifacts")
            config_bytes = contained(root, entry["config"], "configs").read_bytes()
            if (directory / "config.yaml").read_bytes() != config_bytes:
                raise ValueError(f"{label}: score config differs from saved snapshot")
            cfg = yaml.safe_load(config_bytes)
            for folder, key in (
                ("standin", "household_run"),
                ("automation", "python_run"),
            ):
                run = contained(root, f"results/{folder}/runs/{entry[key]}", "results")
                verify_task_runtime(
                    cfg, json.loads((run / "manifest.json").read_text())
                )
            saved = json.loads((directory / "post-run-model-hashes.json").read_text())
            if cfg["inference_engine"] == "mei":
                command = split_launch_command(cfg["benchmark_launch_command"])
                model_dir = command[command.index("--model-dir") + 1]
            else:
                command = split_launch_command(cfg["benchmark_launch_command"])
                model_dir = str(Path(command[command.index("--model") + 1]).parent)
            files = model_files(saved, directory=model_dir)
            profile = declared_profile(cfg)
            if expected is None:
                expected, expected_files = profile, files
            elif (profile, files) != (expected, expected_files):
                raise ValueError(
                    f"{label}: score seeds have different profiles or model files"
                )
        task_cfg = cfg
        for process in item["processes"]:
            cfg = yaml.safe_load(
                contained(root, process["config"], "configs").read_text()
            )
            if not matching_speed_profile(expected, declared_profile(cfg), task_cfg):
                raise ValueError(f"{label}: speed and task declared profiles differ")
            if cfg["inference_engine"] == "mei":
                saved = json.loads(
                    contained(root, item["model_manifest"], "artifacts").read_text()
                )
                files = model_files(saved)
            else:
                files = (
                    (
                        Path(cfg["model_file"]).name,
                        cfg["model_bytes"],
                        cfg["model_sha256"],
                    ),
                )
            if files != expected_files:
                raise ValueError(f"{label}: speed and task model files differ")
        checked.append(label)
    return {
        "status": "passed",
        "profiles": checked,
        "scope": "Validated cohorts, declared launcher/environment and model/runtime identities; does not attest undeclared inherited environment, task sampling parity or cross-engine TPS conventions.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True, type=Path)
    parser.add_argument("--speed", required=True, type=Path)
    args = parser.parse_args()
    score = json.loads(args.scores.read_text())
    speed = json.loads(args.speed.read_text())
    print(json.dumps(compare(REPO, score, speed), indent=2))


if __name__ == "__main__":
    main()

"""Freeze the native and ABBA profiles once the candidate artifact exists."""

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = HERE.name
CONFIGS = ROOT / "configs" / LABEL
OLD = ROOT / "configs/mei-0.11.0-comparison-20261107"
STABLE = {
    "qwen": OLD / "qwen-seed17.yaml",
    "ornith": OLD / "ornith-seed17.yaml",
    "groot": OLD / "groot-seed17.yaml",
    "gemma": ROOT / "configs/queued-models-20261107/gemma-ram13-native.yaml",
}
SOURCE_MANIFESTS = {
    model: ROOT
    / "artifacts/mei-upstream-qualification-20261106"
    / f"{model}-media-prefix-pre-run-model-hashes.json"
    for model in STABLE
    if model != "gemma"
}
SOURCE_MANIFESTS["gemma"] = (
    ROOT / "artifacts/queued-gemma-ram13-native-20261107/post-run-model-hashes.json"
)
sys.path.insert(0, str(ROOT / "runner"))
from mei_clean_speed import clean_environment
from qualify_mei_release import qualification_settings, uncached_streaming_timing
from run_mei_acceptance import validate_owned_config


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def option(argv: list[str], key: str) -> int:
    if argv.count(key) != 1:
        raise ValueError(f"expected exactly one {key}")
    return argv.index(key) + 1


def build(candidate_repo: Path, binary: Path) -> dict[Path, str]:
    source = git(candidate_repo, "rev-parse", "HEAD")
    pins = json.loads((candidate_repo / "Package.resolved").read_text())["pins"]
    (vmlx,) = [p["state"]["revision"] for p in pins if p["identity"] == "vmlx-swift"]
    metal = binary.parent / "mlx.metallib"
    receipt = {
        "source_revision": source,
        "binary_sha256": digest(binary),
        "metallib_sha256": digest(metal),
        "qualification_build": True,
    }
    matrix = {"native": [], "cells": [], "model_manifests": {}}
    outputs = {}
    for model, path in STABLE.items():
        original = yaml.safe_load(path.read_bytes())
        argv = shlex.split(original["benchmark_launch_command"])
        model_path = Path(argv[option(argv, "--model-dir")]).resolve(strict=True)
        model_path.relative_to("/Volumes/Expansion/local-model-bench/mei-models")
        pin = json.loads(SOURCE_MANIFESTS[model].read_bytes())
        if Path(pin["directory"]).resolve(strict=True) != model_path:
            raise ValueError(f"manifest does not identify {model_path}")
        matrix["model_manifests"][model] = str(
            SOURCE_MANIFESTS[model].relative_to(ROOT)
        )
        for cell in ("native", "a1", "b1", "b2", "a2"):
            native = cell == "native"
            candidate = native or cell.startswith("b")
            name = f"{model}-{LABEL}-{cell}"
            config_path = CONFIGS / f"{model}-{cell}.yaml"
            runtime = Path.home() / ".local/share/local-model-bench/mei-runtime" / name
            command = argv.copy()
            for key, value in {
                "--model-dir": model_path,
                "--runtime-base": runtime,
                "--request-log": runtime / "logs/requests.jsonl",
                "--kv-cache-dir": runtime / "kv",
            }.items():
                command[option(command, key)] = str(value)
            if candidate:
                command[option(command, "--mei-repo")] = str(candidate_repo)
                command[option(command, "--mei-binary")] = str(binary)
            if not native:
                command[option(command, "--cache-mode")] = "off"
                index = option(command, "--kv-cache-dir")
                del command[index - 1 : index + 1]
            cfg = {
                key: original[key]
                for key in (
                    "model",
                    "source_revision",
                    "base_model",
                    "inference_engine",
                    "model_bytes",
                    "weight_bytes",
                    "weight_shards",
                    "quant_family",
                    "context_cap",
                    "prefill_step_size",
                    "temperature",
                    "benchmark_endpoint",
                    "resource_monitor_policy",
                    "capacity_plan",
                    "mei_source_commit",
                    "vmlx_commit",
                    "mlx_version",
                    "mei_release_artifact",
                )
            }
            cfg.update(
                benchmark_scope="mei-native-acceptance-v1"
                if native
                else "mei-release-qualification-v1",
                benchmark_status="Apple MLX core main qualification; no scored task rows.",
                benchmark_launch_command=shlex.join(command),
                required_runner_environment=original["required_runner_environment"]
                | {"MEI_RUNTIME_BASE": str(runtime)},
                orchestration={
                    "raw_port": 8024,
                    "served_model_id": command[option(command, "--served-model-id")],
                    "needs_proxy": False,
                    "viable": "model_only",
                    "rank_eligible": False,
                },
            )
            if candidate:
                cfg.update(
                    mei_source_commit=source,
                    vmlx_commit=vmlx,
                    mlx_version="0.32.5",
                    mei_release_artifact=receipt,
                )
            if not native:
                cfg["mei_uncached_streaming_timing"] = True
                cfg["mei_qualification"] = {
                    "repeats": 5,
                    "loaded_tokens": 30000,
                    "decode_tokens": 128,
                    "status_timeout": 1,
                }
                cfg["mei_clean_speed_launch"] = {
                    "mode": "git-stdin-clean-env-v1",
                    "launcher_sha256": digest(ROOT / "runner/start_mei_server.sh"),
                    "environment": {
                        "HOME": str(Path.home()),
                        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                    }
                    | cfg["required_runner_environment"],
                }
                qualification_settings(cfg)
                uncached_streaming_timing(cfg)
                clean_environment(cfg)
            validate_owned_config(cfg)
            outputs[config_path] = yaml.safe_dump(cfg, sort_keys=False)
            matrix["native" if native else "cells"].append(
                {
                    "model": model,
                    "cell": cell,
                    "config": str(config_path.relative_to(ROOT)),
                    "output": f"artifacts/{name}",
                }
            )
    outputs[HERE / "matrix.json"] = json.dumps(matrix, indent=2) + "\n"
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    outputs = build(
        args.candidate_repo.resolve(strict=True), args.binary.resolve(strict=True)
    )
    if any(path.exists() for path in outputs):
        raise FileExistsError("refuse to overwrite existing qualification profiles")
    CONFIGS.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        with path.open("x") as stream:
            stream.write(content)

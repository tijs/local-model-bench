"""Freeze a mirrored Qwen comparison of published, as-built and corrected Mei."""

import argparse
import json
import shlex
import subprocess
from pathlib import Path

import yaml
from patch_release_ndebug import original_manifest, release_manifest
from prepare import CONFIGS, HERE, ROOT, digest, option
from run_campaign import git_file

# isort: split
# prepare adds the benchmark runner modules to the import path.
from mei_clean_speed import clean_environment
from qualify_mei_release import qualification_settings, uncached_streaming_timing
from run_mei_acceptance import validate_owned_config

LABEL = "mei-apple-core-ndebug-20261108"
EXPANSION = Path("/Volumes/Expansion/local-model-bench")
# Each build appears once in each mirrored half. Keep native admission separate.
CASES = {
    "native": ("native", "corrected"),
    "r1": ("a1", "published"),
    "a1": ("b1", "instrumented"),
    "b1": ("b1", "corrected"),
    "b2": ("b2", "corrected"),
    "a2": ("b2", "instrumented"),
    "r2": ("a2", "published"),
}


def artifact(build):
    receipt = json.loads(git_file(HERE / "build-receipt.json"))
    build = build.resolve(strict=True)
    if build.parent != EXPANSION or not build.name.startswith(
        ("apple-release-ndebug-build-20261108.", "apple-release-ndebugbuild-20261108.")
    ):
        raise ValueError("expected the separate Expansion build directory")
    binary = build / "out/Products/Release/mei"
    library = binary.parent / "mlx.metallib"
    patch = build / "aligned-manifest.diff"
    flags = build / "aligned-cxx-flags.sha256"
    evaluator = build / "aligned-metal-eval.txt"
    readback = (build / "aligned-assets.sha256").read_text().splitlines()
    expected = {
        str(binary): digest(binary),
        str(library): digest(library),
        str(patch): digest(patch),
        str(flags): digest(flags),
        str(evaluator): digest(evaluator),
    }
    for line in readback:
        sha, path = line.split("  ", 1)
        if path in expected and expected.pop(path) != sha:
            raise ValueError(
                f"new artifact differs from completed build receipt: {path}"
            )
    if expected:
        raise ValueError(f"build receipt lacks expected identities: {list(expected)}")
    flag_targets = set()
    args_root = build / "out/Intermediates.noindex/mlx-swift.build/Release"
    for line in flags.read_text().splitlines():
        sha, name = line.split("  ", 1)
        args = Path(name).resolve(strict=True)
        target = args.relative_to(args_root).parts[0]
        options = shlex.split(args.read_text())
        if digest(args) != sha or not {"-DNDEBUG", "-DNDEBUG=1"}.intersection(options):
            raise ValueError(
                f"Release compiler flags no longer match the receipt: {args}"
            )
        flag_targets.add(target)
    if flag_targets != {"Cmlx-t.build", "CmlxGraphShim-t.build"}:
        raise ValueError("both C++ targets need recorded Release compiler flags")
    assembly = evaluator.read_text()
    if "needs_commit" not in assembly or "verify_graph" in assembly:
        raise ValueError("unexpected Release Metal evaluator instructions")
    binary_sha = digest(binary)
    metal_sha = digest(library)
    if (
        metal_sha != receipt["release"]["metallib_sha256"]
        or binary_sha == receipt["release"]["sha256"]
    ):
        raise ValueError(
            "corrected executable must differ and reuse the original Metal library"
        )
    checkout = build / "checkouts/vmlx-swift"
    if (checkout / "Package.swift").read_text() != release_manifest(
        original_manifest(checkout)
    ):
        raise ValueError(
            "both Cmlx and its C++ graph shim require the same Release define"
        )
    if (
        subprocess.check_output(
            ["git", "-C", str(checkout), "diff", "--", "Package.swift"]
        )
        != patch.read_bytes()
    ):
        raise ValueError("staged manifest does not match its build receipt")
    return binary, {
        "source_revision": receipt["mei"],
        "binary_sha256": binary_sha,
        "metallib_sha256": metal_sha,
        "build_manifest_patch_sha256": digest(patch),
        "cxx_flags_receipt_sha256": digest(flags),
        "qualification_build": True,
    }


def profiles(build):
    binary, corrected = artifact(build)
    initial = json.loads(git_file(HERE / "matrix.json"))
    matrix = {
        "native": [],
        "cells": [],
        "model_manifests": {"qwen": initial["model_manifests"]["qwen"]},
    }
    outputs = {}
    for cell, (template, arm) in CASES.items():
        cfg = yaml.safe_load(git_file(CONFIGS / f"qwen-{template}.yaml"))
        name = f"qwen-{LABEL}-{cell}"
        runtime = Path.home() / ".local/share/local-model-bench/mei-runtime" / name
        command = shlex.split(cfg["benchmark_launch_command"])
        for key, target in {
            "--runtime-base": runtime,
            "--request-log": runtime / "logs/requests.jsonl",
        }.items():
            command[option(command, key)] = str(target)
        if "--kv-cache-dir" in command:
            command[option(command, "--kv-cache-dir")] = str(runtime / "kv")
        if arm == "corrected":
            command[option(command, "--mei-binary")] = str(binary)
            if cfg["mei_source_commit"] != corrected["source_revision"]:
                raise ValueError(
                    "corrected build must use the as-built candidate source"
                )
            cfg["mei_release_artifact"] = corrected
        cfg["benchmark_launch_command"] = shlex.join(command)
        cfg["required_runner_environment"]["MEI_RUNTIME_BASE"] = str(runtime)
        cfg["benchmark_status"] = f"Release graph instrumentation diagnostic: {arm}."
        validate_owned_config(cfg)
        if cell != "native":
            cfg["mei_clean_speed_launch"]["environment"]["MEI_RUNTIME_BASE"] = str(
                runtime
            )
            clean_environment(cfg)
            qualification_settings(cfg)
            uncached_streaming_timing(cfg)
        config = ROOT / "configs" / LABEL / f"qwen-{cell}.yaml"
        outputs[config] = yaml.safe_dump(cfg, sort_keys=False)
        matrix["native" if cell == "native" else "cells"].append(
            {
                "model": "qwen",
                "cell": cell,
                "arm": arm,
                "config": str(config.relative_to(ROOT)),
                "output": f"artifacts/{name}",
            }
        )
    destination = ROOT / "artifacts" / LABEL
    for evidence in (
        "aligned-manifest.diff",
        "aligned-cxx-flags.sha256",
        "aligned-assets.sha256",
        "aligned-metal-eval.txt",
    ):
        outputs[destination / evidence] = (build / evidence).read_text()
    outputs[destination / "matrix.json"] = json.dumps(matrix, indent=2) + "\n"
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path, help="completed separate diagnostic build")
    outputs = profiles(parser.parse_args().build.resolve(strict=True))
    if any(path.exists() or path.is_symlink() for path in outputs):
        raise FileExistsError("refuse to overwrite a declared comparison")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            stream.write(content)


if __name__ == "__main__":
    main()

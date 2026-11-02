"""Bind scored Clover runs to a pinned native Metal decoder and derived source."""

from __future__ import annotations

import fcntl
import os
import re
import shlex
import subprocess
from pathlib import Path

from bench_common import REPO
from mei_provenance import git, listener_binary, sha256


def system_libraries(binary: Path) -> list[str]:
    result = subprocess.check_output(["otool", "-L", str(binary)], text=True)
    libraries = [line.strip().split()[0] for line in result.splitlines()[1:] if line.strip()]
    if not libraries or any(not name.startswith(("/System/Library/", "/usr/lib/")) for name in libraries):
        raise ValueError("Kapitsa must link only declared system libraries")
    return libraries


def verify_kapitsa_runtime(cfg, *, base_url=None):
    if cfg.get("inference_engine") != "kapitsa-metal":
        return None
    runtime = cfg["runtime"]
    revision = runtime["revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Kapitsa requires a full source revision")
    source = Path(runtime["source_directory"]).resolve(strict=True)
    binary = Path(runtime["binary"]).resolve(strict=True)
    if git(source, "rev-parse", "HEAD") != revision:
        raise ValueError("Kapitsa source revision mismatch")
    if git(source, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Kapitsa source/build inputs are dirty")
    actual = sha256(binary)
    if actual != runtime["binary_sha256"]:
        raise ValueError("Kapitsa executable hash mismatch")
    libraries = system_libraries(binary)
    if libraries != runtime["system_libraries"]:
        raise ValueError("Kapitsa system library inventory mismatch")
    derived = cfg["derived_source"]
    patch = (REPO / derived["patch"]).resolve(strict=True)
    if not patch.is_relative_to(REPO.resolve()) or sha256(patch) != derived["patch_sha256"]:
        raise ValueError("Kapitsa source patch mismatch")
    if git(source, "rev-parse", "HEAD^{tree}") != derived["source_tree"]:
        raise ValueError("Kapitsa derived tree mismatch")
    diff = subprocess.check_output(["git", "-C", str(source), "diff", derived["base_revision"], "HEAD"])
    if diff != patch.read_bytes():
        raise ValueError("Kapitsa source differs from the declared base/patch")
    argv = shlex.split(cfg["benchmark_launch_command"])
    if len(argv) < 2 or Path(argv[0]).resolve() != binary or argv[1] != "serve":
        raise ValueError("Kapitsa launch executable differs from runtime pin")

    def option(flag):
        if argv.count(flag) != 1 or argv.index(flag) + 1 >= len(argv):
            raise ValueError(f"Kapitsa requires one literal {flag}")
        return argv[argv.index(flag) + 1]

    required = {
        "--model": cfg["model_directory"], "--model-id": cfg["orchestration"]["served_model_id"],
        "--host": "127.0.0.1", "--port": str(cfg["orchestration"]["raw_port"]),
        "--context": str(cfg["context_cap"]), "--slots": "1", "--dflash": "none",
        "--disk-cache": "0", "--prefill-chunk": str(cfg["prefill_step_size"]),
    }
    if any(option(flag) != value for flag, value in required.items()):
        raise ValueError("Kapitsa launch settings differ from declared local diffusion profile")
    if {arg for arg in argv[2:] if arg.startswith("--")} != set(required) | {"--private", "--local"}:
        raise ValueError("Kapitsa launch has undeclared options")
    if any(argv.count(flag) != 1 for flag in ("--private", "--local")) or any(
        flag in argv for flag in ("--allow-switch", "--peer", "--engine", "--splash-binary")
    ):
        raise ValueError("Kapitsa must stay private/local without backend/model switching")
    environment = cfg["required_runner_environment"]
    if environment.get("NI_CLOVER_DECODE") != "diffusion" or environment.get("NI_LOCK_HELD") != "1":
        raise ValueError("Kapitsa requires explicit diffusion and an owned GPU lock")
    if environment.get("BENCH_GPU_LOCK") != runtime["gpu_lock"]:
        raise ValueError("Kapitsa caller/engine GPU lock paths differ")
    home = Path(environment["KAPITSA_HOME"])
    if not home.is_absolute() or str(home) != cfg["runtime_base"]:
        raise ValueError("Kapitsa requires an isolated absolute runtime base")
    for name, value in (os.environ | environment).items():
        if value and name.startswith(("DYLD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_FRAMEWORK_PATH")):
            raise ValueError("Kapitsa forbids dynamic-loader environment overrides")
    for name, value in os.environ.items():
        if (value and (name.startswith(("NI_", "NACE_", "KAPITSA_", "MTL_")) or name == "BENCH_GPU_LOCK")
                and value != environment.get(name)):
            raise ValueError(f"Kapitsa has undeclared tuning environment: {name}")
    for name, expected in cfg["model_metadata_hashes"].items():
        if sha256(Path(cfg["model_directory"]) / name) != expected:
            raise ValueError("Kapitsa model/template/generation metadata mismatch")
    if base_url is not None:
        if listener_binary(base_url) != binary:
            raise ValueError("Kapitsa listener does not match pinned executable")
        if any(os.environ.get(name) != value for name, value in environment.items()):
            raise ValueError("Kapitsa effective environment differs from committed profile")
        log = Path(runtime["server_log"]).read_text()
        if "Clover: block diffusion, 32-row blocks, threshold 0.95" not in log:
            raise ValueError("Kapitsa did not confirm actual Clover block diffusion")
    return {
        "verification": "source, derived patch/tree, binary, libraries, metadata verified"
        + (", listener and diffusion verified" if base_url is not None else ""),
        "engine": "kapitsa-metal", "repository": runtime["repository"], "revision": revision,
        "source_tree": derived["source_tree"], "base_revision": derived["base_revision"],
        "patch_sha256": derived["patch_sha256"], "binary_path": str(binary), "binary_sha256": actual,
        "system_libraries": libraries, "decoder": "block diffusion32 threshold0.95; no drafter",
        "environment": environment, "model_metadata_hashes": cfg["model_metadata_hashes"],
    }


def acquire_gpu_lock(cfg):
    lock = Path(cfg["runtime"]["gpu_lock"]).open("a+")  # noqa: SIM115 - ownership transfers to runner cleanup
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    return lock

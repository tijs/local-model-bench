"""Opt-in, reproducible clean-environment launch for final Mei speed runs.

The launcher is read from the recorded Git commit and supplied on stdin, so a
dirty working-tree launcher cannot affect the serving process. This module does
not inspect or persist the inherited environment. The recorded project and lock
files establish source provenance; they do not attest installed Python packages.
Run the qualifier through the project's documented `uv run --locked` workflow.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

MODE = "git-stdin-clean-env-v1"
LAUNCHER = "runner/start_mei_server.sh"
STOPPER = "runner/stop_mei_server.sh"
AUDITED_STOPPER_SHA256 = (
    "57eabaec443d422e0b4e60be3886f26cc2d1ef7ddb76fee7f12bbde5e84f528b"
)
AUDITED_MEI_REVISION = "f57c4ef0a5078d9399a855cfb2f36d0fd45a959a"
AUDITED_VMLX_REVISION = "f32e53b38a811c7c589cd110b9b7a643273d2da3"
AUDITED_REVISION_PAIRS = (
    (AUDITED_MEI_REVISION, AUDITED_VMLX_REVISION),
    (
        "b5451a8e5cf58e0d9bb6da142df39a9a98bd51b4",
        "9db62ce10416db4a33ff0108dca6fc00bdadfff7",
    ),
    (
        "360542ef23058f60f1164070752b8d13f3f2b97f",
        "9db62ce10416db4a33ff0108dca6fc00bdadfff7",
    ),
    (
        "2018275d4d1616e4753b4497513cf5ce5cd8aa46",
        "9db62ce10416db4a33ff0108dca6fc00bdadfff7",
    ),
    (
        "47fdf020426ed7e55ae14f0b2a13d0ac28b32796",
        "3fa3d7edbc98b31cad4e5589a35e58783c7561fe",
    ),
)
AUDITED_LAUNCHER_SHA256 = (
    "bfa28f23dee9e0321b042ed1bd9435a7096880bbb41bd2aafa18b2897e6b86cc"
)
# Retain reproducibility of committed pre-residency launch receipts.
AUDITED_LAUNCHER_SHA256S = frozenset(
    (
        AUDITED_LAUNCHER_SHA256,
        "cfc685b7f2203bd329dbc1f0b1e4e9130cc031b1c58ebc71b31476e8c18467b5",
    )
)
SOURCE_FILES = (
    "pyproject.toml",
    "uv.lock",
    "runner/bench_common.py",
    "runner/capacity_admission.py",
    "runner/mei_clean_speed.py",
    "runner/mei_provenance.py",
    "runner/owned_process.py",
    "runner/qualify_mei_release.py",
    "runner/run_mei_acceptance.py",
    "runner/run_standin_suite.py",
    "runner/supervise_bench.py",
)
PROFILE_KEYS = (
    "MEI_RUNTIME_BASE",
    "SWIFT_DETERMINISTIC_HASHING",
    "VMLX_ENABLE_UNSAFE_COMPILE",
    "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES",
    "VMLX_QWEN35_COMPILE_DECODE_REGIONS",
    "VMLX_QWEN4_EXP_COMPILE_ROUTED_MOE",
)
OPTIONAL_KEYS = {"TMPDIR", "LANG"}
FIXED_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def git_bytes(root: Path, revision: Any, path: str) -> bytes:
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{12,40}", revision):
        raise ValueError("clean launch requires a recorded Git revision")
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"missing committed clean-launch source: {path}")
    return result.stdout


def clean_environment(cfg: dict[str, Any]) -> dict[str, str]:
    """Accept only an explicit non-secret allowlist and matching profile keys."""
    spec = cfg.get("mei_clean_speed_launch")
    if not isinstance(spec, dict) or set(spec) != {
        "mode",
        "launcher_sha256",
        "environment",
    }:
        raise ValueError("invalid clean-speed launch declaration")
    if (
        spec["mode"] != MODE
        or not isinstance(spec["launcher_sha256"], str)
        or spec["launcher_sha256"] not in AUDITED_LAUNCHER_SHA256S
    ):
        raise ValueError("invalid clean-speed mode or launcher SHA256")
    if (
        cfg.get("mei_source_commit"),
        cfg.get("vmlx_commit"),
    ) not in AUDITED_REVISION_PAIRS:
        raise ValueError(
            "clean-speed environment requires an audit for these source revisions"
        )
    environment = spec["environment"]
    required = {"HOME", "PATH", *PROFILE_KEYS}
    if (
        not isinstance(environment, dict)
        or not required <= environment.keys()
        or environment.keys() - required - OPTIONAL_KEYS
        or not all(isinstance(v, str) for v in environment.values())
        or environment["PATH"] != FIXED_PATH
        or not Path(environment["HOME"]).is_absolute()
        or ("TMPDIR" in environment and not Path(environment["TMPDIR"]).is_absolute())
        or (
            "LANG" in environment
            and not re.fullmatch(r"[A-Za-z0-9_.@-]{1,32}", environment["LANG"])
        )
        or not Path(environment["MEI_RUNTIME_BASE"]).is_absolute()
        or any(
            not re.fullmatch(r"[0-9]+", environment[key])
            for key in PROFILE_KEYS
            if key != "MEI_RUNTIME_BASE"
        )
    ):
        raise ValueError(
            "clean-speed environment must use only the declared safe allowlist"
        )
    declared = cfg.get("required_runner_environment", {})
    if (
        not isinstance(declared, dict)
        or set(declared) != set(PROFILE_KEYS)
        or any(environment[key] != declared.get(key) for key in PROFILE_KEYS)
    ):
        raise ValueError(
            "clean-speed environment must match declared runtime and compile settings"
        )
    return dict(environment)


def committed_evidence(
    root: Path, revision: Any, *, verify_worktree: bool
) -> tuple[bytes, dict[str, str]]:
    """Bind source bytes to Git and, pre-launch, require loaded files match."""
    launcher = git_bytes(root, revision, LAUNCHER)
    hashes = {}
    for name in SOURCE_FILES:
        committed = git_bytes(root, revision, name)
        if verify_worktree and (root / name).read_bytes() != committed:
            raise ValueError(
                f"clean-speed runner source differs from committed revision: {name}"
            )
        hashes[name] = hashlib.sha256(committed).hexdigest()
    return launcher, hashes


def launch_receipt(
    root: Path,
    cfg: dict[str, Any],
    command: list[str],
    invocation: dict[str, Any],
    *,
    verify_worktree: bool,
) -> tuple[bytes, dict[str, Any]]:
    """Describe exactly the committed bytes, clean environment and bash argv."""
    if command[:2] != ["bash", LAUNCHER]:
        raise ValueError("clean-speed launch requires the audited launcher command")
    environment = clean_environment(cfg)
    revision = invocation.get("runner_git_sha")
    launcher, source_hashes = committed_evidence(
        root, revision, verify_worktree=verify_worktree
    )
    stopper = git_bytes(root, revision, STOPPER)
    if hashlib.sha256(stopper).hexdigest() != AUDITED_STOPPER_SHA256:
        raise ValueError("committed stop script differs from audited SHA256")
    launcher_sha = hashlib.sha256(launcher).hexdigest()
    if launcher_sha != cfg["mei_clean_speed_launch"]["launcher_sha256"]:
        raise ValueError("committed launcher SHA256 differs from the declared pin")
    actual_command = ["/bin/bash", "-s", "--", *command[2:]]
    receipt = {
        "mode": MODE,
        "runner_git_sha": revision,
        "launcher_path": LAUNCHER,
        "launcher_sha256": launcher_sha,
        "launcher_bytes": len(launcher),
        "source_sha256": source_hashes,
        "environment": environment,
        "declared_command": command,
        "actual_command": actual_command,
        "stopper_path": STOPPER,
        "stopper_sha256": AUDITED_STOPPER_SHA256,
        "stopper_bytes": len(stopper),
        "stop_command": [
            "/bin/bash",
            "-s",
            "--",
            "--runtime-base",
            environment["MEI_RUNTIME_BASE"],
            "--timeout",
            "4",
        ],
    }
    return launcher, receipt


def verify_receipt(
    root: Path,
    cfg: dict[str, Any],
    command: list[str],
    invocation: dict[str, Any],
    receipt: dict[str, Any],
    launcher_copy: Path,
    stopper_copy: Path,
) -> None:
    """Reproduce the declaration and committed bytes without live runtime files."""
    launcher, expected = launch_receipt(
        root, cfg, command, invocation, verify_worktree=False
    )
    stopper = git_bytes(root, invocation.get("runner_git_sha"), STOPPER)
    if (
        receipt != expected
        or launcher_copy.read_bytes() != launcher
        or stopper_copy.read_bytes() != stopper
    ):
        raise ValueError(
            "clean-speed launch receipt or executed launcher evidence changed"
        )

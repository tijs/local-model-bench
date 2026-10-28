"""Fail closed when a pinned Mei config would build/run different local code."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

BUILD_INPUTS = [
    "Sources",
    "Source",
    "Libraries",
    "Package.swift",
    "Package.resolved",
    "scripts/prepare_metallib.sh",
]


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(
            f"Mei provenance: git read failed for {repo}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def declared_path(argv: list[str], flag: str) -> Path:
    try:
        value = argv[argv.index(flag) + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(
            f"pinned Mei configs must declare a literal {flag} path"
        ) from error
    if "$" in value or value.startswith("--"):
        raise ValueError(f"pinned Mei config has unresolved {flag} path: {value!r}")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"pinned Mei config requires absolute {flag} path")
    return path.resolve()


def clean_revision(repo: Path, expected: str, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError(f"{label} pin must be a full lowercase Git revision")
    actual = git(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise ValueError(
            f"{label} source mismatch: expected {expected}, found {actual} at {repo}; use the pinned checkout or a new committed config"
        )
    dirty = git(
        repo, "status", "--porcelain", "--untracked-files=all", "--", *BUILD_INPUTS
    )
    if dirty:
        raise ValueError(f"{label} has modified/untracked build inputs at {repo}")
    return actual


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def listener_binary(base_url: str) -> Path:
    url = urlsplit(base_url)
    if url.hostname not in {"127.0.0.1", "localhost", "::1"} or not url.port:
        raise ValueError(
            "Mei runtime provenance requires an explicit local endpoint port"
        )
    result = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{url.port}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids = set(result.stdout.split())
    if len(pids) != 1:
        raise ValueError("Mei runtime provenance requires exactly one local listener")
    pid = pids.pop()
    if not pid.isdigit():
        raise ValueError("invalid listener PID in Mei provenance")
    result = subprocess.run(
        ["ps", "-p", pid, "-o", "comm="], capture_output=True, text=True, check=False
    )
    if result.returncode or not result.stdout.strip():
        raise ValueError("cannot identify the Mei listener executable")
    return Path(result.stdout.strip()).resolve()


def verify_mei_runtime(
    cfg: dict[str, Any], *, base_url: str | None = None
) -> dict[str, Any] | None:
    if cfg.get("inference_engine") != "mei":
        return None
    expected = cfg.get("mei_source_commit")
    if not expected:
        if cfg.get("benchmark_scope") == "peixinho-standin-v1":
            raise ValueError("stand-in Mei runs require mei_source_commit")
        return {"verification": "unverified legacy config: no Mei source pin"}
    argv = shlex.split(cfg.get("benchmark_launch_command", ""))
    repo = declared_path(argv, "--mei-repo")
    source = clean_revision(repo, expected, "Mei")
    lock = json.loads((repo / "Package.resolved").read_text())
    pins = [x for x in lock.get("pins", []) if x.get("identity") == "vmlx-swift"]
    if len(pins) != 1:
        raise ValueError("Mei lockfile must contain exactly one vmlx-swift pin")
    dependency = pins[0]["state"]["revision"]
    declared = cfg.get("vmlx_commit") or cfg.get("mei_commit")
    if declared and declared != dependency:
        raise ValueError(
            f"vmlx pin mismatch: config declares {declared}, Mei resolves {dependency}"
        )
    result: dict[str, Any] = {
        "verification": "source pins verified",
        "mei_source_commit": source,
        "vmlx_commit": dependency,
        "mei_repo": str(repo),
    }
    if base_url is not None:
        build = declared_path(argv, "--build-dir")
        clean_revision(
            build / "checkouts/vmlx-swift", dependency, "vmlx build checkout"
        )
        binary = build / "release/mei"
        if listener_binary(base_url) != binary.resolve():
            raise ValueError(
                "Mei listener executable does not match the configured build"
            )
        result.update(
            verification="source, dependency and listener verified",
            binary_path=str(binary.resolve()),
            binary_sha256=sha256(binary),
            metallib_sha256=sha256(build / "release/mlx.metallib"),
        )
    return result

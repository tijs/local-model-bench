"""Verify a pinned llama.cpp source, executable, shared libraries and listener."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Any

from mei_provenance import git, listener_binary, sha256


def verify_llama_runtime(
    cfg: dict[str, Any], *, base_url: str | None = None
) -> dict[str, Any] | None:
    if cfg.get("inference_engine") != "llama.cpp":
        return None
    runtime = cfg.get("runtime", {})
    revision = runtime.get("revision", "")
    if not isinstance(revision, str) or not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("llama.cpp requires a full source revision")
    source = Path(runtime["source_directory"]).resolve(strict=True)
    binary = Path(runtime["binary"]).resolve(strict=True)
    if git(source, "rev-parse", "HEAD") != revision:
        raise ValueError("llama.cpp source revision mismatch")
    if git(source, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("llama.cpp source/build inputs are dirty")
    argv = shlex.split(cfg["benchmark_launch_command"])
    if not argv or Path(argv[0]).resolve() != binary:
        raise ValueError("llama.cpp launch executable differs from runtime pin")
    if any(
        os.environ.get(name)
        for name in (
            "DYLD_LIBRARY_PATH",
            "DYLD_INSERT_LIBRARIES",
            "DYLD_FRAMEWORK_PATH",
        )
    ):
        raise ValueError(
            "llama.cpp benchmark forbids dynamic-loader environment overrides"
        )
    actual = sha256(binary)
    if actual != runtime.get("binary_sha256"):
        raise ValueError("llama.cpp executable hash mismatch")
    library_paths = sorted(binary.parent.glob("*.dylib"))
    if any(not p.resolve().is_relative_to(binary.parent) for p in library_paths):
        raise ValueError("llama.cpp shared library symlink escapes the pinned build")
    libraries = {p.name: sha256(p) for p in library_paths}
    if not libraries or libraries != runtime.get("shared_libraries"):
        raise ValueError("llama.cpp shared library inventory/hash mismatch")
    if base_url is not None and listener_binary(base_url) != binary:
        raise ValueError("llama.cpp listener does not match pinned executable")
    return {
        "verification": "source, binary and libraries verified"
        if base_url is None
        else "source, binary, libraries and listener verified",
        "repository": runtime["repository"],
        "revision": revision,
        "binary_path": str(binary),
        "binary_sha256": actual,
        "shared_libraries": libraries,
    }

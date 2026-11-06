"""macOS diagnostic: invalidate clean read-only model cache, verify uncached hashes.

No model bytes are changed. No global purge, dirty mapping or runtime is used.
Run only with all benchmark model servers stopped. This is an explicit cache-state
experiment, not a default hashing policy or a scored benchmark.
"""

import argparse
import ctypes
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PREP = Path(__file__).resolve().parents[1]
lib = ctypes.CDLL(None, use_errno=True)
lib.mmap.restype = ctypes.c_void_p
lib.mmap.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_longlong,
]
lib.msync.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
lib.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
lib.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
PAGE = os.sysconf("SC_PAGE_SIZE")


def resident_pages(fd, size, invalidate=False):
    if not size:
        return 0
    address = lib.mmap(None, size, 1, 1, fd, 0)  # PROT_READ, MAP_SHARED
    if address == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_errno(), "read-only mmap failed")
    try:
        if invalidate and lib.msync(
            address, size, 2
        ):  # MS_INVALIDATE, clean mapping only
            raise OSError(ctypes.get_errno(), "clean-page invalidation failed")
        vector = (ctypes.c_ubyte * ((size + PAGE - 1) // PAGE))()
        if lib.mincore(address, size, vector):
            raise OSError(ctypes.get_errno(), "mincore failed")
        return sum(value & 1 for value in vector)
    finally:
        if lib.munmap(address, size):
            raise OSError(ctypes.get_errno(), "munmap failed")


def stamp(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or args.output.exists():
        raise ValueError("requires macOS and a fresh output")
    processes = subprocess.check_output(["ps", "-axo", "comm="], text=True)
    if any(
        line.strip().endswith(("/mei", "/llama-server"))
        for line in processes.splitlines()
    ):
        raise ValueError("all model servers must be stopped")
    rows = []
    models = Path.home() / ".local/share/local-model-bench/mei-models"
    for model in ("ornith", "qwen", "groot"):
        manifest = PREP / f"{model}-media-prefix-pre-run-model-hashes.json"
        declared = json.loads(manifest.read_text())
        directory = Path(declared["directory"])
        if directory.parent != models or directory.resolve() != directory:
            raise ValueError(
                "requires the existing direct nonsymlinked model directory"
            )
        for entry in declared["files"]:
            name = entry["file"]
            if Path(name).name != name:
                raise ValueError("requires a direct model file")
            path = directory / name
            with path.open("rb", buffering=0) as stream:
                before = os.fstat(stream.fileno())
                if path.resolve() != path or before.st_size != entry["bytes"]:
                    raise ValueError(f"model identity changed: {path}")
                cached_before = resident_pages(stream.fileno(), before.st_size)
                cached_after_invalidate = resident_pages(
                    stream.fileno(), before.st_size, True
                )
                fcntl.fcntl(stream.fileno(), 48, 1)  # F_NOCACHE
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
                cached_after_hash = resident_pages(stream.fileno(), before.st_size)
                if (
                    digest != entry["sha256"]
                    or stamp(before) != stamp(os.fstat(stream.fileno()))
                    or stamp(before) != stamp(path.stat())
                ):
                    raise ValueError(f"model changed during verification: {path}")
                rows.append(
                    {
                        "model": model,
                        **entry,
                        "cached_pages_before": cached_before,
                        "cached_pages_after_invalidate": cached_after_invalidate,
                        "cached_pages_after_hash": cached_after_hash,
                        "bytes_and_timestamps_unchanged": True,
                    }
                )
                print(
                    f"{model} {name}: {cached_before} -> {cached_after_hash} cached pages; hash unchanged",
                    flush=True,
                )
    args.output.write_text(
        json.dumps(
            {
                "page_bytes": PAGE,
                "scope": "Explicit read-only per-file cache-state diagnostic; no model byte changes or global purge",
                "files": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

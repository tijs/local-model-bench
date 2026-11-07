"""Stage or verify the exact queued text-only Gemma snapshot on Expansion."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from model_storage import model_root

DESTINATION = Path("/Volumes/Expansion/local-model-bench/mei-models")
DIRECTORY = "Gemma-4-26B-A4B-it-RAM-13GB-MLX-a29dabb"


def pin():
    path = HERE / "gemma-hub-files.json"
    data = path.read_bytes()
    if data != subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT)}"], cwd=ROOT
    ):
        raise ValueError("Gemma publisher manifest differs from the committed pin")
    return json.loads(data)


def verify_file(path, row):
    size = row["bytes"]
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError(f"wrong file type/size: {path}")
    with path.open("rb") as f:
        if row["sha256"] is not None:
            actual = hashlib.file_digest(f, "sha256").hexdigest()
            if actual != row["sha256"]:
                raise ValueError(f"publisher SHA-256 mismatch: {path}")
        else:
            data = f.read()
            git_blob = hashlib.sha1(
                f"blob {size}\0".encode() + data, usedforsecurity=False
            ).hexdigest()
            if git_blob != row["git_blob"]:
                raise ValueError(f"publisher Git blob mismatch: {path}")
            actual = hashlib.sha256(data).hexdigest()
    return {"file": row["file"], "bytes": size, "sha256": actual}


def verify_or_stage(*, stage=False):
    manifest = pin()
    base = model_root("mei")
    if base != DESTINATION or base.resolve(strict=True) != DESTINATION:
        raise ValueError("expected the direct Expansion model store")
    directory = base / DIRECTORY
    if directory.is_symlink():
        raise ValueError("Gemma staging path is a symlink")
    if stage:
        required = sum(
            row["bytes"]
            for row in manifest["files"]
            if not (directory / row["file"]).exists()
        )
        if shutil.disk_usage(base).free < required + 23 * 1024**3:
            raise ValueError("insufficient headroom for Gemma staging")
        directory.mkdir(exist_ok=True)
    files = []
    for row in manifest["files"]:
        name = row["file"]
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError(f"expected a flat repository file: {name}")
        file = directory / name
        if stage and not file.exists():
            temp = directory / f"{name}.partial"
            if file.is_symlink() or temp.is_symlink():
                raise ValueError(f"unsafe staged file: {file}")
            if not temp.exists() or temp.stat().st_size != row["bytes"]:
                url = f"https://huggingface.co/{manifest['repository']}/resolve/{manifest['revision']}/{name}"
                print(
                    f"Stage {name} ({row['bytes']} bytes)", file=sys.stderr, flush=True
                )
                subprocess.run(
                    [
                        "curl",
                        "--fail",
                        "--location",
                        "--retry",
                        "2",
                        "--continue-at",
                        "-",
                        "--silent",
                        "--show-error",
                        "--output",
                        str(temp),
                        url,
                    ],
                    check=True,
                )
            verified = verify_file(temp, row)
            file.hardlink_to(temp)
            temp.unlink()
        else:
            verified = verify_file(file, row)
        files.append(verified)
    if {p.name for p in directory.iterdir()} != {row["file"] for row in files}:
        raise ValueError("unexpected files in the staged snapshot")
    return {
        "directory": str(directory),
        "revision": manifest["revision"],
        "files": files,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_or_stage(stage=args.stage), indent=2))

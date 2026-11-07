"""Bind the verified Expansion cutover to the four benchmark checkpoint pins."""

import argparse
import hashlib
import json
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
VOLUME = Path("/Volumes/Expansion")
STORE = VOLUME / "local-model-bench"
LEGACY = Path.home() / ".local/share/local-model-bench"
EVIDENCE = STORE / "model-store-migration-20261107"
UUID = "EA591329-8CD6-4171-9623-31C3FB8F335C"
CONFIGS = ROOT / "configs/mei-0.11.0-comparison-20261107"
RUNTIME = ROOT / "artifacts/mei-upstream-qualification-20261106"
sys.path.insert(0, str(ROOT / "runner"))
from model_storage import model_root


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def verify_store(label: str, receipt: dict) -> dict:
    base = STORE / label
    alias = LEGACY / label
    engine = {"gguf-models": "gguf", "mei-models": "mei"}[label]
    if (
        receipt["legacy_path"] != str(alias)
        or receipt["canonical_path"] != str(base)
        or not alias.is_symlink()
        or alias.resolve(strict=True) != base
        or base.stat().st_dev != VOLUME.stat().st_dev
        or model_root(engine).resolve(strict=True) != base
    ):
        raise ValueError(f"unexpected host model store or alias: {label}")
    raw = (EVIDENCE / f"{label}.sha256-manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["manifest_sha256"]:
        raise ValueError(f"migration manifest digest changed: {label}")
    manifest = json.loads(raw)
    files = [row for row in manifest.values() if row[0] == "file"]
    if (
        len(files) != receipt["files"]
        or sum(row[2] for row in files) != receipt["bytes"]
        or sum(row[0] == "link" for row in manifest.values()) != receipt["links"]
    ):
        raise ValueError(f"migration counts changed: {label}")
    return manifest


def verify_checkpoint(model: str, manifest: dict) -> dict:
    cfg = yaml.safe_load((CONFIGS / f"{model}-seed17.yaml").read_text())
    command = shlex.split(cfg["benchmark_launch_command"])
    gguf = model == "logics"
    flag = "--model" if gguf else "--model-dir"
    model_path = Path(command[command.index(flag) + 1])
    base = STORE / ("gguf-models" if gguf else "mei-models")
    canonical = model_path.resolve(strict=True)
    canonical.relative_to(base)
    if gguf:
        entries = [(canonical, cfg["model_bytes"], cfg["model_sha256"])]
    else:
        before = load(RUNTIME / f"{model}-media-prefix-pre-run-model-hashes.json")
        if Path(before["directory"]).resolve(strict=True) != canonical:
            raise ValueError(f"checkpoint path no longer matches pre-run pin: {model}")
        entries = [
            (canonical / row["file"], row["bytes"], row["sha256"])
            for row in before["files"]
        ]
    for path, size, digest in entries:
        row = manifest[str(path.relative_to(base))]
        if (
            row[0] != "file"
            or row[2:] != [size, digest]
            or path.is_symlink()
            or path.stat().st_size != size
        ):
            raise ValueError(f"migrated model file differs from its pin: {path}")
    return {
        "model": model,
        "model_revision": cfg["source_revision"],
        "canonical_path": str(canonical),
        "pinned_files_checked": len(entries),
    }


def verify() -> dict:
    device = plistlib.loads(
        subprocess.check_output(["diskutil", "info", "-plist", VOLUME])
    )
    outcome = load(EVIDENCE / "completed.json")
    if (
        device["MountPoint"] != str(VOLUME)
        or device["VolumeUUID"] != UUID
        or outcome["volume_uuid"] != UUID
        or outcome["status"] != "complete"
    ):
        raise ValueError("the expected volume or terminal migration is missing")
    labels = ("gguf-models", "mei-models")
    manifests = {}
    for label, receipt in zip(labels, outcome["stores"], strict=True):
        if receipt != load(EVIDENCE / f"{label}.receipt.json"):
            raise ValueError(f"migration receipts differ: {label}")
        manifests[label] = verify_store(label, receipt)
    return outcome | {
        "active_checkpoints": [
            verify_checkpoint(
                model, manifests["gguf-models" if model == "logics" else "mei-models"]
            )
            for model in ("qwen", "ornith", "groot", "logics")
        ],
        "verification": "Checked cutover and terminal migration hashes against pinned model-file digests; guarded runs separately rehash every used checkpoint after execution.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = json.dumps(verify(), indent=2) + "\n"
    if args.write:
        with (PREP / "model-store-migration.json").open("x") as stream:
            stream.write(data)
    else:
        print(data, end="")


if __name__ == "__main__":
    main()

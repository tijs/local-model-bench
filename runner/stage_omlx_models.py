#!/usr/bin/env python3
"""Stage exact Hugging Face MLX snapshots into oMLX's isolated model root."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from huggingface_hub import scan_cache_dir  # type: ignore[import-not-found]

ARTIFACTS = {
    "lfm25-8b-a1b-oq4-fp16": ("RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16", "c6d776a30db23fc34644ec8625ed1f0b1d51bfa1", 4_994_820_300),
    "ornith-15-9b-oq4e-fp16": ("scottlowry/Ornith-1.5-9B-oQ4e-fp16", "5a886bbb0c202641e3c278cb4001058f2420827a", 6_968_451_633),
    "qwen38-27b-oq4e-fp16-mtp": ("Jundot/Qwen3.8-27B-oQ4e-fp16-mtp", "569439f7b576fcb8795258855466fee2acd8ea70", 17_916_345_286),
    "lfm25-26b-mlx-bf16": ("LiquidAI/LFM2.5-2.6B-MLX-bf16", "f2d32094cdd69ed7adb85a4b44accfc8770cd655", 5_412_363_419),
    "lfm25-8b-a1b-mlx-bf16": ("LiquidAI/LFM2.5-8B-A1B-MLX-bf16", "f249fa04c32c629c9156e0e1e4ca139b8c06c4f2", 16_956_562_706),
    "qwen3-coder-30b-a3b-4bit": ("mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit", "6e302ea604ad9ab206367e2c501d1571023e7b6d", 17_197_116_337),
    "qwen38-27b-mlx-4bit": ("mlx-community/Qwen3.8-27B-4bit", "3e6447f082e89cc7f0bc6e5441afd38dfce760ff", 16_081_506_075),
    "ternary-bonsai-27b-mlx-2bit": ("prism-ml/Ternary-Bonsai-27B-mlx-2bit", "70f75f3ad081ab840a42f3304c02c27e7f89bfb7", 8_521_060_101),
    "laguna-xs-21-mlx-4bit": ("mlx-community/Laguna-XS-2.1-4bit", "c42e0a8f8d504ceacde015a535dcb286d65c8799", 18_829_718_321),
}


def complete_snapshot(snapshot: Path) -> tuple[bool, list[str]]:
    missing: list[str] = []
    config = snapshot / "config.json"
    if not config.is_file():
        missing.append("config.json")
    index = snapshot / "model.safetensors.index.json"
    if index.is_file():
        try:
            shards = set(json.loads(index.read_text()).get("weight_map", {}).values())
        except (OSError, json.JSONDecodeError) as exc:
            return False, [f"invalid model.safetensors.index.json: {exc}"]
        missing.extend(sorted(name for name in shards if not (snapshot / name).is_file()))
    elif not any(snapshot.glob("*.safetensors")):
        missing.append("*.safetensors or model.safetensors.index.json")
    return not missing, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, default=Path("~/.local/share/local-model-bench/omlx-models").expanduser())
    parser.add_argument("--manifest", type=Path, default=Path("results/omlx/staging-manifest.json"))
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    args.model_root.mkdir(parents=True, exist_ok=True)

    cache = scan_cache_dir()
    revisions: dict[tuple[str, str], tuple[Path, int]] = {}
    for repo in cache.repos:
        for revision in repo.revisions:
            revisions[(repo.repo_id, revision.commit_hash)] = (revision.snapshot_path, revision.size_on_disk)

    manifest = {"created_epoch": time.time(), "model_root": str(args.model_root.resolve()), "artifacts": {}}
    blocked = False
    for slug, (repo_id, revision, expected_bytes) in ARTIFACTS.items():
        entry = {"repo_id": repo_id, "revision": revision, "expected_bytes": expected_bytes}
        cached = revisions.get((repo_id, revision))
        if cached is None:
            entry.update(status="missing", error="exact revision absent from local Hugging Face cache")
            blocked = True
            manifest["artifacts"][slug] = entry
            continue
        snapshot, scanned_bytes = cached
        complete, missing = complete_snapshot(snapshot)
        entry.update(snapshot=str(snapshot), scanned_bytes=scanned_bytes)
        if not complete:
            entry.update(status="incomplete", missing=missing)
            blocked = True
            manifest["artifacts"][slug] = entry
            continue
        target = args.model_root / slug
        if target.is_symlink() and target.resolve() == snapshot.resolve():
            entry["status"] = "staged"
        elif target.exists() or target.is_symlink():
            if not args.replace:
                entry.update(status="conflict", error=f"target already exists: {target}")
                blocked = True
                manifest["artifacts"][slug] = entry
                continue
            if target.is_dir() and not target.is_symlink():
                entry.update(status="conflict", error="refusing to replace a real directory")
                blocked = True
                manifest["artifacts"][slug] = entry
                continue
            target.unlink()
            target.symlink_to(snapshot, target_is_directory=True)
            entry["status"] = "staged"
        else:
            temporary = args.model_root / f".{slug}.tmp-{os.getpid()}"
            temporary.symlink_to(snapshot, target_is_directory=True)
            temporary.replace(target)
            entry["status"] = "staged"
        entry["served_path"] = str(target)
        manifest["artifacts"][slug] = entry

    manifest["status"] = "blocked" if blocked else "complete"
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())

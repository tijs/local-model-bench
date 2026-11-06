"""Preserve this campaign's terminal attempt and remove only its owned KV."""

import argparse
import hashlib
import json
import shlex
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from mei_provenance import verify_mei_runtime


def save(output, name, value):
    path = output / name
    if path.exists():
        raise ValueError(f"refuse existing evidence: {path}")
    path.write_text(json.dumps(value, indent=2) + "\n")


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-manifest", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / "artifacts")
    outcome = json.loads((output / "outcome.json").read_text())
    if outcome.get("returncode") is None:
        raise ValueError("requires a terminal owned child outcome")
    ports = subprocess.run(
        ["lsof", "-nP", "-iTCP:8017", "-iTCP:8024", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    if ports.returncode != 1 or ports.stdout:
        raise ValueError("benchmark ports must be free before preservation/cleanup")
    processes = subprocess.check_output(["ps", "-axo", "comm="], text=True)
    if any(line.strip().endswith("/mei") for line in processes.splitlines()):
        raise ValueError("Mei must have exited before KV cleanup")
    cfg = yaml.safe_load((output / "config.yaml").read_text())
    base = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
    owned = Path.home() / ".local/share/local-model-bench/mei-runtime"
    relative = base.relative_to(owned)
    allowed = {
        f"{model}-upstream011-media-prefix-off-native-20261106"
        for model in ("qwen", "ornith", "groot")
    }
    allowed.add("ornith-upstream011-cold-hash-native-20261106")
    allowed.add("ornith-upstream011-cold-hash-on-native-20261106")
    allowed.update(
        f"{model}-upstream011-media-prefix-on-native-20261106"
        for model in ("qwen", "groot")
    )
    allowed.update(
        f"{model}-upstream011-media-prefix-on-pinned-native-20261106"
        for model in ("qwen", "groot")
    )
    allowed.update(
        f"{model}-upstream011-speed-{cell}-20261106"
        for model in ("qwen", "ornith", "groot")
        for cell in ("a1", "b1", "b2", "a2")
    )
    allowed.update(
        f"{model}-upstream011-paged-io-native-20261106"
        for model in ("qwen", "ornith", "groot")
    )
    allowed.update(f"groot-upstream011-phase-{arm}-20261106" for arm in ("a", "b"))
    allowed.update(
        f"groot-upstream011-phase-mirror-{arm}-20261106" for arm in ("a", "b")
    )
    if len(relative.parts) != 1 or relative.name not in allowed:
        raise ValueError("requires this campaign's exact owned runtime directory")
    if base.resolve() != base or (base / "server.pid").exists():
        raise ValueError("runtime must be nonsymlinked and exited")
    if (output / "owned-kv-cleanup.json").exists():
        raise ValueError("cleanup receipt already exists")
    for name in ("server.log", "requests.jsonl"):
        destination = output / name
        if destination.exists():
            raise ValueError(f"refuse existing log: {destination}")
        shutil.copy2(base / "logs" / name, destination)
    save(output, "post-run-runtime-verification.json", verify_mei_runtime(cfg))
    before = json.loads(args.model_manifest.read_text())
    argv = shlex.split(cfg["benchmark_launch_command"])
    declared_model = Path(argv[argv.index("--model-dir") + 1]).resolve()
    if Path(before["directory"]).resolve() != declared_model:
        raise ValueError("model hash manifest does not match the launched model")
    if "--kv-cache-dir" in argv:
        if (
            argv.count("--kv-cache-dir") != 1
            or Path(argv[argv.index("--kv-cache-dir") + 1]) != base / "kv"
        ):
            raise ValueError("KV launch path does not match the owned runtime")
    else:
        if (
            argv.count("--cache-mode") != 1
            or argv[argv.index("--cache-mode") + 1] != "off"
        ):
            raise ValueError("absent KV path requires explicit cache mode off")
        if (base / "kv").exists() or (base / "kv").is_symlink():
            raise ValueError(
                "cache-off runtime contains unexpected KV data; refuse cleanup"
            )
    rows = []
    for row in before["files"]:
        file = Path(before["directory"]) / row["file"]
        with file.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if sha != row["sha256"] or file.stat().st_size != row["bytes"]:
            raise ValueError(f"model file changed: {file}")
        rows.append(row | {"matches": True})
    save(
        output,
        "post-run-model-hashes.json",
        {"directory": before["directory"], "all_match": True, "files": rows},
    )
    kv = base / "kv"
    if kv.is_symlink() or kv.resolve() != base / "kv":
        raise ValueError("KV path must remain inside the owned runtime")
    inventory: list[dict[str, Any]] = []
    databases = []
    for path in sorted(kv.rglob("*")):
        if path.is_symlink():
            raise ValueError("refuse symlink inside owned KV")
        if not path.is_file():
            continue
        inventory.append(
            {
                "file": str(path.relative_to(base)),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
        if path.suffix in (".sqlite", ".sqlite3", ".db"):
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                tables = [
                    row[0]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                ]
                counts = {}
                for table in tables:
                    quoted = '"' + table.replace('"', '""') + '"'
                    counts[table] = db.execute(
                        f"SELECT COUNT(*) FROM {quoted}"
                    ).fetchone()[0]
                databases.append(
                    {"file": str(path.relative_to(base)), "rows_per_table": counts}
                )
    save(output, "owned-kv-inventory.json", inventory)
    save(output, "owned-kv-index-summary.json", databases)
    if kv.exists():
        shutil.rmtree(kv)
    save(
        output,
        "owned-kv-cleanup.json",
        {
            "runtime_base": str(base),
            "server_exited": True,
            "files": len(inventory),
            "bytes": sum(row["bytes"] for row in inventory),
            "deleted": not kv.exists(),
        },
    )
    print(
        f"Preserved logs, {len(rows)} model hashes and KV metadata; removed {sum(row['bytes'] for row in inventory)} owned bytes."
    )


if __name__ == "__main__":
    main()

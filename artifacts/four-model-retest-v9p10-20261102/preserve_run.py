"""Post-exit preservation, exact hashes and owned KV cleanup for this campaign."""

import hashlib
import json
import shlex
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from llama_provenance import verify_llama_runtime
from mei_provenance import verify_mei_runtime

slug, seed = sys.argv[1:]
assert slug in ("qwen", "ornith", "groot", "logics") and seed in ("17", "29")
OUT = ROOT / f"artifacts/{slug}-four-v9p10-seed{seed}-20261102"
PREP = Path(__file__).resolve().parent
cfg = yaml.safe_load((OUT / "config.yaml").read_text())
assert json.loads((OUT / "outcome.json").read_text())["returncode"] == 0
ports = subprocess.run(
    ["lsof", "-nP", "-iTCP:8017", "-iTCP:8024", "-sTCP:LISTEN"],
    check=False,
    capture_output=True,
    text=True,
)
assert ports.returncode == 1 and not ports.stdout, ports.stdout


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + "\n")


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


old = json.loads((PREP / f"{slug}-staged-model-hashes.json").read_text())
if slug == "logics":
    items = [(Path(old["file"]), old)]
else:
    items = [(Path(old["directory"]) / item["file"], item) for item in old["files"]]
files = []
for path, item in items:
    sha = digest(path)
    assert sha == item["sha256"] and path.stat().st_size == item["bytes"], str(path)
    files.append(
        {
            "file": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha,
            "matches": True,
        }
    )
save("post-run-model-hashes.json", {"all_match": True, "files": files})
if slug == "logics":
    save("post-run-runtime-verification.json", verify_llama_runtime(cfg))
    shutil.copy2(
        f"/tmp/bench_four-model-v9p10-20261102_logics-seed{seed}_server.log",
        OUT / "server.log",
    )
    print("Preserved llama.cpp logs/model/runtime hashes; no owned disk KV tier.")
else:
    args = shlex.split(cfg["benchmark_launch_command"])
    base = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
    assert (
        base
        == Path.home()
        / f".local/share/local-model-bench/mei-runtime/{slug}-four-v9p10-seed{seed}-20261102"
    )
    assert not (base / "server.pid").exists()
    save("post-run-runtime-verification.json", verify_mei_runtime(cfg))
    for name in ("server.log", "requests.jsonl"):
        shutil.copy2(base / "logs" / name, OUT / name)
    inventory = [
        {"file": str(p.relative_to(base)), "bytes": p.stat().st_size}
        for p in sorted(base.rglob("*"))
        if p.is_file()
    ]
    save("post-run-runtime-inventory.json", inventory)
    kv = base / "kv"
    summaries = []
    for db in kv.glob("*.sqlite*"):
        if db.suffix not in (".sqlite", ".sqlite3", ".db"):
            continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for name, schema in con.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table'"
        ):
            safe = '"' + name.replace('"', '""') + '"'
            count = con.execute(f"SELECT count(*) FROM {safe}").fetchone()[0]
            summaries.append(
                {"database": db.name, "table": name, "schema": schema, "rows": count}
            )
        con.close()
    # Some backend revisions name the index cache.db rather than *.sqlite.
    for db in kv.glob("*.db"):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for name, schema in con.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table'"
        ):
            safe = '"' + name.replace('"', '""') + '"'
            summaries.append(
                {
                    "database": db.name,
                    "table": name,
                    "schema": schema,
                    "rows": con.execute(f"SELECT count(*) FROM {safe}").fetchone()[0],
                }
            )
        con.close()
    save("cache-index-summary.json", summaries)
    owned = [x for x in inventory if x["file"].startswith("kv/")]
    before = shutil.disk_usage(base).free
    assert kv.is_dir() and not kv.is_symlink()
    shutil.rmtree(kv)
    receipt = {
        "scope": "Only generated KV of exited campaign run; logs, index summary, inventory, model and task evidence preserved",
        "path": str(kv),
        "removed_files": len(owned),
        "removed_logical_bytes": sum(x["bytes"] for x in owned),
        "disk_free_bytes_before": before,
        "disk_free_bytes_after": shutil.disk_usage(base).free,
        "kv_directory_absent": not kv.exists(),
    }
    save("owned-cache-cleanup.json", receipt)
    print(json.dumps(receipt))

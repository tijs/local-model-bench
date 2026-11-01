"""Reproduce the guarded installed-asset smoke; never writes task score rows.

Run from the repository root with uv run --locked python <this-file>.
The shared parent owns the complete process group and actual resource guards.
Context is deliberately skipped: this is installation diagnostics, not admission.
"""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "runner"))

from run_mei_acceptance import committed_native_config, monitor_child, wait_ready

CONFIG = REPO / "configs/mei-rc2-native-20261101/groot-installed-smoke.yaml"
OUTPUT = REPO / "artifacts/mei-rc2-installed-groot-smoke-20261101"


def main():
    cfg, content = committed_native_config(CONFIG)
    asset = cfg["installed_asset"]
    for name in ("binary", "metallib"):
        with Path(asset[name]).open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == asset[name + "_sha256"]
    program = Path(asset["probe_program"])
    expected = subprocess.check_output([
        "git", "-C", str(program.parents[1]), "show", "v0.10.0-rc.2:tools/probe_mei.py",
    ])
    assert program.read_bytes() == expected
    runtime = Path(asset["runtime_base"])
    if "--child" not in sys.argv:
        for port in (8017, 8024):
            with socket.socket() as connection:
                connection.settimeout(0.5)
                assert connection.connect_ex(("127.0.0.1", port)) != 0, f"occupied port {port}"
        assert not runtime.exists(), "choose a fresh isolated runtime base"
        args = argparse.Namespace(output=OUTPUT, deadline=600, skip_context=True, skip_cache=False)
        rc = monitor_child(cfg, content, args, [sys.executable, str(Path(__file__).resolve()), "--child"])
        # Parent has stopped the owned group, including any interrupted server.
        kv = runtime / "kv"
        inventory = [{"file": str(p.relative_to(kv)), "bytes": p.stat().st_size}
                     for p in sorted(kv.rglob("*")) if p.is_file()]
        (OUTPUT / "owned-kv-cleanup.json").write_text(json.dumps({
            "directory": str(kv), "files": inventory,
            "total_bytes": sum(int(row["bytes"]) for row in inventory),
            "action": "removed only installed-smoke owned KV; weights retained",
        }, indent=2) + "\n")
        if kv.exists():
            shutil.rmtree(kv)
        return rc

    assert os.environ.get("BENCH_ADMITTED_CONFIG_SHA256") == hashlib.sha256(content).hexdigest()
    runtime.mkdir(parents=True, exist_ok=False)
    record = {"status": "failed", "installed_asset": asset,
              "probe_sha256": hashlib.sha256(expected).hexdigest()}
    with (OUTPUT / "server.log").open("x") as log:
        server = subprocess.Popen(shlex.split(cfg["benchmark_launch_command"]), stdout=log,
                                  stderr=subprocess.STDOUT)
        try:
            wait_ready(server, cfg["benchmark_endpoint"])
            result = subprocess.run([
                sys.executable, str(program), "--base-url", cfg["benchmark_endpoint"],
                "--model", cfg["model"], "--tokenizer",
                "/Users/tijs/.local/share/local-model-bench/mei-models/Groot-19B-A3B-textonly-publication-20261101",
                "--output", str(OUTPUT / "probe.json"), "--skip-context",
            ], check=False, timeout=450)
            record["probe_rc"] = result.returncode
            record["status"] = "passed" if result.returncode == 0 else "failed"
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
            (OUTPUT / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

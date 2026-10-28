"""Owned native release admission; run under the existing resource supervisor."""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from mei_provenance import verify_mei_runtime

OUT = Path(__file__).resolve().parent
CFG = ROOT / "configs/Flint-JANGH2-release-20261029/mei.yaml"
cfg = yaml.safe_load(CFG.read_text())
verify_mei_runtime(cfg)
env = dict(os.environ, **cfg["required_runner_environment"])
env["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
with (OUT / "launch.log").open("w") as log:
    child = subprocess.Popen(
        cfg["benchmark_launch_command"],
        shell=True,
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for attempt in range(180):
            if child.poll() is not None:
                raise RuntimeError(f"launcher exited: {child.returncode}")
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8024/health", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            time.sleep(5)
        else:
            raise TimeoutError("release server never healthy")
        identity = verify_mei_runtime(cfg, base_url=cfg["benchmark_endpoint"])
        (OUT / "runtime-identity.json").write_text(json.dumps(identity, indent=2))
        subprocess.run(
            [
                sys.executable,
                "/Users/tijs/projects/mei-flint-jangh2-20261025/tools/probe_mei.py",
                "--base-url",
                cfg["benchmark_endpoint"],
                "--model",
                cfg["model"],
                "--tokenizer",
                "/Users/tijs/.local/share/local-model-bench/mei-models/Flint-40B-A2.5B-JANGH2-mei-adapter",
                "--context-cap",
                "65536",
                "--timeout",
                "900",
                "--output",
                str(OUT / "native-probe.json"),
            ],
            check=True,
        )
        with urllib.request.urlopen(
            "http://127.0.0.1:8024/v1/mei/status", timeout=10
        ) as response:
            (OUT / "final-status.json").write_bytes(response.read())
    finally:
        subprocess.run(
            [
                "bash",
                "runner/stop_mei_server.sh",
                "--runtime-base",
                env["MEI_RUNTIME_BASE"],
            ],
            cwd=ROOT,
            check=False,
        )
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.send_signal(signal.SIGTERM)
            child.wait(timeout=15)

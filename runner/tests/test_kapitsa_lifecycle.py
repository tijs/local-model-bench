"""Failed Kapitsa loads retain GPU ownership until their whole group is stopped."""

import json
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_bench as bench
from kapitsa_provenance import acquire_gpu_lock
from owned_process import OwnedSession


class KapitsaLifecycleTests(unittest.TestCase):
    def test_failed_load_stops_real_descendants_and_releases_gpu_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ready = root / "ready"
            code = ("import os,subprocess,sys,time; from pathlib import Path; "
                    "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); "
                    f"Path({str(ready)!r}).write_text(str(os.getpid())+','+str(child.pid)); time.sleep(120)")
            cfg = {"model": "synthetic-child", "inference_engine": "kapitsa-metal",
                   "benchmark_scope": "model-only-v1", "runtime_base": str(root / "runtime"),
                   "runtime": {"gpu_lock": str(root / "gpu.lock")},
                   "benchmark_launch_command": shlex.join([sys.executable, "-c", code]),
                   "orchestration": {"raw_port": 8017, "served_model_id": "synthetic-child", "viable": "model_only"}}
            path = root / "fixture.yaml"
            path.write_text(yaml.safe_dump(cfg))

            def failed_health(_url, *, proc):
                self.assertIsInstance(proc, OwnedSession)
                with self.assertRaises(BlockingIOError):
                    acquire_gpu_lock(cfg)
                deadline = time.monotonic() + 3
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists())
                return False

            with (patch.object(bench, "verify_kapitsa_runtime"),
                  patch.object(bench, "run", return_value=SimpleNamespace(returncode=0)),
                  patch.object(bench, "admitted_config_snapshot", return_value=path),
                  patch.object(bench, "wait_for_health", side_effect=failed_health),
                  patch("socket.socket") as connection):
                connection.return_value.__enter__.return_value.connect_ex.return_value = 1
                self.assertIsNone(bench.run_one(path))
            for pid in ready.read_text().split(","):
                state = subprocess.run(["ps", "-p", pid, "-o", "stat="], capture_output=True,
                                       text=True, check=False).stdout.strip()
                self.assertTrue(not state or state.startswith("Z"), (pid, state))
            with acquire_gpu_lock(cfg):
                pass
            Path(f"/tmp/bench_{root.name}_fixture_server.log").unlink(missing_ok=True)

    def test_occupied_port_refuses_before_unload_or_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.yaml"
            path.write_text(json.dumps({"inference_engine": "kapitsa-metal", "benchmark_scope": "model-only-v1"}))
            with (patch.object(bench, "verify_kapitsa_runtime"), patch("socket.socket") as connection,
                  patch.object(bench, "_run_one_impl") as launch,
                  self.assertRaisesRegex(ValueError, "occupied benchmark port")):
                connection.return_value.__enter__.return_value.connect_ex.return_value = 0
                bench.run_one(path)
            launch.assert_not_called()

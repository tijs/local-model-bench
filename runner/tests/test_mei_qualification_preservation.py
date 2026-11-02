"""Owned cache cleanup preserves evidence and refuses live/escaped storage."""

import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "artifacts/mei-stable-qualification-20261102/preserve_run.py"
)


class PreservationTests(unittest.TestCase):
    def test_terminal_cache_is_removed_after_logs_hashes_and_index_are_saved(self):
        self.run_fixture("success")

    def test_live_server_or_symlink_escape_cannot_remove_cache(self):
        for scenario in ("live", "symlink", "wrong_model"):
            with self.subTest(scenario=scenario):
                self.run_fixture(scenario)

    def run_fixture(self, scenario):
        spec = importlib.util.spec_from_file_location(
            "qualification_preservation_fixture", SCRIPT
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            repo = root / "repo"
            home = root / "home"
            output = repo / "artifacts/run"
            output.mkdir(parents=True)
            base = (
                home / ".local/share/local-model-bench/mei-runtime/groot-stable-fixture"
            )
            (base / "logs").mkdir(parents=True)
            for name in ("server.log", "requests.jsonl"):
                (base / "logs" / name).write_text("fixture\n")
            kv = base / "kv"
            kv.mkdir()
            (kv / "state.bin").write_bytes(b"synthetic cache")
            with sqlite3.connect(kv / "index.sqlite3") as db:
                db.execute("CREATE TABLE entries (id INTEGER)")
                db.executemany("INSERT INTO entries VALUES (?)", [(1,), (2,)])
            outside = root / "outside"
            outside.mkdir()
            (outside / "keep").write_text("unrelated")
            if scenario == "symlink":
                shutil.rmtree(kv)
                kv.symlink_to(outside, target_is_directory=True)
            model = root / "model"
            model.mkdir()
            weights = model / "fixture.weights"
            weights.write_bytes(b"synthetic weights")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "directory": str(
                            outside if scenario == "wrong_model" else model
                        ),
                        "files": [
                            {
                                "file": weights.name,
                                "bytes": weights.stat().st_size,
                                "sha256": hashlib.sha256(
                                    weights.read_bytes()
                                ).hexdigest(),
                            }
                        ],
                    }
                )
            )
            (output / "outcome.json").write_text(
                json.dumps({"returncode": 0, "status": "passed"})
            )
            (output / "config.yaml").write_text(
                yaml.safe_dump(
                    {
                        "required_runner_environment": {"MEI_RUNTIME_BASE": str(base)},
                        "benchmark_launch_command": f"launcher --model-dir {model} --kv-cache-dir {kv}",
                    }
                )
            )
            args = [
                str(SCRIPT),
                "--output",
                str(output),
                "--model-manifest",
                str(manifest),
            ]
            with (
                patch.object(module, "ROOT", repo),
                patch.object(module.Path, "home", return_value=home),
                patch.object(
                    module, "verify_mei_runtime", return_value={"verified": True}
                ),
                patch.object(
                    module.subprocess, "run", return_value=Mock(returncode=1, stdout="")
                ),
                patch.object(
                    module.subprocess,
                    "check_output",
                    return_value="/fixture/mei\n" if scenario == "live" else "",
                ),
                patch.object(sys, "argv", args),
                patch("builtins.print"),
            ):
                if scenario == "success":
                    module.main()
                else:
                    expected_error = {
                        "live": "Mei must have exited",
                        "symlink": "KV path must remain",
                        "wrong_model": "model hash manifest does not match",
                    }[scenario]
                    with self.assertRaisesRegex(ValueError, expected_error):
                        module.main()
            self.assertEqual((outside / "keep").read_text(), "unrelated")
            self.assertEqual(weights.read_bytes(), b"synthetic weights")
            if scenario == "success":
                self.assertFalse(kv.exists())
                self.assertTrue(
                    json.loads((output / "owned-kv-cleanup.json").read_text())[
                        "deleted"
                    ]
                )
                self.assertEqual(
                    json.loads((output / "owned-kv-index-summary.json").read_text())[0][
                        "rows_per_table"
                    ],
                    {"entries": 2},
                )
                self.assertEqual((output / "server.log").read_text(), "fixture\n")
                self.assertTrue(
                    json.loads((output / "post-run-model-hashes.json").read_text())[
                        "all_match"
                    ]
                )
            else:
                self.assertTrue(kv.exists())
                self.assertFalse((output / "owned-kv-cleanup.json").exists())


if __name__ == "__main__":
    unittest.main()

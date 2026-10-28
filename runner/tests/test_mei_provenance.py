"""Pinned source drift must fail before model launch or benchmark rows."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mei_provenance as provenance
import run_bench


class MeiProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "mei"
        self.repo.mkdir()
        self.dependency = "1" * 40
        (self.repo / "Sources").mkdir()
        (self.repo / "Sources/main.swift").write_text("// fixture\n")
        (self.repo / "Package.resolved").write_text(
            json.dumps(
                {
                    "pins": [
                        {
                            "identity": "vmlx-swift",
                            "state": {"revision": self.dependency},
                        }
                    ]
                }
            )
        )
        self.git("init", "-q")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        self.revision = self.git("rev-parse", "HEAD")
        self.cfg = {
            "inference_engine": "mei",
            "mei_source_commit": self.revision,
            "vmlx_commit": self.dependency,
            "benchmark_launch_command": f"bash launcher --mei-repo {self.repo} --build-dir {self.repo}/build",
        }

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def test_clean_source_and_lock_are_recorded(self):
        identity = provenance.verify_mei_runtime(self.cfg)
        self.assertEqual(identity["mei_source_commit"], self.revision)
        self.assertEqual(identity["vmlx_commit"], self.dependency)
        (self.repo / "research.md").write_text("unrelated local notes")
        provenance.verify_mei_runtime(self.cfg)

    def test_wrong_revision_refused_before_lifecycle(self):
        self.cfg["mei_source_commit"] = "2" * 40
        config = self.repo / "config.yaml"
        config.write_text(json.dumps(self.cfg))
        with patch.object(run_bench, "run") as execute:
            with self.assertRaisesRegex(ValueError, "source mismatch"):
                run_bench.run_one(config)
            execute.assert_not_called()

    def test_modified_or_untracked_build_input_refused(self):
        for name in ("main.swift", "new.swift"):
            with self.subTest(name=name):
                path = self.repo / "Sources" / name
                original = path.read_text() if path.exists() else None
                path.write_text("// changed\n")
                with self.assertRaisesRegex(ValueError, "build inputs"):
                    provenance.verify_mei_runtime(self.cfg)
                if original is None:
                    path.unlink()
                else:
                    path.write_text(original)

    def test_dependency_mismatch_refused(self):
        self.cfg["vmlx_commit"] = "3" * 40
        with self.assertRaisesRegex(ValueError, "vmlx pin mismatch"):
            provenance.verify_mei_runtime(self.cfg)

    def test_standin_requires_source_pin(self):
        with self.assertRaisesRegex(ValueError, "require mei_source_commit"):
            provenance.verify_mei_runtime(
                {"inference_engine": "mei", "benchmark_scope": "peixinho-standin-v1"}
            )

    def test_remote_or_ambiguous_listener_refused(self):
        with self.assertRaisesRegex(ValueError, "local endpoint"):
            provenance.listener_binary("https://example.invalid:8024/v1")
        with patch.object(provenance.subprocess, "run") as execute:
            execute.return_value.stdout = "12\n13\n"
            with self.assertRaisesRegex(ValueError, "exactly one"):
                provenance.listener_binary("http://127.0.0.1:8024/v1")

    def test_listener_and_dependency_verified_and_hashes_recorded(self):
        build = self.repo / "build"
        (build / "release").mkdir(parents=True)
        binary = build / "release/mei"
        binary.write_bytes(b"binary")
        (build / "release/mlx.metallib").write_bytes(b"metal")
        with patch.object(
            provenance, "clean_revision", side_effect=[self.revision, self.dependency]
        ) as check:
            with patch.object(
                provenance, "listener_binary", return_value=binary.resolve()
            ):
                identity = provenance.verify_mei_runtime(
                    self.cfg, base_url="http://127.0.0.1:8024/v1"
                )
            self.assertEqual(check.call_count, 2)
            self.assertEqual(identity["binary_sha256"], provenance.sha256(binary))
        with (
            patch.object(
                provenance,
                "clean_revision",
                side_effect=[self.revision, self.dependency],
            ),
            patch.object(
                provenance, "listener_binary", return_value=Path("/other/mei")
            ),
            self.assertRaisesRegex(ValueError, "executable"),
        ):
            provenance.verify_mei_runtime(self.cfg, base_url="http://127.0.0.1:8024/v1")


if __name__ == "__main__":
    unittest.main()

"""Runtime attribution must bind launch, source, libraries and actual listener."""

import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llama_provenance import verify_llama_runtime
from mei_provenance import sha256


class LlamaProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".gitignore").write_text("build/\n")
        (self.root / "source.cpp").write_text("source identity\n")
        for args in (
            ["init", "-q"],
            ["add", "."],
            [
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
        ):
            subprocess.run(
                ["git", "-C", str(self.root), *args], check=True, capture_output=True
            )
        revision = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()
        self.binary = self.root / "build/bin/llama-server"
        self.binary.parent.mkdir(parents=True)
        self.binary.write_bytes(b"executable")
        self.lib = self.binary.parent / "libtest.dylib"
        self.lib.write_bytes(b"library")
        self.cfg = {
            "inference_engine": "llama.cpp",
            "benchmark_launch_command": shlex.join(
                [str(self.binary), "--alias", "test"]
            ),
            "runtime": {
                "repository": "ggml-org/llama.cpp",
                "revision": revision,
                "source_directory": str(self.root),
                "binary": str(self.binary),
                "binary_sha256": sha256(self.binary),
                "shared_libraries": {"libtest.dylib": sha256(self.lib)},
            },
        }
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_good_runtime_and_actual_listener_are_verified(self):
        with patch("llama_provenance.listener_binary", return_value=self.binary):
            result = verify_llama_runtime(self.cfg, base_url="http://127.0.0.1:8017/v1")
        self.assertIn("listener verified", result["verification"])

    def test_other_engine_does_not_touch_llama(self):
        self.assertIsNone(verify_llama_runtime({"inference_engine": "mei"}))

    def test_dirty_source_and_wrong_revision_are_rejected(self):
        (self.root / "source.cpp").write_text("changed")
        with self.assertRaisesRegex(ValueError, "dirty"):
            verify_llama_runtime(self.cfg)
        self.cfg["runtime"]["revision"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            verify_llama_runtime(self.cfg)

    def test_executable_and_library_changes_are_rejected(self):
        self.binary.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "executable hash"):
            verify_llama_runtime(self.cfg)
        self.cfg["runtime"]["binary_sha256"] = sha256(self.binary)
        self.lib.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "library inventory/hash"):
            verify_llama_runtime(self.cfg)

    def test_library_escape_loader_override_and_listener_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory).resolve() / "outside.dylib"
            outside.write_bytes(b"library")
            self.lib.unlink()
            self.lib.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink escapes"):
                verify_llama_runtime(self.cfg)
            self.lib.unlink()
        self.lib.write_bytes(b"library")
        with (
            patch.dict(os.environ, {"DYLD_LIBRARY_PATH": "/tmp/other"}),
            self.assertRaisesRegex(ValueError, "loader environment"),
        ):
            verify_llama_runtime(self.cfg)
        with (
            patch("llama_provenance.listener_binary", return_value=Path("/tmp/other")),
            self.assertRaisesRegex(ValueError, "listener"),
        ):
            verify_llama_runtime(self.cfg, base_url="http://127.0.0.1:8017/v1")


if __name__ == "__main__":
    unittest.main()

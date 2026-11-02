"""Clover provenance binds the derived source, decoder, metadata and listener."""

import copy
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kapitsa_provenance as provenance
from mei_provenance import sha256


class KapitsaProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / "source"
        (self.source / "src").mkdir(parents=True)
        (self.source / ".gitignore").write_text("build/\n")
        code = self.source / "src/loader.cpp"
        code.write_text("base\n")

        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

        self.git = git
        git("init", "-q")
        git("add", ".")
        commit = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm")
        git(*commit, "base")
        base = git("rev-parse", "HEAD")
        code.write_text("base\nearly residency\n")
        git("add", ".")
        git(*commit, "derived")
        self.patch = self.root / "source.patch"
        self.patch.write_bytes(subprocess.check_output(["git", "-C", str(self.source), "diff", base, "HEAD"]))
        self.binary = self.source / "build/kapitsa"
        self.binary.parent.mkdir()
        self.binary.write_bytes(b"native executable")
        self.log = self.root / "server.log"
        self.log.write_text("Clover: block diffusion, 32-row blocks, threshold 0.95")
        model = self.root / "model"
        model.mkdir()
        (model / "config.json").write_text('{}')
        home = self.root / "runtime"
        environment = {"NI_CLOVER_DECODE": "diffusion", "NI_LOCK_HELD": "1", "KAPITSA_HOME": str(home),
                       "BENCH_GPU_LOCK": str(self.root / "gpu.lock")}
        self.cfg: dict[str, Any] = {
            "inference_engine": "kapitsa-metal", "model_directory": str(model), "runtime_base": str(home),
            "context_cap": 65536, "prefill_step_size": 256,
            "orchestration": {"served_model_id": "clover:diffusion", "raw_port": 8017},
            "required_runner_environment": environment,
            "model_metadata_hashes": {"config.json": sha256(model / "config.json")},
            "runtime": {"repository": "nace-ai/kapitsa", "revision": git("rev-parse", "HEAD"),
                        "source_directory": str(self.source), "binary": str(self.binary),
                        "binary_sha256": sha256(self.binary), "system_libraries": ["/usr/lib/libc++.1.dylib"],
                        "gpu_lock": environment["BENCH_GPU_LOCK"], "server_log": str(self.log)},
            "derived_source": {"patch": "source.patch", "patch_sha256": sha256(self.patch),
                               "source_tree": git("rev-parse", "HEAD^{tree}"), "base_revision": base},
            "benchmark_launch_command": shlex.join([
                str(self.binary), "serve", "--model", str(model), "--model-id", "clover:diffusion",
                "--host", "127.0.0.1", "--port", "8017", "--context", "65536", "--slots", "1",
                "--dflash", "none", "--disk-cache", "0", "--prefill-chunk", "256", "--private", "--local",
            ]),
        }
        for context in (patch.object(provenance, "REPO", self.root),
                        patch.object(provenance, "system_libraries", return_value=["/usr/lib/libc++.1.dylib"]),
                        patch.dict(os.environ, {}, clear=True)):
            context.start()
            self.addCleanup(context.stop)

    def test_good_runtime_and_live_decoder_verify(self):
        self.assertEqual(provenance.verify_kapitsa_runtime(self.cfg)["revision"], self.cfg["runtime"]["revision"])
        with (patch.object(provenance, "listener_binary", return_value=self.binary),
              patch.dict(os.environ, self.cfg["required_runner_environment"])):
            identity = provenance.verify_kapitsa_runtime(self.cfg, base_url="http://localhost:8017/v1")
        self.assertIn("diffusion verified", identity["verification"])

    def test_other_runtime_is_untouched(self):
        self.assertIsNone(provenance.verify_kapitsa_runtime({"inference_engine": "mei"}))

    def test_dirty_source_revision_binary_and_patch_mismatch_refuse(self):
        for field, value, error in (("revision", "0" * 40, "revision mismatch"),
                                    ("binary_sha256", "0" * 64, "executable hash")):
            cfg = copy.deepcopy(self.cfg)
            cfg["runtime"][field] = value
            with self.assertRaisesRegex(ValueError, error):
                provenance.verify_kapitsa_runtime(cfg)
        self.patch.write_text("different patch")
        with self.assertRaisesRegex(ValueError, "patch mismatch"):
            provenance.verify_kapitsa_runtime(self.cfg)
        (self.source / "src/loader.cpp").write_text("uncommitted")
        with self.assertRaisesRegex(ValueError, "dirty"):
            provenance.verify_kapitsa_runtime(self.cfg)

    def test_decoder_launch_overrides_and_undeclared_environment_refuse(self):
        for suffix in (" --context 1024", " --ctx 1024", " --allow-switch", " --engine splash"):
            cfg = self.cfg | {"benchmark_launch_command": self.cfg["benchmark_launch_command"] + suffix}
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                provenance.verify_kapitsa_runtime(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["required_runner_environment"]["NI_CLOVER_DECODE"] = "spec"
        with self.assertRaisesRegex(ValueError, "explicit diffusion"):
            provenance.verify_kapitsa_runtime(cfg)
        for name, value in (("DYLD_LIBRARY_PATH", "/tmp/override"), ("NI_CLOVER_BLOCK", "8")):
            with patch.dict(os.environ, {name: value}), self.assertRaises(ValueError):
                provenance.verify_kapitsa_runtime(self.cfg)

    def test_metadata_listener_and_actual_mode_are_checked(self):
        with (patch.object(provenance, "listener_binary", return_value=self.root / "other"),
              self.assertRaisesRegex(ValueError, "listener")):
            provenance.verify_kapitsa_runtime(self.cfg, base_url="http://localhost:8017/v1")
        self.log.write_text("Clover: self-speculative")
        with (patch.object(provenance, "listener_binary", return_value=self.binary),
              patch.dict(os.environ, self.cfg["required_runner_environment"]),
              self.assertRaisesRegex(ValueError, "actual Clover block diffusion")):
            provenance.verify_kapitsa_runtime(self.cfg, base_url="http://localhost:8017/v1")
        (Path(self.cfg["model_directory"]) / "config.json").write_text("changed metadata")
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            provenance.verify_kapitsa_runtime(self.cfg)

    def test_gpu_lock_excludes_a_second_owner_and_is_reusable_after_cleanup(self):
        with provenance.acquire_gpu_lock(self.cfg), self.assertRaises(BlockingIOError):
            provenance.acquire_gpu_lock(self.cfg)
        with provenance.acquire_gpu_lock(self.cfg):
            pass

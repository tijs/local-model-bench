"""Declared cohorts must not promote partial or mismatched process evidence."""

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_context_speed_cohort import (
    committed_config,
    load_cohort,
)
from context_speed_summary import aggregate_context_speeds
from mei_clean_speed import (
    AUDITED_LAUNCHER_SHA256,
    AUDITED_MEI_REVISION,
    AUDITED_VMLX_REVISION,
    FIXED_PATH,
    MODE,
    PROFILE_KEYS,
)
from qualify_llama_context import succeeded as llama_succeeded


def clean_config(cfg: dict) -> dict:
    required = {key: cfg["required_runner_environment"][key] for key in PROFILE_KEYS}
    cfg["required_runner_environment"] = required
    cfg["mei_clean_speed_launch"] = {
        "mode": MODE,
        "launcher_sha256": AUDITED_LAUNCHER_SHA256,
        "environment": {"HOME": "/Users/tijs", "PATH": FIXED_PATH, **required},
    }
    return cfg


class DeclaredContextCohortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.spec: dict[str, Any] = {
            "profiles": [
                {
                    "model": "Fixture",
                    "model_id": "fixture/model",
                    "engine": "mei",
                    "model_revision": "a" * 40,
                    "runtime_sha256": "b" * 64,
                    "metallib_sha256": "c" * 64,
                    "short_tokens": 17,
                    "long_tokens": 1024,
                    "color": "#123456",
                    "processes": [],
                }
            ]
        }
        manifest = self.root / "artifacts/model-manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "all_match": True,
                    "files": [{"file": "fixture", "bytes": 1, "sha256": "e" * 64}],
                }
            )
        )
        self.spec["profiles"][0].update(
            model_manifest=str(manifest.relative_to(self.root)),
            model_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        )
        self.result = {
            "model": "fixture/model",
            "clean_speed_launch_required": True,
            "clean_speed_launch": {"mode": MODE},
            "prompt_sha256": {"short": "a" * 64, "loaded": "b" * 64},
            "settings": {"loaded_tokens": 1024, "decode_tokens": 128, "repeats": 5},
            "rows": [
                {
                    "phase": "measured",
                    "context": context,
                    "repeat": repeat,
                    "observable": {"prompt_tokens": tokens, "completion_tokens": 128},
                    "decode_tps": rate,
                }
                for context, tokens, rate in (("short", 17, 50), ("loaded", 1024, 25))
                for repeat in range(1, 6)
            ],
        }
        config = {
            "model": "fixture/model",
            "inference_engine": "mei",
            "source_revision": "a" * 40,
            "mei_source_commit": AUDITED_MEI_REVISION,
            "vmlx_commit": AUDITED_VMLX_REVISION,
            "orchestration": {"served_model_id": "fixture/model"},
            "mei_release_artifact": {
                "binary_sha256": "b" * 64,
                "metallib_sha256": "c" * 64,
            },
            "benchmark_launch_command": "bash runner/start_mei_server.sh --model-dir /fixture",
            "required_runner_environment": {
                key: "/tmp/fixture" if key == "MEI_RUNTIME_BASE" else "0"
                for key in PROFILE_KEYS
            },
        }
        clean_config(config)
        for process in ("p1", "p2"):
            cfg = self.root / f"configs/{process}.yaml"
            out = self.root / f"artifacts/{process}"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            out.mkdir(parents=True)
            content = yaml.safe_dump(config).encode()
            cfg.write_bytes(content)
            (out / "config.yaml").write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            (out / "invocation.json").write_text(
                json.dumps({"config_sha256": digest, "runner_git_sha": "d" * 12})
            )
            (out / "outcome.json").write_text(
                json.dumps({"status": "passed", "returncode": 0, "stop_reason": None})
            )
            (out / "server.log").write_text("normal server startup\n")
            (out / "clean-speed-launch.json").write_text(json.dumps({"mode": MODE}))
            (out / "launcher-executed.sh").write_bytes(b"fixture")
            self.spec["profiles"][0]["processes"].append(
                {
                    "id": process,
                    "config": str(cfg.relative_to(self.root)),
                    "config_sha256": digest,
                    "output": str(out.relative_to(self.root)),
                }
            )

    def load(self):
        with (
            patch("build_context_speed_cohort.committed_config"),
            patch("build_context_speed_cohort.verify_receipt"),
            patch("build_context_speed_cohort.validate_resources"),
            patch("build_context_speed_cohort.validate_mei", return_value=self.result),
        ):
            return load_cohort(self.root, self.spec)

    def test_complete_two_processes_produce_balanced_endpoints(self):
        profiles, rows = self.load()
        point = aggregate_context_speeds(profiles, rows)[0]
        self.assertEqual((point.short_tps, point.long_tps), (50, 25))
        self.assertEqual(len(rows), 20)

    def test_mei_line_continuation_uses_qualifier_command_parsing(self):
        for process in self.spec["profiles"][0]["processes"]:
            config_path = self.root / process["config"]
            cfg = yaml.safe_load(config_path.read_bytes())
            cfg["benchmark_launch_command"] = (
                "bash runner/start_mei_server.sh \\\n --model-dir /fixture"
            )
            content = yaml.safe_dump(cfg).encode()
            config_path.write_bytes(content)
            output = self.root / process["output"]
            (output / "config.yaml").write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            process["config_sha256"] = digest
            (output / "invocation.json").write_text(
                json.dumps({"config_sha256": digest, "runner_git_sha": "d" * 12})
            )
        self.assertEqual(len(self.load()[1]), 20)

    def test_interrupted_process_is_rejected(self):
        out = self.root / "artifacts/p2/outcome.json"
        out.write_text(
            json.dumps({"status": "failed", "returncode": 1, "stop_reason": "pressure"})
        )
        with self.assertRaisesRegex(ValueError, "partial or failed"):
            self.load()

    def test_runtime_and_config_mismatch_are_rejected(self):
        profile = self.spec["profiles"][0]
        profile["runtime_sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "binary or Metal"):
            self.load()
        profile["runtime_sha256"] = "b" * 64
        (self.root / "artifacts/p1/config.yaml").write_text("changed")
        with self.assertRaisesRegex(ValueError, "saved snapshot"):
            self.load()

    def test_output_reuse_and_path_escape_are_rejected(self):
        processes = self.spec["profiles"][0]["processes"]
        processes[1]["output"] = processes[0]["output"]
        with self.assertRaisesRegex(ValueError, "cannot be reused"):
            self.load()
        processes[1]["output"] = "../outside"
        with self.assertRaisesRegex(ValueError, "contained"):
            self.load()

    def test_missing_or_inconsistent_receipt_is_rejected(self):
        self.result["clean_speed_launch_required"] = False
        with self.assertRaisesRegex(ValueError, "clean launcher receipt"):
            self.load()
        self.result["clean_speed_launch_required"] = True
        self.result["clean_speed_launch"] = {"mode": "different"}
        with self.assertRaisesRegex(ValueError, "clean launcher receipt"):
            self.load()

    def test_clean_environment_must_match_between_processes(self):
        process = self.spec["profiles"][0]["processes"][1]
        config_path = self.root / process["config"]
        cfg = yaml.safe_load(config_path.read_bytes())
        cfg["mei_clean_speed_launch"]["environment"]["HOME"] = "/tmp/other"
        content = yaml.safe_dump(cfg).encode()
        config_path.write_bytes(content)
        out = self.root / process["output"]
        (out / "config.yaml").write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        process["config_sha256"] = digest
        (out / "invocation.json").write_text(
            json.dumps({"config_sha256": digest, "runner_git_sha": "d" * 12})
        )
        with self.assertRaisesRegex(ValueError, "changed the serving profile"):
            self.load()


class RealMeiEvidenceTests(unittest.TestCase):
    """Use preserved, bounded model-free artifacts; mutations stay in temp."""

    def setUp(self):
        self.repo = Path(__file__).resolve().parents[2]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        original_manifest = (
            self.repo
            / "artifacts/mei-stable-qualification-20261102/groot-pre-run-model-hashes.json"
        )
        manifest = self.root / "artifacts/model-manifest.json"
        manifest.parent.mkdir(parents=True)
        shutil.copyfile(original_manifest, manifest)
        self.spec: dict[str, Any] = {
            "profiles": [
                {
                    "model": "Groot",
                    "model_id": "Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly",
                    "engine": "mei",
                    "model_revision": "53f52e0eb8d67d2941010688b2a6b8807d9a3bea",
                    "runtime_sha256": "5d3b45e9cc7a22e3abe81003ae8b2ec0bf6dff6e3b0b0107bfeb8a26f38a808e",
                    "metallib_sha256": "e87ac8aa940ace7dd1f9945c4b6a3238c3d94604391e0f36a0ac51259bd76f32",
                    "short_tokens": 17,
                    "long_tokens": 30000,
                    "color": "#138675",
                    "model_manifest": str(manifest.relative_to(self.root)),
                    "model_manifest_sha256": hashlib.sha256(
                        manifest.read_bytes()
                    ).hexdigest(),
                    "processes": [],
                }
            ]
        }
        for arm in ("b1", "b2"):
            original_output = (
                self.repo / f"artifacts/mei-stable-groot-snapshot-{arm}-20261103"
            )
            output = self.root / f"artifacts/{arm}"
            shutil.copytree(original_output, output)
            source_cfg = (
                self.repo
                / f"configs/mei-stable-qualification-20261102/groot-snapshot-{arm}.yaml"
            )
            data = yaml.safe_load(source_cfg.read_text())
            # Test-only declaration simulates a fresh clean run. The copied
            # original artifacts remain unchanged outside this temp directory.
            clean_config(data)
            qualification = output / "qualification.json"
            result = json.loads(qualification.read_text())
            result["clean_speed_launch_required"] = True
            result["clean_speed_launch"] = {"mode": MODE}
            qualification.write_text(json.dumps(result))
            (output / "clean-speed-launch.json").write_text(json.dumps({"mode": MODE}))
            (output / "launcher-executed.sh").write_bytes(b"fixture")
            content = yaml.safe_dump(data).encode()
            cfg = self.root / f"configs/{arm}.yaml"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_bytes(content)
            (output / "config.yaml").write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            invocation = json.loads((output / "invocation.json").read_text())
            invocation["config_sha256"] = digest
            (output / "invocation.json").write_text(json.dumps(invocation))
            self.spec["profiles"][0]["processes"].append(
                {
                    "id": arm,
                    "config": str(cfg.relative_to(self.root)),
                    "config_sha256": digest,
                    "output": str(output.relative_to(self.root)),
                }
            )

    def load(self):
        # Git access is mocked: the copied config and command intentionally
        # differ from immutable original evidence. Raw validators run for real.
        with (
            patch("build_context_speed_cohort.committed_config"),
            patch("build_context_speed_cohort.verify_receipt"),
            patch("qualify_mei_release.verify_receipt"),
        ):
            return load_cohort(self.root, self.spec)

    def test_real_evidence_accepts_and_averages_both_processes(self):
        profiles, rows = self.load()
        result = aggregate_context_speeds(profiles, rows)[0]
        self.assertEqual(len(rows), 20)
        self.assertAlmostEqual(result.short_tps, 56.94341988982209)
        self.assertAlmostEqual(result.long_tps, 43.37903010322638)

    def test_manifest_and_post_run_model_mutations_fail(self):
        p = self.root / "artifacts/model-manifest.json"
        manifest = json.loads(p.read_text())
        manifest["files"][0]["sha256"] = "f" * 64
        p.write_text(json.dumps(manifest))
        self.spec["profiles"][0]["model_manifest_sha256"] = hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "post-run model files"):
            self.load()

    def test_modified_raw_response_and_rate_fail(self):
        path = self.root / "artifacts/b1/qualification.json"
        original = json.loads(path.read_text())
        for kind in ("content", "rate"):
            data = json.loads(json.dumps(original))
            row = next(r for r in data["rows"] if r["phase"] == "measured")
            if kind == "content":
                row["response"]["choices"][0]["text"] += "changed"
            else:
                row["response"]["usage"]["tokens_per_second"] += 1
            path.write_text(json.dumps(data))
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(ValueError, "raw response"),
            ):
                self.load()

    def test_compile_flag_and_resource_guard_mutations_fail(self):
        log = self.root / "artifacts/b1/server.log"
        original = log.read_text()
        assert "VMLX_ENABLE_UNSAFE_COMPILE=1 (source operator)" in original
        log.write_text(
            original.replace(
                "VMLX_ENABLE_UNSAFE_COMPILE=1 (source operator)",
                "VMLX_ENABLE_UNSAFE_COMPILE=0 (source operator)",
            )
        )
        with self.assertRaisesRegex(ValueError, "compilation setting"):
            self.load()
        log.write_text(original)
        resources = self.root / "artifacts/b1/resources.jsonl"
        rows = [json.loads(line) for line in resources.read_text().splitlines()]
        rows[-1]["kernel_pressure_level"] = 2
        rows[-2]["kernel_pressure_level"] = 2
        resources.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "resource guards"):
            self.load()

    def test_malformed_resource_sample_is_not_accepted(self):
        resources = self.root / "artifacts/b1/resources.jsonl"
        rows = [json.loads(line) for line in resources.read_text().splitlines()]
        del rows[-1]["swap_used_mib"]
        resources.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaises((ValueError, KeyError)):
            self.load()

    def test_coherent_same_length_prompt_hash_change_is_rejected(self):
        output = self.root / "artifacts/b2"
        prompt_path = output / "prompts.json"
        prompts = json.loads(prompt_path.read_text())
        prompts["loaded"] = ("x" if prompts["loaded"][0] != "x" else "y") + prompts[
            "loaded"
        ][1:]
        prompt_path.write_text(json.dumps(prompts))
        qualification = output / "qualification.json"
        result = json.loads(qualification.read_text())
        result["prompt_sha256"]["loaded"] = hashlib.sha256(
            prompts["loaded"].encode()
        ).hexdigest()
        qualification.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "actual prompt tokens"):
            self.load()

    def test_recorded_git_config_is_checked_at_run_revision(self):
        cfg = "configs/mei-stable-qualification-20261102/groot-snapshot-b1.yaml"
        snapshot = (self.repo / cfg).read_bytes()
        invocation = json.loads(
            (
                self.repo
                / "artifacts/mei-stable-groot-snapshot-b1-20261103/invocation.json"
            ).read_text()
        )
        committed_config(self.repo, cfg, invocation["runner_git_sha"], snapshot)
        with self.assertRaisesRegex(ValueError, "not committed"):
            committed_config(
                self.repo, cfg, invocation["runner_git_sha"], snapshot + b"changed"
            )

    def test_llama_raw_audit_rejects_changed_native_rate(self):
        original = self.repo / "artifacts/logics-context-1-20261103"
        if not (original / "outcome.json").is_file():
            self.skipTest("completed Logics fixture unavailable")
        output = self.root / "artifacts/logics"
        shutil.copytree(original, output)
        self.assertTrue(llama_succeeded(output))
        qfile = output / "qualification.json"
        data = json.loads(qfile.read_text())
        row = next(r for r in data["rows"] if r["phase"] == "measured")
        row["response"]["timings"]["predicted_per_second"] += 1
        qfile.write_text(json.dumps(data))
        self.assertFalse(llama_succeeded(output))


if __name__ == "__main__":
    unittest.main()

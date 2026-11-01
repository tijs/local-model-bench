"""Capacity admission uses declared bytes and measured loading, not a percent floor."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import capacity_admission as capacity
import supervise_bench as monitor


def config():
    return {
        "model_bytes": 20 * 1024**3,
        "context_cap": 65536,
        "resource_monitor_policy": {"admission_mode": "capacity"},
        "capacity_plan": {
            "model_bytes": 20 * 1024**3,
            "context_tokens": 65536,
            "context_cache_bytes": 2 * 1024**3,
            "retained_cache_bytes": 512 * 1024**2,
            "allocator_cache_bytes": 128 * 1024**2,
            "workspace_allowance_bytes": 2 * 1024**3,
            "host_reserve_bytes": 4 * 1024**3,
            "derivation": "test explicit cache and workspace estimate",
        },
    }


class CapacityAdmissionTests(unittest.TestCase):
    def test_byte_plan_rejects_impossible_host_and_invalid_provenance(self):
        cfg = config()
        plan = capacity.capacity_plan(cfg)
        assert plan is not None
        self.assertTrue(
            capacity.capacity_fits(plan, [{"physical_memory_bytes": 32 * 1024**3}])
        )
        self.assertFalse(
            capacity.capacity_fits(plan, [{"physical_memory_bytes": 16 * 1024**3}])
        )
        self.assertFalse(capacity.capacity_fits(plan, [{}]))
        for key, value in [
            ("model_bytes", 1),
            ("context_tokens", 8),
            ("host_reserve_bytes", True),
            ("derivation", ""),
        ]:
            with self.subTest(key=key):
                broken = config()
                broken["capacity_plan"][key] = value
                with self.assertRaises((ValueError, TypeError)):
                    capacity.capacity_plan(broken)

    def test_low_percentage_does_not_block_capacity_but_real_pressure_does(self):
        point = {
            "free_percent": 9,
            "kernel_pressure_level": 1,
            "swap_used_mib": 100,
            "disk_free_bytes": 50 * 1024**3,
        }
        self.assertTrue(monitor.baseline_ready([point] * 7, None, 2))
        self.assertIsNone(monitor.gate_reason(point, point, 2, 0, percent_stop=False))
        self.assertIsNotNone(monitor.gate_reason(point, point, 2, 0))
        self.assertIsNotNone(
            monitor.gate_reason(
                point | {"kernel_pressure_level": 4}, point, 0, 0, percent_stop=False
            )
        )
        self.assertIsNotNone(
            monitor.gate_reason(
                point, point | {"swap_used_mib": -2048}, 0, 0, percent_stop=False
            )
        )
        self.assertFalse(
            monitor.baseline_ready([point | {"kernel_pressure_level": 2}], None, 2)
        )

    def test_context_ramp_records_confirmed_usage_and_allocator_status(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = {
                "resource_probe": True,
                "diagnostic_only": True,
                "context_cap": 80,
                "inference_engine": "mei",
                "capacity_context_probe": {
                    "prompt_tokens": [16, 64],
                    "tokenizer_directory": "/fixture/tokenizer",
                },
            }

            def request(url, payload=None, **kwargs):
                if payload is None:
                    return {"memory": {"peakBytes": 123}}, 0.01
                return {
                    "usage": {
                        "prompt_tokens": len(payload["prompt"]),
                        "completion_tokens": 16,
                    }
                }, 0.01

            with (
                patch.dict(os.environ, {"BENCH_SUPERVISION_OUTPUT": directory}),
                patch.object(
                    capacity, "exact_prompt", side_effect=lambda _, target: "x" * target
                ),
                patch.object(capacity, "request_json", side_effect=request),
            ):
                capacity.validate_context(cfg, "http://localhost/v1", "fixture")
            report = json.loads((Path(directory) / "context-capacity.json").read_text())
            self.assertEqual(report["status"], "passed")
            self.assertEqual(
                [step["usage"]["prompt_tokens"] for step in report["steps"]], [16, 64]
            )
            self.assertEqual(
                report["steps"][-1]["backend_status"]["memory"]["peakBytes"], 123
            )

    def test_failed_ramp_preserves_completed_step_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = {
                "resource_probe": True,
                "diagnostic_only": True,
                "context_cap": 80,
                "inference_engine": "llama.cpp",
                "capacity_context_probe": {"prompt_tokens": [16, 64]},
            }
            calls = []

            def request(url, payload=None, **kwargs):
                if url.endswith("/tokenize"):
                    assert payload is not None
                    return {"tokens": [1] * (len(payload["content"]) // 6)}, 0.01
                calls.append(url)
                if len(calls) == 2:
                    raise RuntimeError("backend stopped")
                return {"usage": {"prompt_tokens": 16, "completion_tokens": 1}}, 0.01

            with (
                patch.dict(os.environ, {"BENCH_SUPERVISION_OUTPUT": directory}),
                patch.object(capacity, "request_json", side_effect=request),
                self.assertRaisesRegex(RuntimeError, "backend stopped"),
            ):
                capacity.validate_context(cfg, "http://localhost/v1", "fixture")
            report = json.loads((Path(directory) / "context-capacity.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(len(report["steps"]), 1)
            self.assertEqual(len(calls), 2)

"""Require complete repeated observations and deterministic cross-arm output."""

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "artifacts/mei-stable-qualification-20261102/run_matrix.py"
)
SPEC = importlib.util.spec_from_file_location("qualification_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


def complete_result():
    return {
        "status": "passed",
        "normal_output_budget": 8192,
        "rows": [
            {
                "context": context,
                "phase": phase,
                "repeat": repeat,
                "observable": {
                    "text": "1, 2, 3",
                    "prompt_tokens": 30000 if context == "loaded" else 13,
                    "completion_tokens": 128,
                    "finish_reason": "length",
                },
                "decode_tps": 40 + repeat,
            }
            for context in ("short", "loaded")
            for phase, repeats in (
                ("cold" if context == "short" else "cold_status", (0,)),
                ("warmup", (0,)),
                ("measured", range(1, 6)),
            )
            for repeat in repeats
        ],
    }


class MatrixAuditTests(unittest.TestCase):
    def test_saved_control_requires_hash_raw_audit_and_same_model_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "control"
            output.mkdir()
            good = complete_result()
            (output / "qualification.json").write_text(json.dumps(good))
            (output / "outcome.json").write_text('{"status": "passed"}')
            (output / "resources.jsonl").write_text(
                '{"kernel_pressure_level": 1, "swap_used_mib": 1000}\n'
            )
            identity = {
                "mei_source_commit": "b" * 40,
                "vmlx_commit": "c" * 40,
                "binary_sha256": "d" * 64,
                "metallib_sha256": "e" * 64,
            }
            cfg = {
                "model": "fixture/model",
                "source_revision": "a" * 40,
                "orchestration": {"served_model_id": "fixture/model"},
                "benchmark_launch_command": "mei --model-dir /fixture",
                "mei_source_commit": identity["mei_source_commit"],
                "vmlx_commit": identity["vmlx_commit"],
                "mei_release_artifact": {
                    "binary_sha256": "d" * 64,
                    "metallib_sha256": "e" * 64,
                },
            }
            good.update(
                model="fixture/model",
                command=["mei", "--model-dir", "/fixture"],
                runtime_identity=identity,
            )
            (output / "qualification.json").write_text(json.dumps(good))
            (output / "config.yaml").write_text(json.dumps(cfg))
            config_sha = hashlib.sha256(
                (output / "config.yaml").read_bytes()
            ).hexdigest()
            (output / "invocation.json").write_text(
                json.dumps({"config_sha256": config_sha})
            )
            (output / "post-run-runtime-verification.json").write_text(
                json.dumps(identity)
            )
            (root / "candidate.yaml").write_text(json.dumps(cfg))
            checked = matrix.audit(output, None)
            audit = output / "qualification-audit.json"
            audit.write_text(json.dumps(checked))
            declared: dict[str, Any] = {
                "cells": [{"model": "example", "config": "candidate.yaml"}],
                "baselines": {
                    "example": {
                        "audit": "control/qualification-audit.json",
                        "sha256": hashlib.sha256(audit.read_bytes()).hexdigest(),
                        "config_sha256": config_sha,
                    }
                },
            }
            with patch.object(matrix, "ROOT", root):
                self.assertEqual(
                    matrix.baseline_references(declared),
                    {"example": checked["reference"]},
                )
                changed = copy.deepcopy(declared)
                changed["baselines"]["example"]["sha256"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    matrix.baseline_references(changed)
                for key in ("model", "source_revision"):
                    (root / "candidate.yaml").write_text(
                        json.dumps(cfg | {key: "wrong"})
                    )
                    with self.assertRaisesRegex(ValueError, "model/revision differs"):
                        matrix.baseline_references(declared)
                (root / "candidate.yaml").write_text(json.dumps(cfg))
                # Relabeling a saved control cannot keep its pinned audit valid.
                (output / "config.yaml").write_text(
                    json.dumps(cfg | {"model": "unrelated/model"})
                )
                (root / "candidate.yaml").write_text(
                    json.dumps(cfg | {"model": "unrelated/model"})
                )
                with self.assertRaisesRegex(ValueError, "configuration hash mismatch"):
                    matrix.baseline_references(declared)
                (output / "config.yaml").write_text(json.dumps(cfg))
                (root / "candidate.yaml").write_text(json.dumps(cfg))
                for change, message in (
                    ({"model": "unrelated/model"}, "served model/command"),
                    ({"command": ["other"]}, "served model/command"),
                    (
                        {"runtime_identity": identity | {"binary_sha256": "f" * 64}},
                        "runtime identity",
                    ),
                ):
                    (output / "qualification.json").write_text(
                        json.dumps(good | change)
                    )
                    with self.assertRaisesRegex(ValueError, message):
                        matrix.baseline_references(declared)
                (output / "qualification.json").write_text(json.dumps(good))
                changed_raw = copy.deepcopy(good)
                changed_raw["rows"].pop()
                (output / "qualification.json").write_text(json.dumps(changed_raw))
                with self.assertRaisesRegex(ValueError, "missing/duplicate"):
                    matrix.baseline_references(declared)

    def test_saved_controls_are_all_or_none_and_paths_stay_contained(self):
        self.assertEqual(matrix.baseline_references({"cells": []}), {})
        with self.assertRaisesRegex(TypeError, "mapping"):
            matrix.baseline_references({"cells": [], "baselines": []})
        with self.assertRaisesRegex(ValueError, "every model"):
            matrix.baseline_references(
                {"cells": [{"model": "other"}], "baselines": {"example": {}}}
            )
        with self.assertRaisesRegex(ValueError, "contained"):
            matrix.baseline_references(
                {
                    "cells": [{"model": "example"}],
                    "baselines": {
                        "example": {"audit": "/outside/qualification-audit.json"}
                    },
                }
            )

    def test_explicit_progress_refuses_to_restart_existing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            declared = root / "declared.json"
            declared.write_text('{"cells": []}')
            progress = root / "progress.json"
            progress.write_text("preserved previous evidence")
            with (
                patch(
                    "sys.argv",
                    [
                        str(SCRIPT),
                        "--matrix",
                        str(declared),
                        "--progress",
                        str(progress),
                    ],
                ),
                self.assertRaisesRegex(ValueError, "do not restart"),
            ):
                matrix.main()
            self.assertEqual(progress.read_text(), "preserved previous evidence")

    def test_repeated_output_is_complete_and_byte_identical(self):
        good = complete_result()
        self.assertEqual(set(matrix.observable_by_context(good)), {"short", "loaded"})
        missing = copy.deepcopy(good)
        missing["rows"].pop()
        duplicate = copy.deepcopy(good)
        duplicate["rows"][-1] = copy.deepcopy(duplicate["rows"][-2])
        changed = copy.deepcopy(good)
        changed["rows"][-1]["observable"]["text"] = "1,2,3"
        for bad in (missing, duplicate, changed):
            with self.assertRaises(ValueError):
                matrix.observable_by_context(bad)

    def test_cross_arm_parity_and_terminal_success_are_required(self):
        good = complete_result()
        baseline = matrix.observable_by_context(good)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "qualification.json").write_text(json.dumps(good))
            (output / "outcome.json").write_text('{"status": "passed"}')
            (output / "resources.jsonl").write_text(
                '{"kernel_pressure_level": 1, "swap_used_mib": 1000}\n'
            )
            checked = matrix.audit(output, baseline)
            self.assertEqual(checked["median_decode_tps"], {"short": 43, "loaded": 43})
            changed = copy.deepcopy(baseline)
            changed["loaded"]["text"] = "1,2,3"
            with self.assertRaisesRegex(ValueError, "A1 control"):
                matrix.audit(output, changed)
            (output / "outcome.json").write_text('{"status": "interrupted"}')
            with self.assertRaisesRegex(ValueError, "did not complete"):
                matrix.audit(output, baseline)


if __name__ == "__main__":
    unittest.main()

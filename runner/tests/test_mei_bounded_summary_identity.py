"""Equal generated text must not permit mixed runtime or compilation arms."""

import copy
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

PREP = (
    Path(__file__).resolve().parents[2] / "artifacts/mei-stable-qualification-20261102"
)
SPEC = importlib.util.spec_from_file_location(
    "bounded_summary_fixture", PREP / "summarize_bounded_allocator.py"
)
assert SPEC is not None and SPEC.loader is not None
summary = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(PREP), *sys.path]):
    SPEC.loader.exec_module(summary)


class BoundedIdentityTests(unittest.TestCase):
    def fixture(self):
        cfg = {
            "benchmark_launch_command": "launcher --mei-binary /fixture/mei --runtime-base /fixture/b1",
            "mei_source_commit": "a" * 40,
            "vmlx_commit": "b" * 40,
            "mei_release_artifact": {
                "binary_sha256": "c" * 64,
                "metallib_sha256": "d" * 64,
            },
            "required_runner_environment": {
                "VMLX_ENABLE_UNSAFE_COMPILE": "1",
                "VMLX_QWEN35_COMPILE_DECODE_REGIONS": "0",
                "VMLX_QWEN4_EXP_COMPILE_ROUTED_MOE": "0",
                "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES": "0",
            },
        }
        identity = {
            "mei_source_commit": cfg["mei_source_commit"],
            "vmlx_commit": cfg["vmlx_commit"],
            "binary_path": "/fixture/mei",
            **cfg["mei_release_artifact"],
        }
        encoded = yaml.safe_dump(cfg).encode()
        return {
            "snapshot": encoded,
            "declared": encoded,
            "preflight_sha": hashlib.sha256(encoded).hexdigest(),
            "result": {
                "command": [
                    "launcher",
                    "--mei-binary",
                    "/fixture/mei",
                    "--runtime-base",
                    "/fixture/b1",
                ],
                "runtime_identity": identity,
                "rows": [{"observable": {"text": "identical output"}}],
            },
            "post": copy.deepcopy(identity),
            "server_log": "\n".join(
                f"mei: vmlx switch {k}={v} (source operator)"
                for k, v in cfg["required_runner_environment"].items()
            ),
        }

    def test_valid_declared_runtime_and_effective_switches(self):
        summary.validate_identity(**self.fixture())

    def test_identical_outputs_cannot_hide_wrong_runtime_or_launch_arm(self):
        for target, key in (
            ("runtime_identity", "mei_source_commit"),
            ("runtime_identity", "vmlx_commit"),
            ("runtime_identity", "binary_sha256"),
            ("runtime_identity", "metallib_sha256"),
            ("runtime_identity", "binary_path"),
            ("post", "binary_sha256"),
        ):
            with self.subTest(target=target, key=key):
                fixture = self.fixture()
                observed = (
                    fixture["post"] if target == "post" else fixture["result"][target]
                )
                observed[key] = "wrong arm"
                with self.assertRaisesRegex(ValueError, "runtime identity"):
                    summary.validate_identity(**fixture)
        fixture = self.fixture()
        fixture["result"]["command"][-1] = "/fixture/c1"
        with self.assertRaisesRegex(ValueError, "launch command"):
            summary.validate_identity(**fixture)

    def test_replaced_config_or_ignored_compilation_switch_is_refused(self):
        fixture = self.fixture()
        fixture["snapshot"] += b"# replaced snapshot\n"
        with self.assertRaisesRegex(ValueError, "predeclared snapshot"):
            summary.validate_identity(**fixture)
        fixture = self.fixture()
        fixture["snapshot"] += b"# replaced both copies\n"
        fixture["declared"] = fixture["snapshot"]
        with self.assertRaisesRegex(ValueError, "predeclared snapshot"):
            summary.validate_identity(**fixture)
        fixture = self.fixture()
        fixture["server_log"] = fixture["server_log"].replace(
            "VMLX_ENABLE_UNSAFE_COMPILE=1", "VMLX_ENABLE_UNSAFE_COMPILE=0"
        )
        with self.assertRaisesRegex(ValueError, "compilation setting"):
            summary.validate_identity(**fixture)


if __name__ == "__main__":
    unittest.main()

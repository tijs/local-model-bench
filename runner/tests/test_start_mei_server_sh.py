"""Regression tests for runner/start_mei_server.sh's gate-control flags and
--dry-run non-destructiveness.

Context (2026-09-06): the NVIDIA-Nemotron-3.5-Lightning-30B-A3B gate ran with
--optimization-profile generic --memory-limit-bytes 30000000000
--cache-limit-bytes 0 --compiled-decode false, but the wrapper previously
forwarded only model/port/context/sampling/KV flags and silently dropped those
four. This test pins that: the wrapper now forwards each when explicitly
provided, stays backward-compatible when they are absent, and --dry-run prints
the full launch line WITHOUT compiling the Swift package or launching a server.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # local-model-bench root
START_MEI = REPO / "runner" / "start_mei_server.sh"

# Flat argv tokens so they can be concatenated with the base args.
GATE_CONTROLS_FLAT = [
    "--optimization-profile", "generic",
    "--memory-limit-bytes", "30000000000",
    "--cache-limit-bytes", "0",
    "--compiled-decode", "false",
]

# (flag, expected value) pairs used for the assertIn coverage check.
GATE_CONTROLS_PAIRS = [
    ("--optimization-profile", "generic"),
    ("--memory-limit-bytes", "30000000000"),
    ("--cache-limit-bytes", "0"),
    ("--compiled-decode", "false"),
]

BASE_ARGS = [
    "--model-dir", "{model}",
    "--served-model-id", "mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit",
    "--port", "8024",
    "--context-cap", "65536",
    "--prefill-step-size", "256",
    "--max-tokens", "32768",
    "--kv-cache-dir", "{kv}",
    "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20",
    "--emit-reasoning", "true", "--cache-reuse", "true",
    "--build-dir", "{build}",
    "--mei-repo", "{repo}",
]


def _stub_env():
    """Model dir with config.json + a Mei checkout with Package.swift —
    enough to satisfy the script's preflight existence checks, and nothing
    more: --dry-run must return before any Swift build or server launch."""
    base = Path(tempfile.mkdtemp(prefix="hermes-mei-sh-"))
    model = base / "model"
    model.mkdir()
    (model / "config.json").write_text("{}")
    repo = base / "mei"
    repo.mkdir()
    (repo / "Package.swift").write_text("// stub\n")
    kv = base / "kv"
    build = base / "build"
    return base, str(model), str(repo), str(kv), str(build)


def _dry_run(extra):
    base, model, repo, kv, build = _stub_env()
    argv = [a.format(model=model, kv=kv, build=build, repo=repo) for a in BASE_ARGS]
    res = subprocess.run(
        ["bash", str(START_MEI), *argv, *extra, "--dry-run"],
        capture_output=True, text=True,
    )
    return base, res


class StartMeiServerForwardingTests(unittest.TestCase):
    def test_dry_run_prints_all_four_gate_controls(self):
        _, res = _dry_run(GATE_CONTROLS_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("mei isolated launch:", res.stdout)
        for flag, val in GATE_CONTROLS_PAIRS:
            self.assertIn(flag, res.stdout)
            self.assertIn(val, res.stdout)

    def test_dry_run_does_not_build_or_touch_runtime(self):
        base, res = _dry_run(GATE_CONTROLS_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        # No Swift build and no runtime/build dirs created — nothing launched.
        self.assertNotIn("building", res.stdout)
        self.assertNotIn("swift build", (res.stdout + res.stderr).lower())
        self.assertFalse(base.joinpath("kv").exists())
        self.assertFalse(base.joinpath("build").exists())

    def test_defaults_do_not_forward_gate_controls(self):
        # Backward compatibility: without the flags, none of the gate controls
        # appear in the launch line, so existing configs are unaffected.
        _, res = _dry_run([])
        self.assertEqual(res.returncode, 0, res.stderr)
        for flag, _ in GATE_CONTROLS_PAIRS:
            self.assertNotIn(flag, res.stdout)


if __name__ == "__main__":
    unittest.main()

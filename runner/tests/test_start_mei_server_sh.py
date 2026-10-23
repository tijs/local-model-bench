"""Regression tests for runner/start_mei_server.sh's gate-control flags and
--dry-run non-destructiveness.

Context (2026-09-06): the NVIDIA-Nemotron-3.5-Lightning-30B-A3B gate ran with
--model-profile generic --memory-limit-bytes 30000000000
--cache-limit-bytes 0 --compiled-decode false, but the wrapper previously
forwarded only model/port/context/sampling/KV flags and silently dropped those
four. Mei 0.5.0 renamed the gate's --optimization-profile flag to
--model-profile; the wrapper (2026-09-12) now forwards --model-profile and
rejects the removed legacy name. The Qwen3.6 OptiQ gate (2026-09-14) pinned
the hidden Mei 0.5.0+ load-path override --load-mmap false (5/5 unaligned
shards: the default mmap path realigned ~16.6 GiB of temporary copies and
OOM'd the GPU allocator); the wrapper now forwards it when explicit. This test
pins that: the wrapper forwards each gate control when explicitly provided,
stays backward-compatible when they are absent, rejects the pre-0.5.0 flag
name, and --dry-run prints the full launch line WITHOUT compiling the Swift
package or launching a server.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]  # local-model-bench root
START_MEI = REPO / "runner" / "start_mei_server.sh"

# Flat argv tokens so they can be concatenated with the base args.
GATE_CONTROLS_FLAT = [
    "--model-profile", "generic",
    "--memory-limit-bytes", "30000000000",
    "--cache-limit-bytes", "0",
    "--compiled-decode", "false",
]

# (flag, expected value) pairs used for the assertIn coverage check.
GATE_CONTROLS_PAIRS = [
    ("--model-profile", "generic"),
    ("--memory-limit-bytes", "30000000000"),
    ("--cache-limit-bytes", "0"),
    ("--compiled-decode", "false"),
]

# Mei 0.5.0+ safetensors load-path override — accepted by the binary though
# hidden from its --help. Pinned `false` by the Qwen3.6 OptiQ gate (5/5
# unaligned shards; the default mmap path realigned ~16.6 GiB of temporary
# copies and OOM'd the GPU allocator) and forwarded only when explicit so
# every older config keeps Mei's own default.
LOAD_MMAP_FLAT = [
    "--load-mmap", "false",
]
LOAD_MMAP_PAIRS = [
    ("--load-mmap", "false"),
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
    "--runtime-base", "{runtime}",
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


def _run_launcher(extra, *, dry_run=True):
    base, model, repo, kv, build = _stub_env()
    argv = [
        a.format(model=model, kv=kv, build=build, repo=repo, runtime=base / "runtime")
        for a in BASE_ARGS
    ]
    res = subprocess.run(
        ["bash", str(START_MEI), *argv, *extra, *(["--dry-run"] if dry_run else [])],
        # macOS Bash may put usage here-doc temporaries in its working dir.
        cwd=base, capture_output=True, text=True,
        # Fail closed even if a regression reaches the build: never run Swift
        # or a real Mei binary from these launcher tests.
        env={**os.environ, "MEI_SWIFT": "/usr/bin/false"},
    )
    return base, res


def _dry_run(extra):
    return _run_launcher(extra)


class StartMeiServerForwardingTests(unittest.TestCase):
    def test_dry_run_prints_all_four_gate_controls(self):
        _, res = _dry_run(GATE_CONTROLS_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("mei isolated launch:", res.stdout)
        for flag, val in GATE_CONTROLS_PAIRS:
            self.assertIn(flag, res.stdout)
            self.assertIn(val, res.stdout)

    def test_dry_run_forwards_load_mmap_when_explicit(self):
        # --load-mmap is a hidden Mei 0.5.0+ load-path override: it must reach
        # the launch line verbatim when a config pins it (the OptiQ gate's
        # `false`), and never appear otherwise.
        _, res = _dry_run(LOAD_MMAP_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("mei isolated launch:", res.stdout)
        for flag, val in LOAD_MMAP_PAIRS:
            self.assertIn(flag, res.stdout)
            self.assertIn(val, res.stdout)

    def test_dry_run_forwards_enable_flint_true_when_explicit(self):
        self._assert_flint_forwarded("true")

    def test_dry_run_forwards_enable_flint_false_when_explicit(self):
        self._assert_flint_forwarded("false")

    def _assert_flint_forwarded(self, value):
        base, res = _dry_run([*GATE_CONTROLS_FLAT, "--enable-flint", value])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(res.stdout.startswith("mei isolated launch: "), res.stdout)
        argv = shlex.split(res.stdout.removeprefix("mei isolated launch: "))
        self.assertEqual(argv.count("--enable-flint"), 1)
        index = argv.index("--enable-flint")
        self.assertEqual(argv[index:index + 2], ["--enable-flint", value])
        self.assertNotIn("building", res.stdout)
        for name in ("kv", "build", "runtime"):
            self.assertFalse((base / name).exists(), name)

    def test_enable_flint_is_not_inferred_from_model_or_environment(self):
        with patch.dict(os.environ, {"ENABLE_FLINT": "true", "MEI_ENABLE_FLINT": "true"}):
            _, res = _dry_run(["--served-model-id", "test-flint-model"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("--enable-flint", shlex.split(res.stdout))

    def test_invalid_enable_flint_fails_before_build_or_launch(self):
        # Deliberately omit --dry-run: malformed input must fail before runtime
        # setup or build/launch even on the normal launch path.
        for values in (
            ["TRUE"], ["False"], ["1"], ["0"], ["yes"], ["no"],
            [" true"], ["true "], [""], [], ["--dry-run"],
        ):
            with self.subTest(values=values):
                base, res = _run_launcher(["--enable-flint", *values], dry_run=False)
                self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
                self.assertIn("--enable-flint must be true or false", res.stderr)
                self.assertNotIn("mei isolated launch:", res.stdout)
                self.assertNotIn("building", res.stdout)
                for name in ("kv", "build", "runtime"):
                    self.assertFalse((base / name).exists(), name)

    def test_dry_run_does_not_build_or_touch_runtime(self):
        base, res = _dry_run(GATE_CONTROLS_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        # No Swift build and no runtime/build dirs created — nothing launched.
        self.assertNotIn("building", res.stdout)
        self.assertNotIn("swift build", (res.stdout + res.stderr).lower())
        self.assertFalse(base.joinpath("kv").exists())
        self.assertFalse(base.joinpath("build").exists())
        self.assertFalse(base.joinpath("runtime").exists())

    def test_legacy_optimization_profile_flag_is_rejected(self):
        # Mei 0.5.0 renamed --optimization-profile to --model-profile; the
        # wrapper must not silently accept the removed name, or a config
        # written against the old flag would launch with NO profile at all.
        _, res = _dry_run(["--optimization-profile", "generic"])
        self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
        self.assertIn("unknown option: --optimization-profile", res.stderr)
        self.assertNotIn("--model-profile", res.stdout)

    def test_defaults_do_not_forward_gate_controls(self):
        # Backward compatibility: without the flags, none of the gate controls
        # (nor --load-mmap or the default-off Flint gate) appear in the launch
        # line, so existing configs are unaffected.
        _, res = _dry_run([])
        self.assertEqual(res.returncode, 0, res.stderr)
        for flag, _ in GATE_CONTROLS_PAIRS + LOAD_MMAP_PAIRS:
            self.assertNotIn(flag, res.stdout)
        self.assertNotIn("--enable-flint", shlex.split(res.stdout))


if __name__ == "__main__":
    unittest.main()

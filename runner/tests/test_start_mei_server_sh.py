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

Context (2026-10-15): Mei's ServerConfig has supported --repetition-penalty
since before 0.9.0 (Sources/MeiCore/ServerConfig.swift), but the wrapper never
forwarded it, so no config could pin a repetition penalty. LFM2.5-24B-A2B's
vendor sampling (temperature 0.1 / top_k 50 / repetition_penalty 1.05) needs
it. Forwarded ONLY when explicit — no default is injected, so every existing
config keeps Mei's own default exactly as before.

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

# Mei's sampling repetition penalty (ServerConfig --repetition-penalty).
# Wired into the wrapper 2026-10-15 for LFM2.5-24B-A2B's vendor sampling
# (1.05); forwarded only when explicit so older configs keep Mei's default.
REPETITION_PENALTY_FLAT = [
    "--repetition-penalty", "1.05",
]
REPETITION_PENALTY_PAIRS = [
    ("--repetition-penalty", "1.05"),
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
    def test_local_vmlx_requires_path_and_revision_together(self):
        for extra in (["--vmlx-repo", "/not-used"],
                      ["--vmlx-revision", "a" * 40]):
            _, res = _dry_run(extra)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
            self.assertIn("must be supplied together", res.stderr)

    def test_local_vmlx_dry_run_delegates_exact_selection_to_mei_guard(self):
        # Explicit helper stub tests the wrapper boundary; real Git/SwiftPM
        # selection is separately exercised by Mei's override tests/build.
        base, model, repo, kv, build = _stub_env()
        scripts = Path(repo) / "scripts"
        scripts.mkdir()
        (scripts / "use_local_vmlx.sh").write_text(
            "#!/bin/bash\nprintf 'override guard: '; printf '%q ' \"$@\"; printf '\\n'\n")
        argv = [a.format(model=model, kv=kv, build=build, repo=repo) for a in BASE_ARGS]
        revision = "a" * 40
        res = subprocess.run(
            ["bash", str(START_MEI), *argv, "--vmlx-repo", str(base / "local-vmlx"),
             "--vmlx-revision", revision, "--dry-run"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("override guard:", res.stdout)
        self.assertIn(f"--path {base / 'local-vmlx'} --revision {revision}", res.stdout)
        self.assertIn(f"--build-dir {build} --dry-run", res.stdout)
        self.assertFalse(Path(build).exists())

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

    def test_dry_run_forwards_repetition_penalty_when_explicit(self):
        # --repetition-penalty must reach the launch line verbatim when a
        # config pins it (LFM2.5-24B-A2B vendor sampling 1.05)...
        _, res = _dry_run(REPETITION_PENALTY_FLAT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("mei isolated launch:", res.stdout)
        for flag, val in REPETITION_PENALTY_PAIRS:
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
        # (nor the --load-mmap load-path override, nor the sampling
        # --repetition-penalty) appear in the launch line, so existing
        # configs are unaffected.
        _, res = _dry_run([])
        self.assertEqual(res.returncode, 0, res.stderr)
        for flag, _ in GATE_CONTROLS_PAIRS + LOAD_MMAP_PAIRS + REPETITION_PENALTY_PAIRS:
            self.assertNotIn(flag, res.stdout)


if __name__ == "__main__":
    unittest.main()

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
import os
import hashlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]  # local-model-bench root
START_MEI = REPO / "runner" / "start_mei_server.sh"
FUSED_CACHE_FLAG = "--fused-gate-up-cache-limit-bytes"
FUSED_CACHE_ENV = "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES"
MAX_CACHE_BLOCKS_FLAG = "--max-cache-blocks"
CANDIDATE3_COMMIT = "0b68ce2d960e8d6754a52ea780c8fec2c57cde3c"
LFM_CONFIG_PATH = "configs/LiquidAI-LFM2.5-24B-A2B-MLX-4bit/mei.yaml"


def _candidate3_file(path):
    return subprocess.check_output(["git", "show", f"{CANDIDATE3_COMMIT}:{path}"], cwd=REPO)

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


def _dry_run(extra, *, omit=(), env=None, script=START_MEI):
    base, model, repo, kv, build = _stub_env()
    argv = []
    for flag, value in zip(BASE_ARGS[::2], BASE_ARGS[1::2]):
        if flag not in omit:
            argv += [flag, value.format(model=model, kv=kv, build=build, repo=repo)]
    res = subprocess.run(
        ["bash", str(script), *argv, *extra, "--dry-run"],
        capture_output=True, text=True, timeout=30, env=env,
    )
    return base, res


def _launch_argv(res):
    """Parse the shell-quoted vector, not loose flag/value substrings."""
    prefix = "mei isolated launch: "
    lines = [line[len(prefix):] for line in res.stdout.splitlines()
             if line.startswith(prefix)]
    if len(lines) != 1:
        raise AssertionError(f"expected one launch vector: {res.stdout!r}")
    return shlex.split(lines[0])


class StartMeiServerForwardingTests(unittest.TestCase):
    def test_dry_run_reports_runtime_override_without_creating_it(self):
        base, model, repo, kv, build = _stub_env()
        self.addCleanup(shutil.rmtree, base)
        runtime = base / "runtime-lfm25"
        argv = [a.format(model=model, kv=kv, build=build, repo=repo) for a in BASE_ARGS]
        res = subprocess.run(
            ["bash", str(START_MEI), *argv, "--runtime-base", str(runtime), "--dry-run"],
            capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn(f"mei isolated runtime: {runtime}", res.stdout)
        self.assertIn(f"pid: {runtime / 'server.pid'}", res.stdout)
        self.assertIn(f"logs: {runtime / 'logs'}", res.stdout)
        self.assertFalse(runtime.exists())
        self.assertFalse(Path(build).exists())

    def test_dry_run_without_override_reports_unchanged_default_runtime(self):
        base, res = _dry_run([])
        self.addCleanup(shutil.rmtree, base)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn(f"mei isolated runtime: {Path.home() / '.local/share/local-model-bench/mei-runtime'}",
                      res.stdout)

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
        self.assertNotIn(MAX_CACHE_BLOCKS_FLAG, _launch_argv(res))

    def test_prefill_and_memory_candidate_flags_are_explicit_and_independent(self):
        # Suppress BASE_ARGS' explicit prefill/max caps to exercise absence.
        # The wrapper must not turn an LFM candidate into a global default.
        for extra in ([], ["--prefill-step-size", "512"],
                      ["--prefill-step-size", "1024"],
                      ["--memory-limit-bytes", "32000000000"],
                      ["--prefill-step-size", "512", "--memory-limit-bytes", "32000000000"],
                      ["--prefill-step-size", "1024", "--memory-limit-bytes", "32000000000"]):
            with self.subTest(extra=extra):
                base, res = _dry_run(["--model-profile", "qwen3.6-35b-a3b-text", *extra],
                                     omit=("--prefill-step-size", "--max-tokens"))
                self.addCleanup(shutil.rmtree, base)
                self.assertEqual(res.returncode, 0, res.stderr)
                argv = _launch_argv(res)
                self.assertNotIn("--max-tokens", argv)
                for flag in ("--prefill-step-size", "--memory-limit-bytes"):
                    if flag in extra:
                        self.assertEqual(argv.count(flag), 1)
                        self.assertEqual(argv[argv.index(flag) + 1], extra[extra.index(flag) + 1])
                    else:
                        self.assertNotIn(flag, argv)
                self.assertFalse((base / "build").exists())


class MaxCacheBlocksForwardingTests(unittest.TestCase):
    def test_explicit_limits_are_forwarded_exactly_once_without_changing_reuse(self):
        for value in ("2", "4097", "0004097", "8192", "9223372036854775807"):
            for reuse in (None, "false"):
                with self.subTest(value=value, reuse=reuse):
                    extra = [MAX_CACHE_BLOCKS_FLAG, value]
                    if reuse is not None:
                        extra += ["--cache-reuse", reuse]
                    base, res = _dry_run(extra, omit=("--cache-reuse",))
                    self.addCleanup(shutil.rmtree, base)
                    self.assertEqual(res.returncode, 0, res.stderr)
                    argv = _launch_argv(res)
                    self.assertEqual(argv.count(MAX_CACHE_BLOCKS_FLAG), 1)
                    self.assertEqual(argv[argv.index(MAX_CACHE_BLOCKS_FLAG) + 1], value)
                    self.assertEqual(argv[argv.index("--cache-reuse") + 1], reuse or "true")
                    self.assertFalse((base / "build").exists())
                    self.assertFalse((base / "kv").exists())

    def test_absent_option_preserves_the_entire_candidate3_default_vector(self):
        with tempfile.TemporaryDirectory(prefix="mei-old-wrapper-") as td:
            previous = Path(td) / "start_mei_server.sh"
            previous.write_bytes(_candidate3_file("runner/start_mei_server.sh"))
            old_base, old = _dry_run([], omit=("--cache-reuse",), script=previous)
            base, res = _dry_run([], omit=("--cache-reuse",))
            for root in (old_base, base):
                self.addCleanup(shutil.rmtree, root)
            self.assertEqual(old.returncode, 0, old.stderr)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual([x.replace(str(base), "{fixture}") for x in _launch_argv(res)],
                             [x.replace(str(old_base), "{fixture}") for x in _launch_argv(old)])
            self.assertNotIn(MAX_CACHE_BLOCKS_FLAG, _launch_argv(res))

    def test_invalid_and_missing_values_fail_closed_before_any_preflight_or_build(self):
        for value in (None, "", "0", "000", "1", "0001", "-1", "+2", "2.0", "2e3",
                      "true", "false", "null", " 2", "2 ", "2\n", "0x10", "１２",
                      "2;exit 0", "9223372036854775808", "9" * 100):
            with self.subTest(value=value):
                # Use no required paths: rejection must precede even preflight.
                extra = [MAX_CACHE_BLOCKS_FLAG] + ([] if value is None else [value])
                res = subprocess.run(["bash", str(START_MEI), *extra],
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
                self.assertIn(f"{MAX_CACHE_BLOCKS_FLAG} must be an integer", res.stderr)
                self.assertNotIn("mei isolated launch:", res.stdout)
                self.assertNotIn("building", res.stdout)

    def test_invalid_limit_is_not_ignored_with_cache_off_or_a_later_valid_limit(self):
        for extra in (["--cache-reuse", "false", MAX_CACHE_BLOCKS_FLAG, "0"],
                      [MAX_CACHE_BLOCKS_FLAG, "0", MAX_CACHE_BLOCKS_FLAG, "4097"]):
            base, res = _dry_run(extra)
            self.addCleanup(shutil.rmtree, base)
            self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
            self.assertNotIn("mei isolated launch:", res.stdout)
            self.assertFalse((base / "build").exists())


class FusedGateUpEnvironmentTests(unittest.TestCase):
    """Child-only env forwarding, with no Swift, model, server or endpoint.

    The non-dry-run path uses inert shell recorders in place of the build,
    metallib helper and executable. Nothing listens or performs inference.
    """

    def test_absent_option_injects_no_environment_or_mei_flag(self):
        env = os.environ.copy()
        env.pop(FUSED_CACHE_ENV, None)
        base, res = _dry_run([], env=env)
        self.addCleanup(shutil.rmtree, base)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn(FUSED_CACHE_ENV, res.stdout)
        self.assertNotIn(FUSED_CACHE_FLAG, _launch_argv(res))
        self.assertNotEqual(_launch_argv(res)[0], "env")

    def test_explicit_zero_and_nonnegative_integers_are_visible_not_mei_flags(self):
        for value in ("0", "000", "536870912", "9223372036854775807"):
            with self.subTest(value=value):
                base, res = _dry_run([FUSED_CACHE_FLAG, value])
                self.addCleanup(shutil.rmtree, base)
                self.assertEqual(res.returncode, 0, res.stderr)
                argv = _launch_argv(res)
                self.assertEqual(argv[:2], ["env", f"{FUSED_CACHE_ENV}={value}"])
                self.assertEqual(argv[2], str(base / "build" / "release" / "mei"))
                self.assertNotIn(FUSED_CACHE_FLAG, argv)
                self.assertFalse((base / "build").exists())
                self.assertNotIn("building", res.stdout)

    def test_invalid_values_fail_closed_before_build_or_launch(self):
        for value in ("", "-1", "+1", "0.0", "1e3", "true", "false", "null",
                      " 0", "0 ", "0\n", "0x0", "１２", "1;exit 0",
                      "9223372036854775808", "9" * 100):
            with self.subTest(value=value):
                base, res = _dry_run([FUSED_CACHE_FLAG, value])
                self.addCleanup(shutil.rmtree, base)
                self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
                self.assertIn(f"{FUSED_CACHE_FLAG} must be a nonnegative integer", res.stderr)
                self.assertNotIn("mei isolated launch:", res.stdout)
                self.assertFalse((base / "build").exists())

    def test_missing_value_is_rejected(self):
        base, res = _dry_run([FUSED_CACHE_FLAG])
        self.addCleanup(shutil.rmtree, base)
        self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
        self.assertIn(f"{FUSED_CACHE_FLAG} must be a nonnegative integer", res.stderr)

    def test_launch_env_is_child_only_and_absent_option_preserves_inheritance(self):
        for inherited, selected in ((None, None), (None, "0"), ("123", None), ("123", "0")):
            with self.subTest(inherited=inherited, selected=selected):
                base, model, repo, kv, build = _stub_env()
                self.addCleanup(shutil.rmtree, base)
                scripts = Path(repo) / "scripts"
                scripts.mkdir()
                # These scripts only print their environment/argv and exit.
                recorder = (
                    '#!/bin/bash\n'
                    f'printf "recorder env: %s\\n" "${{{FUSED_CACHE_ENV}-unset}}"\n'
                    'printf "recorder argv: "; printf "%q " "$@"; printf "\\n"\n'
                )
                swift = base / "record-build"
                swift.write_text(recorder)
                swift.chmod(0o755)
                (scripts / "prepare_metallib.sh").write_text(recorder)
                binary = Path(build) / "release" / "mei"
                binary.parent.mkdir(parents=True)
                binary.write_text(recorder)
                binary.chmod(0o755)
                runtime = base / "runtime"
                env = os.environ.copy()
                env.pop(FUSED_CACHE_ENV, None)
                if inherited is not None:
                    env[FUSED_CACHE_ENV] = inherited
                env["MEI_SWIFT"] = str(swift)
                before = env.copy()
                argv = [a.format(model=model, kv=kv, build=build, repo=repo) for a in BASE_ARGS]
                # No listener is created; port 0 avoids checking a model port.
                argv[argv.index("--port") + 1] = "0"
                extra = [] if selected is None else [FUSED_CACHE_FLAG, selected]
                res = subprocess.run(
                    ["bash", str(START_MEI), *argv, "--runtime-base", str(runtime), *extra],
                    capture_output=True, text=True, timeout=30, env=env)
                self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
                effective = selected if selected is not None else inherited
                self.assertIn(f"recorder env: {effective or 'unset'}\n",
                              (runtime / "logs" / "server.log").read_text())
                helper_env = f"recorder env: {inherited or 'unset'}\n"
                self.assertIn(helper_env, (runtime / "logs" / "build.log").read_text())
                self.assertIn(helper_env, res.stdout)  # metallib helper
                self.assertNotIn(FUSED_CACHE_FLAG, (runtime / "logs" / "server.log").read_text())
                self.assertEqual(env, before)
                self.assertFalse((runtime / "server.pid").exists())
                launch = _launch_argv(res)
                if selected is None:
                    self.assertEqual(launch[0], str(binary))
                    self.assertNotIn(FUSED_CACHE_ENV, res.stdout)
                else:
                    self.assertEqual(launch[:3], ["env", f"{FUSED_CACHE_ENV}={selected}", str(binary)])


class MeiConfigDryRunTests(unittest.TestCase):
    """Real config -> wrapper -> exact argv, with metadata-only path fixtures.

    No real model/source/runtime path is accessed. The local-vMLX guard is an
    explicit echo stub; it is not a source-identity or inference test.
    """

    def _config_dry_run(self, cfg, *, script=START_MEI):
        base, model, repo, kv, build = _stub_env()
        self.addCleanup(shutil.rmtree, base)
        paths = {
            "--model-dir": model, "--mei-repo": repo, "--build-dir": build,
            "--runtime-base": str(base / "runtime"),
            "--vmlx-repo": str(base / "vmlx"), "--kv-cache-dir": kv,
        }
        command = shlex.split(cfg["benchmark_launch_command"].replace("\\\n", " "))
        wrapper = command.index("runner/start_mei_server.sh")
        self.assertEqual(command[wrapper - 1], "bash")
        # Apply only literal env assignments; never execute a shell prefix.
        # Existing research configs' inherited settings must remain intact.
        env = os.environ.copy()
        env.pop(FUSED_CACHE_ENV, None)
        prefix = command[:wrapper - 1]
        if prefix:
            self.assertEqual(prefix[0], "env")
            for assignment in prefix[1:]:
                key, separator, value = assignment.partition("=")
                self.assertEqual(separator, "=")
                env[key] = value
        args = command[wrapper + 1:]
        for flag, value in paths.items():
            if flag in args:
                self.assertEqual(args.count(flag), 1)
                args[args.index(flag) + 1] = value
        for flag in ("--mei-repo", "--build-dir", "--runtime-base"):
            if flag not in args:
                args += [flag, paths[flag]]
        if "--vmlx-repo" in args:
            scripts = Path(repo) / "scripts"
            scripts.mkdir()
            (scripts / "use_local_vmlx.sh").write_text(
                "#!/bin/bash\nprintf 'override guard: '; printf '%q ' \"$@\"; printf '\\n'\n")
        before = {p.relative_to(base) for p in base.rglob("*")}
        res = subprocess.run(["bash", str(script), *args, "--dry-run"],
                             capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual({p.relative_to(base) for p in base.rglob("*")}, before)
        self.assertFalse(Path(build).exists())
        self.assertFalse(Path(paths["--runtime-base"]).exists())
        return res, paths

    def test_lfm_experimental_config_dry_run_has_exact_launch_argv(self):
        config = REPO / "configs" / "LiquidAI-LFM2.5-24B-A2B-MLX-4bit" / "mei.yaml"
        res, paths = self._config_dry_run(yaml.safe_load(config.read_text()))
        self.assertEqual(_launch_argv(res), [
            "env", f"{FUSED_CACHE_ENV}=0",
            str(Path(paths["--build-dir"]) / "release" / "mei"),
            "--model-dir", paths["--model-dir"],
            "--served-model-id", "LiquidAI/LFM2.5-24B-A2B-MLX-4bit",
            "--host", "127.0.0.1", "--port", "8029", "--context-cap", "65536",
            "--temperature", "0.1", "--top-p", "0", "--top-k", "50",
            "--emit-reasoning", "true", "--cache-reuse", "true",
            "--max-tokens", "4096", "--prefill-step-size", "1024",
            "--max-cache-blocks", "4097",
            "--min-p", "0", "--repetition-penalty", "1.05",
            "--model-profile", "lfm2.5-24b-a2b",
            "--memory-limit-bytes", "32000000000", "--load-mmap", "false",
        ])
        self.assertIn(
            f"override guard: --path {paths['--vmlx-repo']} "
            "--revision 22969e9555b5e86df862e43e3d7356575d3dd053 "
            f"--build-dir {paths['--build-dir']} --dry-run", res.stdout)

    def test_candidate4_differs_from_immutable_candidate3_only_in_cache_policy(self):
        raw = _candidate3_file(LFM_CONFIG_PATH)
        self.assertEqual(hashlib.sha256(raw).hexdigest()[:12], "63f2b2fa27ff")
        predecessor = yaml.safe_load(raw)
        candidate = yaml.safe_load((REPO / LFM_CONFIG_PATH).read_text())
        documentary = {"mei_source_commit", "settings", "known_gaps"}
        execution = {"benchmark_launch_command", "max_cache_blocks"}
        self.assertEqual({k: v for k, v in candidate.items() if k not in documentary | execution},
                         {k: v for k, v in predecessor.items() if k not in documentary | execution})
        self.assertIs(type(candidate["max_cache_blocks"]), int)
        self.assertEqual(candidate["max_cache_blocks"], 4097)
        self.assertNotIn("max_cache_blocks", predecessor)
        self.assertEqual(candidate["mei_source_commit"], "faf48a331b6bede352c334e0c6e3d4d4d7e10372")
        launch = shlex.split(candidate["benchmark_launch_command"].replace("\\\n", " "))
        self.assertEqual(launch.count(MAX_CACHE_BLOCKS_FLAG), 1)
        i = launch.index(MAX_CACHE_BLOCKS_FLAG)
        self.assertEqual(launch[i + 1], str(candidate["max_cache_blocks"]))
        del launch[i:i + 2]
        self.assertEqual(launch[launch.index("--cache-reuse") + 1], "true")
        launch[launch.index("--cache-reuse") + 1] = "false"
        self.assertEqual(launch, shlex.split(predecessor["benchmark_launch_command"].replace("\\\n", " ")))

        # Compare actual wrapper output too, normalizing ONLY fixture paths.
        old_res, old_paths = self._config_dry_run(predecessor)
        res, paths = self._config_dry_run(candidate)
        def normalized(result, fixture_paths):
            argv = _launch_argv(result)
            for flag, path in fixture_paths.items():
                argv = [token.replace(path, "{" + flag + "}") for token in argv]
            return argv
        old_argv = normalized(old_res, old_paths)
        argv = normalized(res, paths)
        i = argv.index(MAX_CACHE_BLOCKS_FLAG)
        self.assertEqual(argv[i:i + 2], [MAX_CACHE_BLOCKS_FLAG, "4097"])
        del argv[i:i + 2]
        argv[argv.index("--cache-reuse") + 1] = "false"
        self.assertEqual(argv, old_argv)

    def test_all_other_configs_are_byte_identical_to_immutable_candidate3(self):
        files = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", CANDIDATE3_COMMIT, "--", "configs"],
            cwd=REPO, text=True).splitlines()
        self.assertTrue(files)
        for relative in files:
            if relative == LFM_CONFIG_PATH:
                continue
            with self.subTest(path=relative):
                self.assertEqual((REPO / relative).read_bytes(), _candidate3_file(relative))
        self.assertEqual({str(p.relative_to(REPO)) for p in (REPO / "configs").rglob("*.yaml")},
                         {p for p in files if p.endswith(".yaml")})

    def test_other_mei_configs_keep_explicit_values_and_absent_defaults(self):
        configs = [(p, cfg) for p in sorted((REPO / "configs").glob("*/*.yaml"))
                   if p.parent.name != "LiquidAI-LFM2.5-24B-A2B-MLX-4bit"
                   and "runner/start_mei_server.sh" in
                   (cfg := yaml.safe_load(p.read_text())).get("benchmark_launch_command", "")]
        self.assertTrue(configs)
        saw_absent = set()
        for path, cfg in configs:
            with self.subTest(config=str(path.relative_to(REPO))):
                command = shlex.split(cfg["benchmark_launch_command"].replace("\\\n", " "))
                res, _ = self._config_dry_run(cfg)
                argv = _launch_argv(res)
                self.assertNotIn(FUSED_CACHE_FLAG, command)
                self.assertNotIn("fused_gate_up_cache_limit_bytes", cfg)
                self.assertNotIn("max_cache_blocks", cfg)
                self.assertNotIn(MAX_CACHE_BLOCKS_FLAG, command)
                self.assertNotIn(MAX_CACHE_BLOCKS_FLAG, argv)
                self.assertNotIn(FUSED_CACHE_ENV, res.stdout)
                self.assertNotEqual(argv[0], "env")
                for flag in ("--prefill-step-size", "--memory-limit-bytes", "--max-tokens",
                             "--model-profile", "--load-mmap", "--repetition-penalty"):
                    if flag in command:
                        self.assertEqual(argv.count(flag), 1)
                        self.assertEqual(argv[argv.index(flag) + 1], command[command.index(flag) + 1])
                    else:
                        self.assertNotIn(flag, argv)
                        saw_absent.add(flag)
                # Cache-off is LFM-only; explicit values and the wrapper's
                # existing true default remain unchanged for every other lane.
                self.assertEqual(argv.count("--cache-reuse"), 1)
                expected_cache = command[command.index("--cache-reuse") + 1] \
                    if "--cache-reuse" in command else "true"
                self.assertEqual(argv[argv.index("--cache-reuse") + 1], expected_cache)
        # Fail if the config inventory no longer exercises either absence path.
        self.assertTrue({"--prefill-step-size", "--memory-limit-bytes"} <= saw_absent)

    def test_other_mei_configs_keep_entire_candidate3_wrapper_vectors(self):
        with tempfile.TemporaryDirectory(prefix="mei-old-config-wrapper-") as td:
            previous = Path(td) / "start_mei_server.sh"
            previous.write_bytes(_candidate3_file("runner/start_mei_server.sh"))
            for path in sorted((REPO / "configs").glob("*/*.yaml")):
                if str(path.relative_to(REPO)) == LFM_CONFIG_PATH:
                    continue
                cfg = yaml.safe_load(path.read_text())
                if "runner/start_mei_server.sh" not in cfg.get("benchmark_launch_command", ""):
                    continue
                with self.subTest(config=str(path.relative_to(REPO))):
                    old_res, old_paths = self._config_dry_run(cfg, script=previous)
                    res, paths = self._config_dry_run(cfg)
                    def normalized(result, fixture_paths):
                        argv = _launch_argv(result)
                        for flag, value in fixture_paths.items():
                            argv = [token.replace(value, "{" + flag + "}") for token in argv]
                        return argv
                    self.assertEqual(normalized(res, paths), normalized(old_res, old_paths))


if __name__ == "__main__":
    unittest.main()

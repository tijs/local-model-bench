"""Regression tests for runner/run_fixture_suite.py.

These build a real, throwaway git repo per test (not a mock) since the
functions under test shell out to `git` directly — a mocked git would not
have caught any of the bugs these tests pin down.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_fixture_suite as rfs


def _init_git_repo(run_dir):
    subprocess.run(["git", "init", "-q"], cwd=run_dir, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "-A"],
        cwd=run_dir, check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "baseline"],
        cwd=run_dir, check=True,
    )
    subprocess.run(["git", "tag", "baseline"], cwd=run_dir, check=True)


class RestoreHarnessFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = Path(self.tmp) / "run"
        self.run_dir.mkdir()
        (self.run_dir / "package.json").write_text('{"name": "x"}\n')
        _init_git_repo(self.run_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gitignored_dangerous_file_is_still_removed(self):
        # CR3-5: git ls-files (the old sweep mechanism) never sees a file
        # excluded by .gitignore, and `git add -A` silently skips it too
        # — an agent editing .gitignore to hide its own vitest.config.ts
        # used to defeat the entire dangerous-file sweep.
        (self.run_dir / ".gitignore").write_text("vitest.config.ts\n")
        (self.run_dir / "vitest.config.ts").write_text("export default {}\n")
        rfs.restore_harness_files(self.run_dir)
        self.assertFalse((self.run_dir / "vitest.config.ts").exists())

    def test_vite_config_variant_is_dangerous(self):
        # CR3-4: _DANGEROUS_NEW_FILES originally only listed
        # vitest.config.{ts,js,mjs}, missing the whole vite.config.*
        # family (a Vitest project configured via vite.config.ts's own
        # `test:` block is a normal setup).
        (self.run_dir / "vite.config.mts").write_text("export default {}\n")
        rfs.restore_harness_files(self.run_dir)
        self.assertFalse((self.run_dir / "vite.config.mts").exists())

    def test_tampered_gitignore_is_restored_to_baseline_content(self):
        # CR3-5, second half: .gitignore itself should be restored from
        # baseline, not just used (in its tampered form) to decide what
        # to scan.
        (self.run_dir / ".gitignore").write_text("node_modules/\n")
        subprocess.run(["git", "add", "-A"], cwd=self.run_dir, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "-m", "add gitignore"],
            cwd=self.run_dir, check=True,
        )
        subprocess.run(["git", "tag", "-f", "baseline"], cwd=self.run_dir, check=True)
        (self.run_dir / ".gitignore").write_text("node_modules/\nvitest.config.ts\n")
        rfs.restore_harness_files(self.run_dir)
        self.assertEqual((self.run_dir / ".gitignore").read_text(), "node_modules/\n")

    def test_legitimate_source_file_is_untouched(self):
        (self.run_dir / "src.ts").write_text("export const x = 1;\n")
        rfs.restore_harness_files(self.run_dir)
        self.assertTrue((self.run_dir / "src.ts").exists())
        self.assertEqual((self.run_dir / "src.ts").read_text(), "export const x = 1;\n")


class GradeMutationGuardTests(unittest.TestCase):
    """CR3-15: agent_test_file/require_kill were documented in
    tasks/SCHEMA.md but never actually enforced by grade_mutation()."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = Path(self.tmp) / "run"
        self.run_dir.mkdir()
        (self.run_dir / "src.rs").write_text("pub fn f() {}\n")
        _init_git_repo(self.run_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_agent_test_file_fails_even_if_test_command_would_pass(self):
        task = {
            "check": {
                "source_file": "src.rs",
                "agent_test_file": "tests/never_created.rs",
                "test_command": "true",
                "cwd": ".",
                "mutants": [],
            }
        }
        passed, output, _ = rfs.grade_mutation(task, self.run_dir)
        self.assertFalse(passed)
        self.assertIn("agent_test_file", output)

    def test_require_kill_other_than_all_is_rejected(self):
        task = {
            "check": {
                "source_file": "src.rs",
                "require_kill": "majority",
                "test_command": "true",
                "cwd": ".",
                "mutants": [],
            }
        }
        passed, output, _ = rfs.grade_mutation(task, self.run_dir)
        self.assertFalse(passed)
        self.assertIn("require_kill", output)

    def test_require_kill_all_default_is_not_flagged(self):
        # Regression guard: the two checks above must not misfire on the
        # real, unset-require_kill case every actual testwrite task uses.
        task = {
            "check": {
                "source_file": "src.rs",
                "agent_test_file": "tests/does_exist.rs",
                "test_command": "true",
                "cwd": ".",
                "mutants": [],
            }
        }
        (self.run_dir / "tests").mkdir()
        (self.run_dir / "tests" / "does_exist.rs").write_text("// test\n")
        passed, output, _ = rfs.grade_mutation(task, self.run_dir)
        self.assertNotIn("require_kill", output)
        self.assertNotIn("agent_test_file", output)


class StaleBuildCacheGitignoreTests(unittest.TestCase):
    """CR3-9: reset_fixture() only ever gitignored node_modules/, so an
    agent's own `cargo test`/`swift test` mid-run could create a fresh
    target/ or .build/ that restore_harness_files()'s `git add -A` then
    staged in full — confirmed live to add 356 files from one `cargo
    test` in kiem_mini's rust/ alone."""

    def test_every_stale_build_cache_dir_is_gitignored(self):
        tmp = tempfile.mkdtemp()
        try:
            run_dir = Path(tmp) / "run"
            rfs.reset_fixture("kiem_mini", run_dir)
            gitignore = (run_dir / ".gitignore").read_text()
            for d in rfs._STALE_BUILD_CACHE_DIRS:
                self.assertIn(f"{d}/", gitignore, f"{d}/ missing from .gitignore")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AgentWorkspaceIsolationTests(unittest.TestCase):
    def test_prompt_names_absolute_ephemeral_run_root(self):
        run_dir = Path("/tmp/bench-run-123/run")
        prompt = rfs.isolated_agent_prompt("Implement it", run_dir)
        self.assertIn(str(run_dir), prompt)
        self.assertIn("ONLY inside", prompt)
        self.assertIn("Do not edit the source fixture", prompt)

    def test_preserve_tree_restores_agent_side_effects(self):
        root = Path(tempfile.mkdtemp())
        try:
            (root / "src").mkdir()
            original = root / "src" / "lib.rs"
            original.write_text("baseline\n")
            state = {}
            with rfs.preserve_tree(root, state):
                original.write_text("contaminated\n")
                (root / "new.txt").write_text("new\n")
            self.assertEqual(original.read_text(), "baseline\n")
            self.assertFalse((root / "new.txt").exists())
            self.assertTrue(state["changed"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_repository_guard_removes_escape_but_keeps_result_artifacts(self):
        root = Path(tempfile.mkdtemp())
        try:
            (root / "runner" / "runs").mkdir(parents=True)
            (root / "results").mkdir()
            (root / "fixtures").mkdir()
            baseline = root / "fixtures" / "base.txt"
            baseline.write_text("baseline\n")
            state = {}
            with rfs.preserve_repository(root, state):
                baseline.write_text("contaminated\n")
                (root / "src").mkdir()
                (root / "src" / "lib.rs").write_text("escaped\n")
                (root / "results" / "transcript.log").write_text("keep\n")
                (root / "runner" / "runs" / "work.txt").write_text("keep\n")
            self.assertEqual(baseline.read_text(), "baseline\n")
            self.assertFalse((root / "src").exists())
            self.assertTrue((root / "results" / "transcript.log").exists())
            self.assertTrue((root / "runner" / "runs" / "work.txt").exists())
            self.assertTrue(state["changed"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class RepositoryEntriesScopeTests(unittest.TestCase):
    """M2 (improvement plan): the byte-manifest guard scanned the WHOLE
    repo, including .venv — measured on the real checkout at 31,129 files
    / 1.2GB / 5.7s, read TWICE per coding task (baseline + comparison),
    of which 30,957 files were the virtualenv. Narrowed to the
    benchmark-owned subtrees, with git-ignored paths skipped."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp).resolve()
        for sub in ("runner", "tasks", "checks", "fixtures", "configs"):
            (self.root / sub).mkdir()
            (self.root / sub / "kept.txt").write_text(f"{sub} content\n")
        (self.root / "AGENTS.md").write_text("root file\n")
        # Ignored content, inside and outside a protected subtree.
        (self.root / ".venv" / "lib").mkdir(parents=True)
        (self.root / ".venv" / "lib" / "huge.bin").write_bytes(b"x" * 4096)
        (self.root / "runner" / "__pycache__").mkdir()
        (self.root / "runner" / "__pycache__" / "x.pyc").write_bytes(b"\x00" * 64)
        (self.root / "fixtures" / "node_modules").mkdir()
        (self.root / "fixtures" / "node_modules" / "dep.js").write_text("dep\n")
        # Intentional run output, never guarded.
        (self.root / "results").mkdir()
        (self.root / "results" / "log.jsonl").write_text('{"row": 1}\n')
        (self.root / ".gitignore").write_text(
            ".venv/\n__pycache__/\nnode_modules/\nrunner/runs/\n"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_protected_subtrees_are_scanned_byte_for_byte(self):
        entries = rfs._repository_entries(self.root)
        for sub in ("runner", "tasks", "checks", "fixtures", "configs"):
            self.assertEqual(entries[f"{sub}/kept.txt"], ("file", f"{sub} content\n".encode()))
        self.assertEqual(entries["AGENTS.md"], ("file", b"root file\n"))

    def test_gitignored_content_is_not_scanned(self):
        entries = rfs._repository_entries(self.root)
        for leaked in (
            ".venv/lib/huge.bin",
            "runner/__pycache__/x.pyc",
            "fixtures/node_modules/dep.js",
        ):
            self.assertNotIn(leaked, entries, f"{leaked} should not be scanned")

    def test_results_output_is_not_guarded(self):
        entries = rfs._repository_entries(self.root)
        self.assertNotIn("results/log.jsonl", entries)

    def test_a_new_top_level_directory_is_still_detected(self):
        # Narrowing must not create a blind spot: an agent creating an
        # entirely new top-level directory is still an escape.
        state = {}
        with rfs.preserve_repository(self.root, state):
            (self.root / "evil").mkdir()
            (self.root / "evil" / "payload.sh").write_text("rm -rf /\n")
        self.assertTrue(state["changed"])
        self.assertFalse((self.root / "evil").exists())

    def test_tampering_inside_a_protected_subtree_is_reverted(self):
        state = {}
        with rfs.preserve_repository(self.root, state):
            (self.root / "checks" / "kept.txt").write_text("tampered\n")
            (self.root / "fixtures" / "added.rs").write_text("fn main() {}\n")
        self.assertTrue(state["changed"])
        self.assertEqual((self.root / "checks" / "kept.txt").read_text(), "checks content\n")
        self.assertFalse((self.root / "fixtures" / "added.rs").exists())

    def test_writes_to_ignored_and_output_paths_are_left_alone(self):
        state = {}
        with rfs.preserve_repository(self.root, state):
            (self.root / "results" / "transcript.log").write_text("keep me\n")
            (self.root / ".venv" / "lib" / "new.bin").write_bytes(b"y" * 16)
        self.assertFalse(state["changed"])
        self.assertTrue((self.root / "results" / "transcript.log").exists())
        self.assertTrue((self.root / ".venv" / "lib" / "new.bin").exists())

    def test_falls_back_safely_when_git_is_unavailable(self):
        with unittest.mock.patch(
            "run_fixture_suite._git_ignored_entries", return_value=None
        ):
            entries = rfs._repository_entries(self.root)
        # The static fallback list must still keep the virtualenv and
        # bytecode caches out of the scan.
        self.assertNotIn(".venv/lib/huge.bin", entries)
        self.assertNotIn("runner/__pycache__/x.pyc", entries)
        self.assertIn("runner/kept.txt", entries)


class SandboxTests(unittest.TestCase):
    """M3 (improvement plan): `hermes chat --yolo` auto-approves every
    tool call, so a mis-resolved path could write to sibling projects or
    the benchmark checkout. The restoration guards revert such writes but
    are detect-and-repair; this prevents them."""

    def test_profile_denies_repo_and_siblings_but_allows_the_run_dir(self):
        # Paths are resolved (macOS's /tmp is a symlink to /private/tmp)
        # because seatbelt matches on real paths, not symlinked ones.
        run_dir = Path("/tmp/bench-run-1/run").resolve()
        profile = rfs.sandbox_profile(run_dir)
        repo = str(Path(rfs.REPO).resolve())
        self.assertIn(f'(deny file-write* (subpath "{repo}"))', profile)
        self.assertIn(f'(deny file-write* (subpath "{Path(repo).parent}"))', profile)
        self.assertIn(f'(allow file-write* (subpath "{run_dir}"))', profile)

    def test_run_dir_allow_comes_after_every_containing_deny(self):
        # SBPL is last-match-wins, so an allow placed before a deny that
        # contains it would be silently overridden — the profile would
        # compile fine and block every build.
        profile = rfs.sandbox_profile("/tmp/bench-run-1/run")
        lines = profile.splitlines()
        last_deny = max(i for i, line in enumerate(lines) if line.startswith("(deny"))
        run_allow = next(i for i, line in enumerate(lines) if "/tmp/bench-run-1/run" in line)
        self.assertGreater(run_allow, last_deny)

    def test_disabled_by_env_var_returns_the_command_unchanged(self):
        with unittest.mock.patch.object(rfs, "SANDBOX_ENABLED", False):
            cmd, sandboxed = rfs.sandbox_wrapped_command(["echo", "hi"], "/tmp/run")
        self.assertEqual(cmd, ["echo", "hi"])
        self.assertFalse(sandboxed)

    def test_unavailable_sandbox_degrades_to_running_unwrapped(self):
        # A missing/broken seatbelt must not turn every coding task into
        # a harness error.
        with unittest.mock.patch.object(rfs, "_sandbox_available", return_value=False):
            cmd, sandboxed = rfs.sandbox_wrapped_command(["echo", "hi"], "/tmp/run")
        self.assertEqual(cmd, ["echo", "hi"])
        self.assertFalse(sandboxed)

    @unittest.skipUnless(
        sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").exists(),
        "seatbelt only exists on macOS",
    )
    def test_live_seatbelt_blocks_the_repo_and_allows_the_run_dir(self):
        # The real thing: a scratch tree standing in for the repo, so no
        # actual benchmark file is ever written during the test.
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            fake_repo = tmp / "local-model-bench"
            run_dir = fake_repo / "runner" / "runs" / "tmpx" / "run"
            run_dir.mkdir(parents=True)
            (fake_repo / "fixtures").mkdir()
            sibling = tmp / "some-other-project"
            sibling.mkdir()

            with unittest.mock.patch.object(rfs, "REPO", fake_repo):
                profile = rfs.sandbox_profile(run_dir)
                if not rfs._sandbox_available(profile):
                    self.skipTest("seatbelt self-test failed in this environment")

                def _write(target):
                    return subprocess.run(
                        ["/usr/bin/sandbox-exec", "-p", profile,
                         "/bin/sh", "-c", f"echo x > {target}"],
                        capture_output=True,
                    ).returncode

                self.assertEqual(_write(run_dir / "ok.txt"), 0, "run dir must be writable")
                self.assertNotEqual(
                    _write(fake_repo / "fixtures" / "escaped.rs"), 0,
                    "a write into the benchmark checkout must be blocked",
                )
                self.assertNotEqual(
                    _write(sibling / "escaped.txt"), 0,
                    "a write into a sibling project must be blocked",
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ExtractHermesSessionStatsTests(unittest.TestCase):
    """F6: the coding suite previously logged zero performance data from
    the actual target workload — no tokens, no turn count, no tool-call
    data. extract_hermes_session_stats() pulls this from hermes's own
    SQLite session store via `hermes sessions export`."""

    def test_no_session_id_in_either_stream_degrades_gracefully(self):
        stats = rfs.extract_hermes_session_stats(
            "no session id anywhere in this text", "nor in this one"
        )
        self.assertEqual(stats, rfs._EMPTY_SESSION_STATS)

    def test_session_id_is_found_on_stderr(self):
        # H2 (improvement plan): current Hermes prints its `session_id:`
        # banner on STDERR, but this only ever searched stdout — so every
        # coding row silently logged an empty telemetry block even when
        # the task graded fine.
        session = {"api_call_count": 3, "tool_call_count": 4, "messages": []}
        with unittest.mock.patch("run_fixture_suite.subprocess.run") as m:
            m.return_value = unittest.mock.Mock(returncode=0, stdout=json.dumps(session))
            stats = rfs.extract_hermes_session_stats(
                stdout="ordinary agent chatter, no banner here\n",
                stderr="session_id: from_stderr_123\n",
            )
        self.assertEqual(stats["hermes_turns"], 3)
        self.assertEqual(stats["hermes_tool_calls"], 4)
        self.assertIn("from_stderr_123", m.call_args[0][0])

    def test_session_id_on_stdout_still_works(self):
        # Both streams are checked rather than just swapped, so the
        # extraction survives a Hermes version that puts it back.
        session = {"api_call_count": 7, "tool_call_count": 8, "messages": []}
        with unittest.mock.patch("run_fixture_suite.subprocess.run") as m:
            m.return_value = unittest.mock.Mock(returncode=0, stdout=json.dumps(session))
            stats = rfs.extract_hermes_session_stats(
                stdout="session_id: from_stdout_456\n", stderr="",
            )
        self.assertEqual(stats["hermes_turns"], 7)
        self.assertIn("from_stdout_456", m.call_args[0][0])

    def test_stderr_wins_when_both_streams_carry_a_banner(self):
        # Hermes writes its own banner to stderr; anything matching on
        # stdout is far more likely to be the agent echoing text back.
        session = {"api_call_count": 1, "tool_call_count": 0, "messages": []}
        with unittest.mock.patch("run_fixture_suite.subprocess.run") as m:
            m.return_value = unittest.mock.Mock(returncode=0, stdout=json.dumps(session))
            rfs.extract_hermes_session_stats(
                stdout="session_id: echoed_by_the_agent\n",
                stderr="session_id: real_one\n",
            )
        self.assertIn("real_one", m.call_args[0][0])

    def test_stdout_only_call_still_supported(self):
        # The stderr parameter defaults, so an old single-argument call
        # site (or a caller that genuinely has only stdout) still works.
        stats = rfs.extract_hermes_session_stats("nothing here")
        self.assertEqual(stats, rfs._EMPTY_SESSION_STATS)

    def test_export_subprocess_failure_degrades_gracefully(self):
        with unittest.mock.patch("run_fixture_suite.subprocess.run") as m:
            m.return_value = unittest.mock.Mock(returncode=1, stdout="")
            stats = rfs.extract_hermes_session_stats("session_id: some_id_that_fails\n")
        self.assertEqual(stats, rfs._EMPTY_SESSION_STATS)

    def test_real_session_json_is_parsed_correctly(self):
        session = {
            "api_call_count": 9, "tool_call_count": 10,
            "input_tokens": 105920, "output_tokens": 3264, "reasoning_tokens": 0,
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "tool", "tool_name": "patch", "content": json.dumps({"success": True, "diff": "..."})},
                {"role": "tool", "tool_name": "patch", "content": json.dumps({"success": False, "error": "no match"})},
                # A tool call whose own exit_code reads 0 despite the
                # output clearly showing a compile failure (confirmed live
                # against a real session — piping can swallow the real
                # exit status) — must still be counted via the output-text
                # fallback, not just the exit_code field.
                {"role": "tool", "tool_name": "terminal", "content": json.dumps({
                    "exit_code": 0, "error": None,
                    "output": "error: could not compile `notekeep` due to 1 previous error",
                })},
                {"role": "tool", "tool_name": "terminal", "content": json.dumps({
                    "exit_code": 0, "error": None, "output": "Finished dev profile",
                })},
            ],
        }
        with unittest.mock.patch("run_fixture_suite.subprocess.run") as m:
            m.return_value = unittest.mock.Mock(returncode=0, stdout=json.dumps(session) + "\n")
            stats = rfs.extract_hermes_session_stats("", "session_id: real_session_id\n")
        self.assertEqual(stats["hermes_turns"], 9)
        self.assertEqual(stats["hermes_tool_calls"], 10)
        self.assertEqual(stats["hermes_input_tokens"], 105920)
        # 2 real errors: the explicit success:false, and the exit_code:0-
        # but-actually-failed compile call. The final successful terminal
        # call must NOT be counted.
        self.assertEqual(stats["hermes_tool_errors"], 2)


if __name__ == "__main__":
    unittest.main()

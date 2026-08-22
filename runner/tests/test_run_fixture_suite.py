"""Regression tests for runner/run_fixture_suite.py.

These build a real, throwaway git repo per test (not a mock) since the
functions under test shell out to `git` directly — a mocked git would not
have caught any of the bugs these tests pin down.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()

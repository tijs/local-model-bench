"""Smoke test for runner/grade_mutation.sh against a real, compilable
fixture (kiem_mini's rust/ crate) — not a mock, since the bug this pins
down (CR3-1) was in the script's own backup/restore shell logic, which a
mocked subprocess call would never exercise.

Run: uv run --with pyyaml python3 -m unittest discover -s runner/tests -v
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_fixture_suite as rfs

REPO = rfs.REPO
GRADE_MUTATION_SH = REPO / "runner" / "grade_mutation.sh"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class GradeMutationBackupRestoreTests(unittest.TestCase):
    """CR3-1: Round 2's L-3+L-4 commit accidentally deleted the line that
    actually backed up the source file before swapping in mutants — every
    `cp "$backup" "$full_source"` was overwriting the real implementation
    with an EMPTY file. Confirmed live at the time: after a clean run, the
    source file was left 0 bytes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = Path(self.tmp) / "run"
        rfs.reset_fixture("kiem_mini", self.run_dir)
        self.source_file = "rust/src/lib.rs"
        self.full_source = self.run_dir / self.source_file
        self.original_hash = _sha256(self.full_source)

        # A real mutant: extract_tags always returns an empty Vec, which
        # the fixture's own existing tests/basic.rs (not overlaid — it's
        # already part of the fixture, standing in for "the agent's test
        # file" here) should catch.
        original = self.full_source.read_text()
        mutant_source = original.replace(
            "text.split_whitespace()\n"
            "        .filter(|tok| tok.starts_with('#'))\n"
            "        .map(|tok| tok.trim_start_matches('#').to_string())\n"
            "        .collect()",
            "Vec::new()",
        )
        assert mutant_source != original, "mutant substitution did not match — fixture source changed?"
        self.mutant_path = Path(self.tmp) / "mutant1_lib.rs"
        self.mutant_path.write_text(mutant_source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *mutants):
        return subprocess.run(
            [str(GRADE_MUTATION_SH), str(self.run_dir), self.source_file,
             "cargo test", "rust", *[str(m) for m in mutants]],
            capture_output=True, text=True,
        )

    def test_source_file_is_byte_identical_after_a_clean_run(self):
        proc = self._run(self.mutant_path)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(_sha256(self.full_source), self.original_hash)

    def test_mutant_that_is_actually_killed_reports_pass(self):
        proc = self._run(self.mutant_path)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertIn("1/1 mutants killed", proc.stdout)

    def test_missing_mutant_file_fails_cleanly_without_corrupting_source(self):
        missing = Path(self.tmp) / "does_not_exist.rs"
        proc = self._run(missing)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("mutant file not found", proc.stderr)
        # The whole point of CR3-1: even a hard-fail path before any
        # mutant swap must never leave the source file corrupted.
        self.assertEqual(_sha256(self.full_source), self.original_hash)

    def test_source_file_restored_even_when_no_mutants_are_killed(self):
        # A mutant identical to the real source should SURVIVE (agent's
        # tests can't distinguish it), but the source file must still be
        # restored afterward regardless of the pass/fail outcome.
        identical_mutant = Path(self.tmp) / "mutant_identical.rs"
        identical_mutant.write_text(self.full_source.read_text())
        proc = self._run(identical_mutant)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SURVIVED", proc.stdout)
        self.assertEqual(_sha256(self.full_source), self.original_hash)


if __name__ == "__main__":
    unittest.main()

"""Regression tests for M5 and the Low findings of the 2026-08-24
improvement plan.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

import bench_common
import build_leaderboard
import run_bench
import run_fixture_suite as rfs

REPO = bench_common.REPO


class SpeedFloorDocstringTests(unittest.TestCase):
    """M5: run_bench.py's docstring said the speed floor was 10 tok/s long
    after the active threshold became 4.0, so a reader taking the file at
    its word got the gate's behavior wrong."""

    def test_docstrings_name_the_constant_not_a_number(self):
        for module in (run_bench, build_leaderboard._speed_gated_configs):
            doc = module.__doc__ or ""
            with self.subTest(module=getattr(module, "__name__", module)):
                self.assertIn("MIN_HERMES_OPS_TOKENS_PER_SECOND", doc)

    def test_no_stale_speed_floor_number_is_restated(self):
        # Any "<n> tok/s" claim in these docstrings must agree with the
        # authoritative constant, or not be there at all.
        actual = bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND
        pattern = re.compile(r"(\d+(?:\.\d+)?)\s*tok/s")
        for name, doc in (
            ("run_bench", run_bench.__doc__ or ""),
            ("_speed_gated_configs", build_leaderboard._speed_gated_configs.__doc__ or ""),
        ):
            for found in pattern.findall(doc):
                with self.subTest(module=name, found=found):
                    self.assertEqual(
                        float(found), actual,
                        f"{name}'s docstring restates {found} tok/s but the "
                        f"constant is {actual} — refer to the constant instead",
                    )


class FindListeningPidTests(unittest.TestCase):
    """Low finding: `pids[0]` depended on lsof's unspecified output order,
    so two samples within one PeakRSSSampler run could resolve to
    different processes and splice their RSS into one 'peak'."""

    def _with_lsof_output(self, stdout):
        result = unittest.mock.Mock(stdout=stdout)
        with unittest.mock.patch("bench_common.subprocess.run", return_value=result):
            return bench_common._find_listening_pid(8012)

    def test_single_listener(self):
        self.assertEqual(self._with_lsof_output("4321\n"), 4321)

    def test_multiple_listeners_resolve_deterministically(self):
        # Same set, two different output orders, one answer.
        self.assertEqual(self._with_lsof_output("991\n77\n1200\n"), 77)
        self.assertEqual(self._with_lsof_output("1200\n991\n77\n"), 77)

    def test_no_listener(self):
        self.assertIsNone(self._with_lsof_output("\n"))

    def test_garbage_lines_are_skipped_not_fatal(self):
        # A stray non-numeric line used to abort the whole lookup via the
        # ValueError handler, losing a perfectly good pid on the next line.
        self.assertEqual(self._with_lsof_output("lsof: WARNING\n4321\n"), 4321)

    def test_subprocess_failure_returns_none(self):
        with unittest.mock.patch(
            "bench_common.subprocess.run", side_effect=OSError("no lsof")
        ):
            self.assertIsNone(bench_common._find_listening_pid(8012))


class TailSnippetTests(unittest.TestCase):
    """Low finding: `grade_output.strip()[-500:]` sliced mid-token, so a
    log row could start with 'rror[E0433]: failed to resolve' — neither
    greppable as an error code nor obviously truncated."""

    def test_short_text_is_unchanged(self):
        self.assertEqual(rfs.tail_snippet("all good\n", 500), "all good")

    def test_long_text_keeps_the_tail_and_marks_the_cut(self):
        text = "\n".join(f"line {i}" for i in range(500))
        out = rfs.tail_snippet(text, 100)
        self.assertTrue(out.startswith("[...truncated...]\n"))
        self.assertTrue(out.rstrip().endswith("line 499"))

    def test_cut_lands_on_a_line_boundary(self):
        text = "warning: something\n" * 20 + "error[E0433]: failed to resolve\n"
        out = rfs.tail_snippet(text, 40)
        body = out.split("\n", 1)[1]
        # No half-word at the start of the retained text.
        self.assertFalse(body.startswith("rror"))
        for line in body.splitlines():
            self.assertIn(line, {"warning: something", "error[E0433]: failed to resolve"})

    def test_one_very_long_line_is_not_shrunk_to_nothing(self):
        text = "x" * 400 + "\n" + "y" * 400
        out = rfs.tail_snippet(text, 100)
        self.assertGreaterEqual(len(out) - len("[...truncated...]\n"), 90)

    def test_none_and_empty_are_safe(self):
        self.assertEqual(rfs.tail_snippet(None, 100), "")
        self.assertEqual(rfs.tail_snippet("", 100), "")


class OverlayCheckFileModeTests(unittest.TestCase):
    """Low finding: shutil.copy2 preserves the SOURCE mode, so a checks/
    file that ended up 600 on one machine and 644 on another produced two
    different run trees from the same committed bytes."""

    def test_overlaid_check_files_are_normalized_to_644(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            src = tmp / "checks" / "demo_suite" / "demo-task"
            src.mkdir(parents=True)
            restrictive = src / "check_a.rs"
            restrictive.write_text("// check\n")
            os.chmod(restrictive, 0o600)
            (src / "check_b.rs").write_text("// check\n")

            run_dir = tmp / "run"
            run_dir.mkdir()
            with unittest.mock.patch.object(rfs, "REPO", tmp):
                copied = rfs.overlay_check_files(
                    "demo_suite", "demo-task", run_dir, "tests"
                )
            self.assertEqual(sorted(copied), ["check_a.rs", "check_b.rs"])
            for name in copied:
                mode = stat.S_IMODE((run_dir / "tests" / name).stat().st_mode)
                self.assertEqual(oct(mode), oct(0o644), f"{name} has mode {oct(mode)}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SwiftToolchainPinningTests(unittest.TestCase):
    """Low finding: the Swift checks ran `DEVELOPER_DIR=$(xcode-select -p)`
    — the machine's ambient default — while AGENTS.md required pinning to
    Xcode and wrongly claimed the check already did so. A task graded
    against Command Line Tools swift and one graded against Xcode swift
    are not the same task."""

    def _swift_commands(self):
        for task_file in sorted((REPO / "tasks").glob("*.yaml")):
            spec = yaml.safe_load(task_file.read_text())
            for task in spec.get("tasks") or []:
                command = (task.get("check") or {}).get("command", "")
                if "swift" in command:
                    yield task["id"], command

    def test_every_swift_check_pins_developer_dir(self):
        commands = list(self._swift_commands())
        self.assertTrue(commands, "no swift check found — test proves nothing")
        for task_id, command in commands:
            with self.subTest(task=task_id):
                self.assertNotIn("xcode-select", command)
                self.assertIn("/Applications/Xcode.app/Contents/Developer", command)
                self.assertIn("BENCH_DEVELOPER_DIR", command)


if __name__ == "__main__":
    unittest.main()

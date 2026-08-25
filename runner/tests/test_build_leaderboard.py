"""Regression tests for runner/build_leaderboard.py.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_leaderboard as bl


class HarnessErrorExclusionTests(unittest.TestCase):
    """CR3-6: harness_error rows (a genuine harness crash, e.g. an npm ci
    network blip — not a model failure) used to be counted exactly like
    a real trial everywhere: the main table's pass rate, the by-suite
    table, and the flaky-task grouping. Confirmed live with a synthetic
    2-pass/1-harness-crash group: pass rate read 67% (should be 100%,
    2/2 real trials) and the task was wrongly flagged "Flaky" (2/3)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _base_row(self, **overrides):
        row = {
            "suite": "hermes_ops",
            "task_id": "hermes_ops-selection",
            "task_type": "tool-selection",
            "model": "test-model",
            "inference_engine": "vllm-mlx",
            "quant": None,
            "config_path": None,
            "config_hash": None,
            "runner_git_sha": "abc123",
            "trial": 1,
            "pass": True,
            "grade_output": "PASS",
        }
        row.update(overrides)
        return row

    def test_harness_error_row_excluded_from_pass_rate(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        # sanity gate column added (finding F3) since this assertion was
        # first written — match on the surrounding cells rather than an
        # exact full-row string, so an unrelated column addition doesn't
        # make this brittle.
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        cells = [c.strip() for c in row_line.split("|")]
        self.assertEqual(cells[9], "2")     # tasks
        self.assertEqual(cells[10], "100%")  # pass rate

    def test_harness_error_row_not_flagged_as_flaky(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        flaky_section = text[text.index("## Flaky tasks"):text.index("## By suite")]
        self.assertIn("None observed", flaky_section)

    def test_harness_error_row_surfaced_in_own_section(self):
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=3, **{"pass": False, "harness_error": True, "grade_output": "HARNESS ERROR: network blip"}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        harness_section = text[text.index("## Harness errors"):]
        self.assertIn("network blip", harness_section)

    def test_genuine_flakiness_still_detected(self):
        # Regression guard: excluding harness_error rows must not also
        # suppress REAL model flakiness (a genuine pass/fail split with no
        # harness_error involved).
        self._write_log([
            self._base_row(trial=1, **{"pass": True}),
            self._base_row(trial=2, **{"pass": False}),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        flaky_section = text[text.index("## Flaky tasks"):text.index("## By suite")]
        self.assertIn("hermes_ops-selection", flaky_section)
        self.assertIn("1/2", flaky_section)

    def test_omlx_factors_are_visible_and_not_called_full_fp16(self):
        cfg = self.repo / "configs" / "qwen" / "omlx-mtp.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(
            "inference_engine: omlx\nquant_family: oQ4e-fp16 mixed precision\n"
            "cache_mode: ssd-warm\nmtp_mode: lightning\n"
            "temperature: 1\nreasoning_mode: medium\n"
        )
        import hashlib
        config_hash = hashlib.sha256(cfg.read_bytes()).hexdigest()[:12]
        self._write_log([self._base_row(
            model="qwen", inference_engine="omlx", config_path="configs/qwen/omlx-mtp.yaml",
            config_hash=config_hash,
        )])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| qwen |"))
        self.assertIn("| omlx |", row_line)  # primary engine column
        self.assertIn("| oQ4e-fp16 mixed precision | ssd-warm | lightning |", row_line)


class PeakRssColumnTests(unittest.TestCase):
    """F7: peak RSS is reported as the MAX across a group's rows, not an
    average — the 32GB unified-memory ceiling is a hard capacity limit,
    so the worst observed footprint is what matters for "does this fit,"
    not a smoothed mean that could hide a run that came close to
    swapping."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _base_row(self, **overrides):
        row = {
            "suite": "hermes_ops", "task_id": "hermes_ops-selection",
            "task_type": "tool-selection", "model": "test-model", "inference_engine": "vllm-mlx",
            "quant": None, "config_path": None, "config_hash": None,
            "runner_git_sha": "abc123", "trial": 1, "pass": True, "grade_output": "PASS",
        }
        row.update(overrides)
        return row

    def test_peak_rss_reports_the_max_not_the_average(self):
        self._write_log([
            self._base_row(trial=1, peak_rss_gb=18.2),
            self._base_row(trial=2, peak_rss_gb=25.9),
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        # 25.9 (the max) must appear; the average (22.05) must not be what's shown.
        self.assertIn("25.9", text)
        self.assertNotIn("22.1", text)

    def test_peak_rss_blank_when_never_measured(self):
        self._write_log([self._base_row(trial=1)])  # no peak_rss_gb key at all
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        self.assertIn("| — |", row_line)


class SlowPassColumnTests(unittest.TestCase):
    """F5: a PASS that took longer than INTERACTIVE_BUDGET_SECONDS is still
    counted in pass_rate (correctness didn't change) but must be surfaced
    as its own count — not silently blended in with a 5-second pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _base_row(self, **overrides):
        row = {
            "suite": "hermes_ops", "task_id": "hermes_ops-error-recovery",
            "task_type": "error-recovery", "model": "test-model", "inference_engine": "vllm-mlx",
            "quant": None, "config_path": None, "config_hash": None,
            "runner_git_sha": "abc123", "trial": 1, "pass": True, "grade_output": "PASS",
        }
        row.update(overrides)
        return row

    def test_slow_pass_counted_separately_from_pass_rate(self):
        self._write_log([
            self._base_row(trial=1, within_budget=True),
            self._base_row(trial=2, within_budget=False),  # e.g. a 3135s pass
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        cells = [c.strip() for c in row_line.split("|")]
        self.assertIn("100%", cells)  # both rows still correctness-passed
        self.assertIn("1", cells)     # exactly one of them was slow

    def test_failed_task_never_counted_as_a_slow_pass(self):
        # A genuine FAIL that also happens to be over-budget shouldn't
        # double-count against this signal — it's already a failure.
        self._write_log([self._base_row(trial=1, **{"pass": False, "within_budget": False})])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        cells = [c.strip() for c in row_line.split("|")]
        self.assertEqual(cells[11], "0")  # "slow passes" column


class CompositeRankingTests(unittest.TestCase):
    """F3: the leaderboard didn't rank anything — no composite score, no
    tie-break, alphabetical order. score = 0.5*coding + 0.3*hermes_ops +
    0.2*speed, renormalized over whichever axes a group actually has data
    for (a group with no coding rows yet must not be scored as if its
    missing coding axis were 0)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _best_overall_section(self, text):
        return text[text.index("## Best overall"):text.index("## Flaky tasks")]

    def test_sanity_excluded_from_pass_rate_and_shown_as_its_own_gate(self):
        self._write_log([
            {"suite": "sanity", "task_id": "sanity-basic", "task_type": "sanity",
             "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS"},
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": False,
             "grade_output": "FAIL"},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| m |"))
        cells = [c.strip() for c in row_line.split("|")]
        self.assertEqual(cells[6], "1/1")  # sanity gate: passed
        self.assertEqual(cells[9], "1")    # tasks: only the hermes_ops row counts
        self.assertEqual(cells[10], "0%")  # pass rate: sanity's PASS excluded, hermes_ops's FAIL counts

    def test_group_with_zero_coding_rows_is_excluded_even_with_hermes_ops_data(self):
        # Changed 2026-08-25: a group used to still get scored on
        # hermes_ops+speed alone with zero coding rows — that let a fast
        # model with no coding evidence at all rank above (or tie) a
        # genuinely coding-tested one, since "Best overall" is a QUALITY
        # ranking on a benchmark whose whole point is coding capability.
        # Now such a group is omitted entirely, same as a harness-error-
        # only group.
        self._write_log([
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "hermes-only-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS", "tokens_per_second": 20.0},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        self.assertNotIn("hermes-only-model", section)

    def test_pure_speed_group_no_longer_outscores_a_real_coding_pass(self):
        # The bug that prompted this whole rework: a group with ONLY a
        # tok/s number (no coding, no hermes_ops) used to score a perfect
        # 1.00 if it happened to be the fastest thing in the run — tied
        # with, or beating, a group with genuine 100% coding evidence.
        self._write_log([
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "speed-only-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS", "tokens_per_second": 200.0},
            {"suite": "kiem_mini", "task_id": "kiem_mini-feature", "task_type": "feature",
             "model": "coding-tested-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": "h1", "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS", "tokens_per_second": 5.0},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        self.assertNotIn("speed-only-model", section)
        self.assertIn("coding-tested-model", section)

    def test_dedups_to_the_most_evidenced_fragment_per_model_engine_quant(self):
        # A model tested twice under different config_hash/runner_sha (a
        # real config edit, or a harness-version change) used to show BOTH
        # fragments as independently-ranked rows — an early 1-task
        # fragment could then outrank that same model's own later, complete
        # sweep. Only the more-evidenced fragment should appear.
        rows = [
            {"suite": "kiem_mini", "task_id": "kiem_mini-feature", "task_type": "feature",
             "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": "early", "runner_git_sha": "sha1", "trial": 1, "pass": True,
             "grade_output": "PASS", "tokens_per_second": 50.0},
        ]
        for i, task_id in enumerate(["kiem_mini-feature", "kiem_mini-rename", "kiem_mini-debug"]):
            rows.append({
                "suite": "kiem_mini", "task_id": task_id, "task_type": "feature",
                "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
                "config_hash": "later", "runner_git_sha": "sha2", "trial": 1,
                "pass": i != 1,  # one deliberate fail, so this fragment isn't a perfect 100% either
                "grade_output": "PASS" if i != 1 else "FAIL", "tokens_per_second": 40.0,
            })
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        matches = [l for l in section.splitlines() if l.startswith("| ") and " m " in l]
        self.assertEqual(len(matches), 1, f"expected exactly one row for 'm', got: {matches}")
        self.assertIn("later", matches[0])  # the 3-task fragment, not the 1-task one

    def test_higher_coding_pass_rate_ranks_above_faster_but_less_correct_model(self):
        # Coding is weighted 0.5, speed only 0.2 — a model that's 100%
        # correct on coding but slow must still outrank one that's fast
        # but fails half its coding tasks. Also guards that the mild
        # coding-shrinkage added 2026-08-25 (k=1) doesn't invert this at
        # the smallest possible sample size (n=1 for both models here) —
        # a stronger k was tried first and DID invert it, which is why k=1
        # was chosen instead of the more textbook k=5.
        self._write_log([
            {"suite": "kiem_mini", "task_id": "kiem_mini-feature", "task_type": "feature",
             "model": "correct-but-slow", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": "h1", "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS", "tokens_per_second": 5.0},
            {"suite": "kiem_mini", "task_id": "kiem_mini-feature", "task_type": "feature",
             "model": "fast-but-wrong", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": "h2", "runner_git_sha": "abc", "trial": 1, "pass": False,
             "grade_output": "FAIL", "tokens_per_second": 50.0},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        correct_rank = next(i for i, l in enumerate(section.splitlines()) if "correct-but-slow" in l)
        wrong_rank = next(i for i, l in enumerate(section.splitlines()) if "fast-but-wrong" in l)
        self.assertLess(correct_rank, wrong_rank, "the correct-but-slow model must rank first")

    def test_group_with_zero_scoreable_axes_is_omitted_not_zero_scored(self):
        # A harness-error-only group has no pass/fail signal at all on any
        # axis (harness_error rows are excluded from `scored` upstream) —
        # it must be left out of the ranking, not shown with a misleading
        # score of 0.
        self._write_log([
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "all-harness-errors", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": False,
             "harness_error": True, "grade_output": "HARNESS ERROR"},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        self.assertNotIn("all-harness-errors", section)


class BlockedConfigsSectionTests(unittest.TestCase):
    """A config marked `orchestration.viable: blocked` (a model+inference-
    engine combination ruled out as non-viable, e.g. Qwen3.8-27B after a
    live pilot showed it too slow to ever finish a task) must be surfaced
    in the leaderboard, and — since such a config can be blocked before it
    was ever run — this must come from scanning configs/**/*.yaml
    directly, not from log.jsonl rows."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _write_config(self, rel_path, content):
        p = self.repo / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def _blocked_section(self, text):
        return text[text.index("## Blocked configs"):]

    def test_blocked_config_with_no_log_rows_still_appears(self):
        # Some other, unrelated model's row must exist so main() doesn't
        # take the "no runs yet" early-return path — the blocked config
        # itself has NO row of its own, which is the whole point of the test.
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "unrelated-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        self._write_config(
            "configs/NeverRun-Model/gguf.yaml",
            "model: some-org/NeverRun-Model-GGUF\n"
            "inference_engine: llama.cpp\n"
            "orchestration:\n"
            "  viable: blocked\n"
            "  blocked_reason: \"Marked non-viable before this config was ever run.\"\n",
        )
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._blocked_section(text)
        self.assertIn("NeverRun-Model", section)
        self.assertIn("Marked non-viable before this config was ever run.", section)

    def test_non_blocked_config_not_listed(self):
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "unrelated-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        self._write_config(
            "configs/StillFine-Model/mlx.yaml",
            "model: some-org/StillFine-Model\ninference_engine: vllm-mlx\norchestration:\n  viable: full\n",
        )
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._blocked_section(text)
        self.assertNotIn("StillFine-Model", section)
        self.assertIn("None currently blocked.", section)


class SpeedGatedConfigsSectionTests(unittest.TestCase):
    """run_bench.py's speed gate (probes hermes_ops-selection, stops before
    the rest of hermes_ops + coding if it's under
    bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND twice in a row) writes to
    results/speed_gate.jsonl, a dedicated log kept separate from log.jsonl.
    build_leaderboard.py must render it as its own section, and must not
    choke when the file doesn't exist at all (the common case, before any
    config has ever tripped this gate)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def _speed_gate_section(self, text):
        return text[text.index("## Speed-gated configs"):]

    def test_missing_speed_gate_log_renders_none_gated(self):
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "unrelated-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        self.assertIn("None gated on speed so far.", self._speed_gate_section(text))

    def test_speed_gated_entry_is_rendered_with_its_measurements(self):
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "unrelated-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        (self.repo / "results" / "speed_gate.jsonl").write_text(json.dumps({
            "model": "TooSlow/Model-4bit", "inference_engine": "vllm-mlx",
            "config_path": "configs/TooSlow-Model/mlx.yaml", "config_hash": "abc123",
            "suite": "hermes_ops",
            "measured_tokens_per_second": [0.18, 0.22, 0.31],
            "avg_tokens_per_second": 0.237,
            "threshold_tokens_per_second": 10.0,
            "timestamp": "2026-08-22T12:00:00Z",
        }) + "\n")
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._speed_gate_section(text)
        self.assertIn("TooSlow/Model-4bit", section)
        self.assertIn("0.18, 0.22, 0.31", section)
        self.assertIn("0.24", section)  # avg, rendered to 2 decimals
        self.assertIn("configs/TooSlow-Model/mlx.yaml", section)

    def test_old_speed_gate_entry_with_backend_key_still_shows_its_engine(self):
        # Entries written before the backend->framework rename (2026-08-23)
        # carry "backend" only — must not silently render as blank.
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "unrelated-model", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        (self.repo / "results" / "speed_gate.jsonl").write_text(json.dumps({
            "model": "OldEntry/Model", "backend": "omlx",
            "config_path": "configs/OldEntry-Model/omlx.yaml", "config_hash": "def456",
            "measured_tokens_per_second": [0.01], "avg_tokens_per_second": 0.01,
            "threshold_tokens_per_second": 1.0,
            "timestamp": "2026-08-22T00:00:00Z",
        }) + "\n")
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._speed_gate_section(text)
        row_line = next(l for l in section.splitlines() if "OldEntry/Model" in l)
        self.assertIn("| omlx |", row_line)


class InferenceEngineFieldHistoryBackcompatTests(unittest.TestCase):
    """The engine-identity field went through two renames in quick
    succession on 2026-08-23: `backend` (mlx/gguf/omlx/api) -> `framework`
    (still too coarse a name for what it actually meant) -> `inference_engine`
    (llama.cpp/vllm-mlx/omlx/..., the final name). results/log.jsonl is an
    append-only historical record — rows logged before either rename are
    never rewritten in place, so a real row can carry any of the three
    field names. _row_inference_engine() must still group/render all three
    correctly rather than treating older rows as missing an identity
    column."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_log(self, rows):
        (self.repo / "results" / "log.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n"
        )

    def test_old_backend_only_row_still_renders_its_identity(self):
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "legacy-model", "backend": "mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| legacy-model |"))
        self.assertIn("| mlx |", row_line)

    def test_old_middle_tier_framework_only_row_still_renders_its_identity(self):
        # Rows logged between the two renames (2026-08-23, same day) carry
        # "framework" only — the middle tier of the fallback chain.
        self._write_log([{
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "mid-rename-model", "framework": "llama.cpp", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        row_line = next(l for l in text.splitlines() if l.startswith("| mid-rename-model |"))
        self.assertIn("| llama.cpp |", row_line)

    def test_rows_from_all_three_field_name_generations_do_not_silently_merge(self):
        # A backend-only row, a framework-only row, and an inference_engine
        # row for the same model are three DIFFERENT strings in the
        # grouping key even though two of them describe the same real
        # engine — this is an accepted, documented gap (not silently
        # averaging differently-labeled data), not something this fix
        # papers over.
        self._write_log([
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "m", "backend": "mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS"},
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "m", "framework": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS"},
            {"suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
             "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
             "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
             "grade_output": "PASS"},
        ])
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        main_table = text[:text.index("## Best overall")]
        row_lines = [l for l in main_table.splitlines() if l.startswith("| m |")]
        self.assertEqual(len(row_lines), 2)  # "mlx" and "vllm-mlx" — 2 groups, not 3 or 1
        joined = "".join(row_lines)
        self.assertIn("| mlx |", joined)
        self.assertIn("| vllm-mlx |", joined)


class MarkdownTableColumnCountTests(unittest.TestCase):
    """Confirmed live 2026-08-23: the main table's header had 20 columns
    but its separator row had 21 `|---|` cells — a leftover from trimming
    a redundant "framework" column during the backend->inference_engine
    rename (the header string was updated, the separator string wasn't).
    GitHub renders this as a visibly broken table. Generic guard: every
    `| header | ... |` line immediately followed by an all-dashes
    `|---|...|` line must have the SAME number of `|` characters, for
    every table this file generates, not just the one that broke."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = bl.REPO
        bl.REPO = self.repo

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_table_header_matches_its_separator_row_width(self):
        (self.repo / "results" / "log.jsonl").write_text(json.dumps({
            "suite": "hermes_ops", "task_id": "hermes_ops-selection", "task_type": "tool-selection",
            "model": "m", "inference_engine": "vllm-mlx", "quant": None, "config_path": None,
            "config_hash": None, "runner_git_sha": "abc", "trial": 1, "pass": True,
            "grade_output": "PASS",
        }) + "\n")
        bl.main()
        lines = (self.repo / "results" / "LEADERBOARD.md").read_text().splitlines()
        mismatches = []
        for i in range(1, len(lines)):
            sep = lines[i].strip()
            if not sep or set(sep) - set("|-"):
                continue  # not an all-dashes separator line
            header = lines[i - 1]
            if header.count("|") != sep.count("|"):
                mismatches.append((i + 1, header.count("|"), sep.count("|"), header[:60]))
        self.assertEqual(mismatches, [], f"header/separator column-count mismatches: {mismatches}")


if __name__ == "__main__":
    unittest.main()

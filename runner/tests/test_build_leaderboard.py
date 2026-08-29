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
        # sanity gate and reasoning-effort columns added since this
        # assertion was first written — match on the surrounding cells
        # rather than an exact full-row string, so an unrelated column
        # addition doesn't make this brittle.
        row_line = next(l for l in text.splitlines() if l.startswith("| test-model |"))
        cells = [c.strip() for c in row_line.split("|")]
        self.assertEqual(cells[10], "2")     # tasks
        self.assertEqual(cells[11], "100%")  # pass rate

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
        self.assertEqual(cells[12], "0")  # "slow passes" column


class CompositeRankingTests(unittest.TestCase):
    """Round 3 (2026-08-27, benchmark v2) of the "Best overall" ranking,
    replacing round 2's plain "primary sort: coding_pass_rate, tie-break:
    speed" (gate-then-rank, 2026-08-26) with a weighted composite score.
    User request: the score should reflect not just pass/fail but speed,
    time taken, and turns used per task — "Pass + speed should get most
    weight, then time, then turns." This coincided with bumping the
    coding-suite timeouts (tasks/kiem_mini.yaml etc., 1500s -> 3000s) so a
    slow-but-eventually-correct model can finish instead of being hard-
    killed — the composite score is what lets that model still compete
    (scoring lower on speed/time) instead of needing an outright
    disqualification to keep the leaderboard meaningful.

    Unchanged from round 2:
    1. ELIGIBILITY — a group needs at least one row on ALL THREE axes
       (sanity, hermes_ops, coding) to represent a genuinely completed run.
    2. USEFULNESS GATE (hard pass/fail tier, not a weighted input):
       hermes_ops_pass_rate >= 0.5. Every gate-passing group ranks above
       every gate-failing group, regardless of the score below.
    3. Dedup to the most-evidenced fragment per (model, engine, quant).

    New in round 3 — among gate-passers, ranked by CODING_SCORE_WEIGHTS-
    weighted composite of: coding_pass_rate (0.45), speed normalized
    against the fastest gate-passer (0.25), avg wall_seconds per coding
    task inverse-normalized against the fastest-completing gate-passer
    (0.20), and avg turns per coding task inverse-normalized against the
    fewest-turns gate-passer (0.10). pass=0.35/speed=0.35 (equal) was
    tried first, but a real regenerated-leaderboard check found a
    0%-coding model outranking an 82%-coding model on speed alone at
    those weights — user's call was to give pass MORE weight than speed
    (0.45 vs 0.25) instead, so pass can no longer be fully cancelled out
    by raw speed. A large enough speed gap can still flip a modest
    pass-rate gap (not a bug — see
    test_large_speed_advantage_can_outrank_modest_pass_rate_advantage),
    just a bigger gap is needed than when the two were tied.
    """

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

    def _complete_rows(self, model, hermes_ops_passes, coding_passes, tps,
                        config_hash="h", runner_sha="abc", quant=None,
                        inference_engine="vllm-mlx", wall_seconds=None, turns=None,
                        timestamp=None):
        """Builds a full (sanity + hermes_ops + coding) row set for one
        group — one sanity-basic PASS, one hermes_ops row per bool in
        `hermes_ops_passes`, one kiem_mini row per bool in `coding_passes`,
        all carrying the same tokens_per_second so avg tok/s == tps.
        wall_seconds/turns, when given, are applied uniformly to every
        coding row (sufficient for these tests, which only need group-
        level averages to differ, not per-task variation) — omitted
        entirely (not just None) when not given, matching how a real log
        row without hermes_turns/wall_seconds actually looks. `timestamp`,
        when given, is stamped on every row (default omitted, like a real
        row always has a timestamp but most dedup tests don't care which)."""
        rows = [{
            "suite": "sanity", "task_id": "sanity-basic", "task_type": "sanity",
            "model": model, "inference_engine": inference_engine, "quant": quant,
            "config_path": None, "config_hash": config_hash, "runner_git_sha": runner_sha,
            "trial": 1, "pass": True, "grade_output": "PASS", "tokens_per_second": tps,
        }]
        for i, ok in enumerate(hermes_ops_passes):
            rows.append({
                "suite": "hermes_ops", "task_id": f"hermes_ops-task{i}", "task_type": "tool-selection",
                "model": model, "inference_engine": inference_engine, "quant": quant,
                "config_path": None, "config_hash": config_hash, "runner_git_sha": runner_sha,
                "trial": 1, "pass": ok, "grade_output": "PASS" if ok else "FAIL",
                "tokens_per_second": tps,
            })
        for i, ok in enumerate(coding_passes):
            row = {
                "suite": "kiem_mini", "task_id": f"kiem_mini-task{i}", "task_type": "feature",
                "model": model, "inference_engine": inference_engine, "quant": quant,
                "config_path": None, "config_hash": config_hash, "runner_git_sha": runner_sha,
                "trial": 1, "pass": ok, "grade_output": "PASS" if ok else "FAIL",
                "tokens_per_second": tps,
            }
            if wall_seconds is not None:
                row["wall_seconds"] = wall_seconds
            if turns is not None:
                row["hermes_turns"] = turns
            rows.append(row)
        if timestamp is not None:
            for row in rows:
                row["timestamp"] = timestamp
        return rows

    def test_group_missing_any_axis_is_excluded_entirely(self):
        cases = {
            "no-sanity": [r for r in self._complete_rows("no-sanity", [True], [True], 10.0)
                          if r["suite"] != "sanity"],
            "no-hermes-ops": self._complete_rows("no-hermes-ops", [], [True], 10.0),
            "no-coding": self._complete_rows("no-coding", [True], [], 10.0),
        }
        for label, rows in cases.items():
            with self.subTest(label=label):
                self.repo_log_rows = rows
                self._write_log(rows)
                bl.main()
                text = (self.repo / "results" / "LEADERBOARD.md").read_text()
                section = self._best_overall_section(text)
                self.assertNotIn(label, section)

    def test_gate_failing_group_ranks_below_all_gate_passing_groups(self):
        # A model that fails the usefulness gate (hermes_ops < 50%) must
        # rank below EVERY gate-passing group, even one with weaker coding
        # and slower speed — the gate is a hard tier boundary, not a
        # weighted input that a great composite score could outweigh.
        rows = (
            self._complete_rows("gate-fails", hermes_ops_passes=[False, False, True],
                                 coding_passes=[True, True], tps=100.0, config_hash="h1")
            + self._complete_rows("gate-passes-weaker", hermes_ops_passes=[True, False],
                                   coding_passes=[False], tps=1.0, config_hash="h2")
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        fail_rank = next(i for i, l in enumerate(section.splitlines()) if "gate-fails" in l)
        pass_rank = next(i for i, l in enumerate(section.splitlines()) if "gate-passes-weaker" in l)
        self.assertLess(pass_rank, fail_rank, "the gate-passing group must rank above the gate-failing one")
        row_line = next(l for l in section.splitlines() if "gate-fails" in l)
        self.assertIn("FAIL", row_line)

    def test_higher_coding_pass_rate_wins_when_speed_is_comparable(self):
        # With speed (and time/turns) held equal, pass rate alone must
        # still decide the ranking — the composite score doesn't discard
        # pass rate, it just no longer gives it UNCONDITIONAL priority
        # over speed the way round 2's plain sort did.
        rows = (
            self._complete_rows("correct", hermes_ops_passes=[True], coding_passes=[True, True],
                                 tps=20.0, config_hash="h1")
            + self._complete_rows("wrong", hermes_ops_passes=[True], coding_passes=[True, False],
                                   tps=20.0, config_hash="h2")
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        correct_rank = next(i for i, l in enumerate(section.splitlines()) if "| correct " in l)
        wrong_rank = next(i for i, l in enumerate(section.splitlines()) if "| wrong " in l)
        self.assertLess(correct_rank, wrong_rank, "with equal speed, the higher-coding-pass-rate model must rank first")

    def test_large_speed_advantage_can_outrank_modest_pass_rate_advantage(self):
        # Deliberate, documented consequence of pass+speed both carrying
        # real weight: a LARGE ENOUGH speed gap can still flip a modest
        # pass-rate gap, unlike round 2 where coding_pass_rate was an
        # unconditional primary sort — just a bigger gap is needed now
        # that pass (0.45) outweighs speed (0.25) rather than tying it.
        # 25x speed gap vs a 2/2-vs-1/2 pass-rate gap flips it under the
        # current weights (a 10x gap, tried first, landed on an exact tie
        # at these weights — 0.475 vs 0.475 — so this uses a clearly
        # decisive gap instead of one that happens to cancel out).
        rows = (
            self._complete_rows("correct-but-slow", hermes_ops_passes=[True], coding_passes=[True, True],
                                 tps=2.0, config_hash="h1")
            + self._complete_rows("fast-but-wrong", hermes_ops_passes=[True], coding_passes=[True, False],
                                   tps=50.0, config_hash="h2")
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        correct_rank = next(i for i, l in enumerate(section.splitlines()) if "correct-but-slow" in l)
        wrong_rank = next(i for i, l in enumerate(section.splitlines()) if "fast-but-wrong" in l)
        self.assertLess(wrong_rank, correct_rank, "a large enough speed advantage should outrank a modest pass-rate edge")

    def test_equal_coding_pass_rate_broken_by_higher_speed(self):
        rows = (
            self._complete_rows("equal-coding-fast", hermes_ops_passes=[True], coding_passes=[True, False],
                                 tps=80.0, config_hash="h1")
            + self._complete_rows("equal-coding-slow", hermes_ops_passes=[True], coding_passes=[True, False],
                                   tps=8.0, config_hash="h2")
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        fast_rank = next(i for i, l in enumerate(section.splitlines()) if "equal-coding-fast" in l)
        slow_rank = next(i for i, l in enumerate(section.splitlines()) if "equal-coding-slow" in l)
        self.assertLess(fast_rank, slow_rank, "with tied coding pass rate, the faster model must rank first")

    def test_shorter_time_taken_scores_higher_all_else_equal(self):
        # Same pass rate and speed, only avg wall_seconds per coding task
        # differs — the faster-to-finish group must score higher via the
        # time axis (weight 0.20).
        rows = (
            self._complete_rows("quick-finisher", hermes_ops_passes=[True], coding_passes=[True, True],
                                 tps=20.0, config_hash="h1", wall_seconds=100.0)
            + self._complete_rows("slow-finisher", hermes_ops_passes=[True], coding_passes=[True, True],
                                   tps=20.0, config_hash="h2", wall_seconds=2000.0)
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        quick_rank = next(i for i, l in enumerate(section.splitlines()) if "quick-finisher" in l)
        slow_rank = next(i for i, l in enumerate(section.splitlines()) if "slow-finisher" in l)
        self.assertLess(quick_rank, slow_rank, "less time taken per task must score higher, all else equal")

    def test_fewer_turns_scores_higher_all_else_equal(self):
        # Same pass rate, speed, and time — only avg turns per coding task
        # differs — the fewer-turns group must score higher via the turns
        # axis (weight 0.10). A genuinely smart model solving a task in
        # fewer turns is exactly what this axis is meant to reward.
        rows = (
            self._complete_rows("few-turns", hermes_ops_passes=[True], coding_passes=[True, True],
                                 tps=20.0, config_hash="h1", wall_seconds=500.0, turns=5)
            + self._complete_rows("many-turns", hermes_ops_passes=[True], coding_passes=[True, True],
                                   tps=20.0, config_hash="h2", wall_seconds=500.0, turns=35)
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        few_rank = next(i for i, l in enumerate(section.splitlines()) if "few-turns" in l)
        many_rank = next(i for i, l in enumerate(section.splitlines()) if "many-turns" in l)
        self.assertLess(few_rank, many_rank, "fewer turns per task must score higher, all else equal")

    def test_timed_out_row_with_no_turns_recorded_is_not_rewarded_for_it(self):
        # A coding row killed by the wall-clock timeout has hermes_turns =
        # None (hermes never got to export session stats) -- this must NOT
        # read as "0 turns" (which would perversely score BETTER than a
        # model that actually completed and got a real, higher turn
        # count). It should be substituted with
        # CODING_TURNS_CEILING_FOR_TIMEOUT (an assumed worst case), so a
        # timed-out row never wins the turns axis over a real completion.
        rows = (
            self._complete_rows("timed-out", hermes_ops_passes=[True], coding_passes=[False],
                                 tps=20.0, config_hash="h1", wall_seconds=3000.0)  # no turns= given -> None in the row
            + self._complete_rows("finished-many-turns", hermes_ops_passes=[True], coding_passes=[True],
                                   tps=20.0, config_hash="h2", wall_seconds=500.0, turns=30)
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        # The timed-out group's displayed avg turns must reflect the
        # ceiling substitution (40.0), not blank/0.
        timed_out_line = next(l for l in section.splitlines() if "timed-out" in l)
        self.assertIn(f"{bl.CODING_TURNS_CEILING_FOR_TIMEOUT:.1f}", timed_out_line)
        # And it must still lose overall (it also failed the coding task
        # and took much longer) -- the point is the turns axis specifically
        # doesn't give it an undeserved boost.
        timed_out_rank = next(i for i, l in enumerate(section.splitlines()) if "timed-out" in l)
        finished_rank = next(i for i, l in enumerate(section.splitlines()) if "finished-many-turns" in l)
        self.assertLess(finished_rank, timed_out_rank)

    def test_dedups_to_the_most_evidenced_fragment_per_model_engine_quant(self):
        # A model tested twice under different config_hash/runner_sha (a
        # real config edit, or a harness-version change) used to show BOTH
        # fragments as independently-ranked rows — an early 1-task
        # fragment could then outrank that same model's own later, complete
        # sweep. Only the more-evidenced fragment should appear.
        rows = self._complete_rows(
            "m", hermes_ops_passes=[True], coding_passes=[True], tps=50.0,
            config_hash="early", runner_sha="sha1",
        ) + self._complete_rows(
            "m", hermes_ops_passes=[True, True], coding_passes=[True, False, True], tps=40.0,
            config_hash="later", runner_sha="sha2",
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        matches = [l for l in section.splitlines() if l.startswith("| ") and " m " in l]
        self.assertEqual(len(matches), 1, f"expected exactly one row for 'm', got: {matches}")
        self.assertIn("later", matches[0])  # the more-evidenced fragment, not the 1-task one

    def test_evidence_tie_is_broken_by_recency_not_iteration_order(self):
        # Real incident, 2026-08-28 (benchmark v2 Phase D wrap-up):
        # Qwen3-Coder-30B-A3B's genuine full rerun (19 tasks, 89% pass)
        # lost a tie to an OLDER partial run under the same config_hash
        # that happened to also have exactly 19 tasks (74% pass) but was
        # logged earlier — the old `evidence > current` comparison never
        # replaces on an exact tie, so whichever fragment the dict
        # iteration reached first won, regardless of which one was the
        # real, current result. Deliberately construct an exact evidence
        # tie (2 hermes_ops + 3 coding = 5 both sides) where the OLDER
        # fragment is iterated first (earlier config_hash/runner_sha
        # alphabetically, so dict insertion order would favor it) to
        # prove recency — not insertion order — now wins.
        rows = self._complete_rows(
            "m", hermes_ops_passes=[True, True], coding_passes=[True, True, False], tps=20.0,
            config_hash="h", runner_sha="a-older", timestamp="2026-08-25T00:00:00Z",
        ) + self._complete_rows(
            "m", hermes_ops_passes=[True, True], coding_passes=[True, True, True], tps=20.0,
            config_hash="h", runner_sha="z-newer", timestamp="2026-08-28T00:00:00Z",
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        matches = [l for l in section.splitlines() if l.startswith("| ") and " m " in l]
        self.assertEqual(len(matches), 1, f"expected exactly one row for 'm', got: {matches}")
        self.assertIn("100% (3)", matches[0])  # the newer, fully-passing fragment

    def test_complete_but_thin_fragment_not_shadowed_by_incomplete_rich_one(self):
        # Real incident (openai/gpt-5.6-luna via OpenRouter, found
        # 2026-08-29): dedup-to-most-evidenced-fragment ran BEFORE the
        # eligibility check, using an evidence metric (n_coding +
        # n_hermes_ops) that ignores n_sanity entirely. A harness-code
        # commit landed between when this model's sanity check ran and
        # when its full 11-task coding rerun happened, so the RICH
        # fragment (11 coding + 6 hermes_ops, real data) has zero sanity
        # rows under its own runner_git_sha, while a separate, THINNER
        # fragment (1 coding + 8 hermes_ops) under a different
        # runner_git_sha DOES have sanity and is genuinely complete on
        # all three axes. The old code deduped to the richer fragment
        # first (by evidence count alone), then eligibility-checked ONLY
        # that winner, found it missing sanity, and discarded it --
        # silently deleting the model from "Best overall" entirely even
        # though a genuinely complete fragment existed. Eligibility must
        # be checked BEFORE dedup, not after, so a complete-but-thin
        # fragment isn't shadowed out of existence by an
        # incomplete-but-rich one.
        rows = (
            self._complete_rows(
                "m", hermes_ops_passes=[True] * 8, coding_passes=[True],
                tps=35.0, config_hash="h", runner_sha="thin-but-complete",
                timestamp="2026-08-24T21:51:47Z",
            )
            + [
                r for r in self._complete_rows(
                    "m", hermes_ops_passes=[True] * 6, coding_passes=[True] * 10 + [False],
                    tps=25.0, config_hash="h", runner_sha="rich-but-incomplete",
                    timestamp="2026-08-26T19:37:15Z",
                )
                if r["suite"] != "sanity"
            ]
        )
        self._write_log(rows)
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        section = self._best_overall_section(text)
        matches = [l for l in section.splitlines() if l.startswith("| ") and " m " in l]
        self.assertEqual(
            len(matches), 1,
            f"expected 'm' to still appear (a complete fragment exists), got: {matches}",
        )


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

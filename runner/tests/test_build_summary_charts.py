"""Regression tests for runner/build_summary_charts.py.

Run: uv run --locked python -m unittest discover -s runner/tests -v

These tests never write to the repo's real results/ directory — every renderer
targets a throwaway temp dir, and the integration test points build() at a temp
log. They reuse a small synthetic fixture, so build_leaderboard's FULL_*_TASKS
eligibility sizes are patched down to 1 (same approach+reason as
test_build_leaderboard.py). Chart tests that touch real matplotlib rendering
are wrapped in skipUnless(matplotlib_ok) so the suite still passes where
matplotlib is unavailable.
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_summary_charts as sbc
import build_leaderboard as bl

# rank_groups()'s eligibility checks against the real FULL_*_TASKS sizes (8/15);
# our fixtures are tiny, so patch them down to 1 module-wide exactly like
# test_build_leaderboard.py does. _is_v2_or_later() shells out to real git and
# can't resolve fabricated shas, so default it to True.
_v2_patch = mock.patch("build_leaderboard._is_v2_or_later", return_value=True)
_hermes_size_patch = mock.patch("build_leaderboard.FULL_HERMES_OPS_TASKS", 1)
_coding_size_patch = mock.patch("build_leaderboard.FULL_CODING_TASKS", 1)


def setUpModule():
    _v2_patch.start()
    _hermes_size_patch.start()
    _coding_size_patch.start()


def tearDownModule():
    _v2_patch.stop()
    _hermes_size_patch.stop()
    _coding_size_patch.stop()


def _matplotlib_ok():
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:  # pragma: no cover - environment check
        return False


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = Path(self.tmp) / "out"
        self._orig_repo = bl.REPO
        bl.REPO = Path(self.tmp)

    def tearDown(self):
        bl.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- fixture helpers ----------------------------------------------------
    def _row(self, model, engine, suite, pass_=True, ts="2026-08-25T10:00:00Z",
             wall=5.0, tps=50.0, harness_error=False, quant=None,
             config_hash="aaa111", runner_sha="aaa111111111",
             grade_output="PASS", task_id=None, **kw):
        row = {
            "suite": suite,
            "task_id": task_id or f"{suite}-x",
            "task_type": "prompt-response",
            "model": model,
            "inference_engine": engine,
            "quant": quant,
            "config_path": None,
            "config_hash": config_hash,
            "runner_git_sha": runner_sha,
            "trial": 1,
            "pass": pass_,
            "grade_output": grade_output,
            "tokens_per_second": tps,
            "wall_seconds": wall,
            "timestamp": ts,
            "harness_error": harness_error,
        }
        row.update(kw)
        return row

    def _write_log(self, rows, name="log.jsonl", subdir=None):
        base = Path(self.tmp)
        if subdir:
            base = base / subdir
        base.mkdir(parents=True, exist_ok=True)
        lp = base / name
        lp.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return lp


def _group_stats_for(rows):
    """Convenience: group rows the leaderboard way and compute stats."""
    groups = sbc.group_rows(rows)
    return sbc.compute_group_stats(groups)


class SelectionFilteringAndPairingTests(_Base):
    """Selection resolution is by family + engine (model strings differ between
    Mei and GGUF provenance) and engine-delta pairs by family."""

    def _gemma_group(self, engine, model, quant=None, config_hash="g1"):
        rows = []
        for i, suite in enumerate(["sanity", "hermes_ops", "kiem_mini"]):
            ts = (datetime(2026, 8, 25, 10, 0, 0) + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append(self._row(model, engine, suite, pass_=True, ts=ts,
                                  wall=10.0, config_hash=config_hash))
        return rows

    def test_resolve_selection_matches_by_model_contains_case_insensitive(self):
        gs = _group_stats_for(
            self._gemma_group("mei", "mlx-community/gemma-4-26b-a4b-it-4bit") +
            self._gemma_group("llama.cpp", "mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact", config_hash="g2")
        )
        records = [
            {"family": "gemma-4-26B", "engine": "mei", "model_contains": "gemma-4-26b-a4b-it-4bit"},
            {"family": "gemma-4-26B", "engine": "llama.cpp", "model_contains": "gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact"},
        ]
        eligible = {x["key"] for x in gs}
        selected = sbc.resolve_selection(records, gs, eligible)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["family"], "gemma-4-26B")
        self.assertEqual(selected[0]["engine"], "mei")
        self.assertTrue(selected[0]["gs"]["key"][0].startswith("mlx-community"))
        self.assertEqual(selected[1]["engine"], "llama.cpp")
        self.assertIn("mudler/gemma-4-26B", selected[1]["gs"]["key"][0])

    def test_resolve_selection_unmatched_record_flag_partial(self):
        gs = _group_stats_for(self._gemma_group("mei", "mlx-community/gemma-4-26b-a4b-it-4bit"))
        records = [{"family": "qwen3.8", "engine": "mei", "model_contains": "no-such-model"}]
        selected = sbc.resolve_selection(records, gs, set())
        self.assertEqual(len(selected), 1)
        self.assertIsNone(selected[0]["gs"])
        self.assertTrue(selected[0]["partial"])

    def test_engine_delta_pairs_only_families_with_both_engines(self):
        records = [
            {"family": "gemma-4-26B", "engine": "mei", "model_contains": "gemma-4-26b-a4b-it-4bit"},
            {"family": "gemma-4-26B", "engine": "llama.cpp", "model_contains": "gemma-4-26B-A4B"},
            {"family": "ornith-1.5-35B", "engine": "mei", "model_contains": "Ornith-1.5-35B-A3B-MLX-4bit"},
        ]
        gs = _group_stats_for(
            self._gemma_group("mei", "mlx-community/gemma-4-26b-a4b-it-4bit") +
            self._gemma_group("llama.cpp", "mudler/gemma-4-26B-A4B-it-APEX", config_hash="g2") +
            self._gemma_group("mei", "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit", config_hash="g3")
        )
        eligible = {x["key"] for x in gs}
        selected = sbc.resolve_selection(records, gs, eligible)
        pairs, skipped = sbc.compute_engine_deltas(selected)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["family"], "gemma-4-26B")
        self.assertIn("pass_delta", pairs[0])
        # The ornith family had only mei -> skipped cleanly, not charted.
        self.assertEqual(len(skipped), 1)
        self.assertIn("no llama.cpp", skipped[0]["reason"])

    def test_engine_delta_includes_score_delta_when_available(self):
        gs = _group_stats_for(
            self._gemma_group("mei", "mlx-community/gemma-4-26b-a4b-it-4bit") +
            self._gemma_group("llama.cpp", "mudler/gemma-4-26B-A4B-it-APEX", config_hash="g2")
        )
        records = [
            {"family": "g", "engine": "mei", "model_contains": "gemma"},
            {"family": "g", "engine": "llama.cpp", "model_contains": "gemma"},
        ]
        selected = sbc.resolve_selection(records, gs, {x["key"] for x in gs})
        pairs, _ = sbc.compute_engine_deltas(selected, score_by_key={g["key"]: 0.4 for g in gs})
        self.assertIsNotNone(pairs[0]["score_delta"])


class QualityRuntimeUsesTotalRuntimeTests(_Base):
    """quality_vs_runtime uses the RECOVERED total_runtime_seconds, not a
    per-task wall average; groups without a recoverable runtime are skipped."""

    def _timed_group(self, model, engine, n=3, start_hour=10, every_min=1):
        rows = []
        base = datetime(2026, 8, 25, start_hour, 0, 0)
        for i in range(n):
            suite = ["sanity", "hermes_ops", "kiem_mini"][i]
            ts = (base + timedelta(minutes=i * every_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append(self._row(model, engine, suite, pass_=True, ts=ts, wall=120.0))
        return rows

    def test_recovered_total_runtime_is_used(self):
        # Two 3-row groups, same per-task wall (120s) but very different total
        # elapsed span (2-min apart vs 5-min apart) -> recovered runtime differs.
        g1 = self._timed_group("m/alpha", "mei", n=3, start_hour=10, every_min=1)
        g2 = self._timed_group("m/beta", "llama.cpp", n=3, start_hour=11, every_min=5)
        gs = _group_stats_for(g1 + g2)
        gs_by_model = {x["key"][0]: x for x in gs}
        alpha = gs_by_model["m/alpha"]
        beta = gs_by_model["m/beta"]
        # total_runtime_seconds spans first->last task (plus first task's wall),
        # so it is LARGER than a single wall and reflects the inter-task gap.
        self.assertGreater(alpha["total_runtime_seconds"], 120.0)
        self.assertGreater(beta["total_runtime_seconds"], alpha["total_runtime_seconds"])
        self.assertEqual(sbc.total_runtime_hours(alpha), alpha["total_runtime_seconds"] / 3600.0)

    @unittest.skipUnless(_matplotlib_ok(), "matplotlib not available")
    def test_quality_chart_skips_group_without_recoverable_runtime(self):
        # A group with no timestamps -> total_runtime_seconds None -> dropped.
        no_ts = self._row("m/lonely", "mei", "hermes_ops", pass_=True, timestamp=None, wall_seconds=5.0)
        with_ts = self._row("m/ok", "mei", "hermes_ops", pass_=True, ts="2026-08-25T10:00:00Z", wall_seconds=5.0)
        rows = [no_ts, with_ts,
                self._row("m/ok", "mei", "kiem_mini", pass_=True, ts="2026-08-25T10:01:00Z", wall_seconds=5.0)]
        gs = _group_stats_for(rows)
        only_good = [g for g in gs if g["total_runtime_seconds"] is not None]
        self.assertEqual(len(only_good), 1)

    def test_none_runtime_group_is_not_usable_for_comparison(self):
        gs = [{
            "key": ("m/x", "mei", None, "h", "s"), "total_runtime_seconds": None,
            "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 1, "n_coding_pass": 1,
        }, {
            "key": ("m/y", "mei", None, "h", "s"), "total_runtime_seconds": 7200.0,
            "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 1, "n_coding_pass": 1,
        }]
        # Only ONE group has a recoverable runtime -> the chart needs >=2 usable
        # points, so it must skip (None returned). This proves the None-runtime
        # group is excluded from the usable set rather than counted/comparison.
        self.assertIsNone(sbc.render_quality_vs_runtime(gs, self.out))

    def test_quality_chart_skips_when_under_two_usable_points(self):
        gs = [{
            "key": ("m/x", "mei", None, "h", "s"), "total_runtime_seconds": 3600.0,
            "n_hermes_ops": 1, "n_coding": 0, "n_hermes_ops_pass": 1, "n_coding_pass": 0,
        }]
        self.assertIsNone(sbc.render_quality_vs_runtime(gs, self.out))


class SuiteHeatmapExcludesHarnessErrorTests(_Base):
    def _group_rows(self, model="m/g", engine="mei"):
        rows = [
            self._row(model, engine, "sanity", pass_=True),
            self._row(model, engine, "hermes_ops", pass_=True),
            self._row(model, engine, "hermes_ops", pass_=True),
            # harness_error row must be excluded from the pass-rate denominator
            self._row(model, engine, "hermes_ops", pass_=False, harness_error=True),
            self._row(model, engine, "hermes_ops", pass_=False),
            self._row(model, engine, "kiem_mini", pass_=True),
        ]
        return rows

    def test_matrix_excludes_harness_error_rows(self):
        rows = self._group_rows()
        groups = sbc.group_rows(rows)
        selected = [{"gs": _group_stats_for(rows)[0], "family": "g", "engine": "mei",
                     "eligible": True, "partial": False, "label": "m/g"}]
        matrix, suites = sbc._group_suite_matrix(groups, selected)
        hermes_cell = matrix[0]["row"]["hermes_ops"]
        # 2 pass out of 3 non-error rows = 2/3, NOT 2/4 (harness_error excluded).
        self.assertAlmostEqual(hermes_cell, 100 * 2 / 3, places=6)
        self.assertIn("sanity", suites)
        self.assertIn("kiem_mini", suites)

    def test_matrix_marks_missing_suite_cell(self):
        rows = [self._row("m/g", "mei", "sanity", pass_=True)]
        groups = sbc.group_rows(rows)
        gs = _group_stats_for(rows)[0]
        selected = [{"gs": gs, "family": "g", "engine": "mei", "eligible": True,
                     "partial": False, "label": "m/g"}]
        matrix, suites = sbc._group_suite_matrix(groups, selected)
        self.assertIsNone(matrix[0]["row"]["hearth_full"])  # suite with no rows


class ChartSkipTests(_Base):
    """Chart functions skip cleanly (return None) instead of crashing when data
    is insufficient or failure data has no variation."""

    def test_engine_delta_no_usable_pairs_returns_none(self):
        pairs = [{"family": "f", "pass_delta": None, "runtime_hours": None}]
        self.assertIsNone(sbc.render_engine_delta(pairs, self.out))

    def test_heatmap_empty_matrix_returns_none(self):
        self.assertIsNone(sbc._render_suite_heatmap_matrix([], self.out, ["sanity"]))

    def test_runtime_breakdown_no_data_returns_none(self):
        # A selected group whose rows are absent from rows_by_key has no wall-time
        # data -> no entries -> clean skip, not a crash.
        gs = _group_stats_for([self._row("m/x", "mei", "sanity", pass_=True)])[0]
        selected = [{"gs": gs, "family": "g", "engine": "mei", "eligible": True,
                     "partial": False, "label": "m/x"}]
        self.assertIsNone(sbc.render_runtime_breakdown({}, selected, self.out))

    def test_failure_taxonomy_rejects_all_pass(self):
        rows = [self._row("m/x", "mei", "hermes_ops", pass_=True) for _ in range(5)]
        counts, total = sbc.failure_taxonomy_counts(rows)
        self.assertEqual(total, 0)
        self.assertFalse(sbc.should_render_taxonomy(counts, total))

    def test_failure_taxonomy_rejects_single_homogeneous_category(self):
        # Only harness errors (one category) -> no variation -> skip.
        rows = [self._row("m/x", "mei", "hermes_ops", pass_=False, harness_error=True)
                for _ in range(4)]
        counts, total = sbc.failure_taxonomy_counts(rows)
        self.assertEqual(total, 4)
        self.assertFalse(sbc.should_render_taxonomy(counts, total))

    def test_failure_taxonomy_accepts_varied_failures(self):
        rows = [
            self._row("m/x", "mei", "hermes_ops", pass_=True),
            self._row("m/x", "mei", "hermes_ops", pass_=False,
                      grade_output="FAIL: run errored: exceeded max_turns (40) without a final non-tool-call response"),
            self._row("m/x", "mei", "hermes_ops", pass_=False, harness_error=True),
        ]
        counts, total = sbc.failure_taxonomy_counts(rows)
        self.assertEqual(total, 2)
        self.assertTrue(sbc.should_render_taxonomy(counts, total))

    def test_classify_failure_timeout_and_malformed(self):
        timed = self._row("m", "mei", "hermes_ops", pass_=False,
                          grade_output="FAIL: run errored: stream stalled in phase 'first_progress'")
        malformed = self._row("m", "mei", "hermes_ops", pass_=False,
                              grade_output="FAIL: model called tool(s) never declared in this task's manifest: ['search_filessearch_files']")
        self.assertEqual(sbc.classify_failure(timed), "timeout_stall")
        self.assertEqual(sbc.classify_failure(malformed), "malformed_tool")
        self.assertIsNone(sbc.classify_failure(self._row("m", "mei", "hermes_ops", pass_=True)))


@unittest.skipUnless(_matplotlib_ok(), "matplotlib not available")
class RendererWritesPngTests(_Base):
    """At least one renderer writes a nonempty PNG to a temp dir."""

    def test_quality_renderer_writes_nonempty_png(self):
        gs = [
            {"key": ("m/a", "mei", None, "h", "s"), "total_runtime_seconds": 3600.0,
             "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 1, "n_coding_pass": 1},
            {"key": ("m/b", "llama.cpp", None, "h", "s"), "total_runtime_seconds": 7200.0,
             "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 0, "n_coding_pass": 1},
            {"key": ("m/c", "mei", None, "h", "s"), "total_runtime_seconds": 5400.0,
             "n_hermes_ops": 2, "n_coding": 1, "n_hermes_ops_pass": 2, "n_coding_pass": 1},
        ]
        path = sbc.render_quality_vs_runtime(gs, self.out)
        self.assertIsNotNone(path)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 1000)

    def test_engine_delta_renderer_writes_nonempty_png(self):
        gs_mei = {"key": ("m/x", "mei", None, "h", "s"), "total_runtime_seconds": 3600.0,
                  "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 1, "n_coding_pass": 1}
        gs_ll = {"key": ("m/x", "llama.cpp", None, "h", "s"), "total_runtime_seconds": 7200.0,
                 "n_hermes_ops": 1, "n_coding": 1, "n_hermes_ops_pass": 1, "n_coding_pass": 0}
        pairs = [{"family": "f", "mei_gs": gs_mei, "llama_gs": gs_ll,
                  "mei_engine": "mei", "llama_engine": "llama.cpp",
                  "pass_delta": 0.2, "runtime_hours": -1.0}]
        path = sbc.render_engine_delta(pairs, self.out)
        self.assertIsNotNone(path)
        self.assertGreater(Path(path).stat().st_size, 1000)

    def test_engine_delta_renderer_four_families_with_zero_delta_pair(self):
        # Regression for the layout change: the legend lives at figure level in
        # the reserved title band (fig.legend) and a ZERO pass delta (Mei and
        # llama.cpp points coincide) is annotated ABOVE the point. Visual layout
        # cannot be asserted from source, so this exercises the render path that
        # covers both changes: >1 family horizontally-spaced rows, a coincident
        # zero-delta row (upper-right region the legend previously overlapped),
        # and a non-zero delta row. It must still write a nonempty PNG.
        def _gs(model, engine, pass_=True):
            return {"key": (model, engine, None, "h", "s"),
                    "total_runtime_seconds": 3600.0,
                    "n_hermes_ops": 1, "n_coding": 1,
                    "n_hermes_ops_pass": 1 if pass_ else 0,
                    "n_coding_pass": 1 if pass_ else 1}
        # Zero-delta family: Mei and llama.cpp have IDENTICAL pass rates, so the
        # two markers coincide and the annotate-above path is taken.
        families = ["alpha", "beta", "gamma", "delta"]
        pairs = []
        for i, fam in enumerate(families):
            zero = (i % 2 == 0)
            pass_ = ([True, True] if zero else [True, False])
            pairs.append({
                "family": fam,
                "mei_gs": _gs(f"m/{fam}", "mei", pass_=pass_[0]),
                "llama_gs": _gs(f"m/{fam}", "llama.cpp", pass_=pass_[1]),
                "mei_engine": "mei", "llama_engine": "llama.cpp",
                "pass_delta": 0.0 if zero else 0.5,
                "runtime_hours": -float(i + 1),
                "score_delta": -0.010 if zero else 0.330,
            })
        path = sbc.render_engine_delta(pairs, self.out)
        self.assertIsNotNone(path)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 1000)
        # Documented layout contract lives in render_engine_delta's docstring and
        # this test's comment: legend is figure-level (reserved title band) and
        # zero-delta rows annotate above the coincident point. Pixel layout is
        # not asserted from source; the render path above covers both changes.

    def test_heatmap_renderer_writes_nonempty_png(self):
        matrix = [{"label": "g1", "row": {"sanity": 100.0, "hermes_ops": 66.7, "kiem_mini": None}}]
        path = sbc._render_suite_heatmap_matrix(matrix, self.out, ["sanity", "hermes_ops", "kiem_mini"])
        self.assertIsNotNone(path)
        self.assertGreater(Path(path).stat().st_size, 1000)


class EndToEndIntegrationTests(_Base):
    """build() runs the pipeline from a temp log to temp PNGs and never writes
    to the repo's real results/ directory."""

    def _battery(self):
        models = [
            ("mlx-community/gemma-4-26b-a4b-it-4bit", "mei"),
            ("mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact", "llama.cpp"),
        ]
        rows = []
        for mi, (model, engine) in enumerate(models):
            start = datetime(2026, 8, 25, 10 + mi, 0, 0)
            for task, suite in enumerate(["sanity", "hermes_ops", "kiem_mini"]):
                ts = (start + timedelta(minutes=task)).strftime("%Y-%m-%dT%H:%M:%SZ")
                rows.append(self._row(model, engine, suite, pass_=True, ts=ts, wall_seconds=60.0))
        return rows

    def test_build_writes_pngs_to_output_dir_and_leaves_results_alone(self):
        log = self._write_log(self._battery())
        out = sbc.build(log_path=log, output_dir=self.out)
        # Two groups both write the headline charts.
        self.assertIsNotNone(out["written"]["quality_vs_runtime"])
        # Note: WITHOUT a --selection the two groups default to different family
        # strings (Mei vs GGUF provenance names differ), so engine-delta pairing
        # has no shared family and is correctly skipped here.
        self.assertIsNone(out["written"]["engine_delta"])
        self.assertIn("no llama.cpp", out["engine_delta_skipped"][0]["reason"])
        # Suite heatmap + runtime breakdown written.
        self.assertIsNotNone(out["written"]["suite_heatmap"])
        self.assertIsNotNone(out["written"]["runtime_breakdown"])
        # All-pass battery -> failure taxonomy skipped, not written.
        self.assertEqual(out["written"].get("failure_taxonomy", None), None)
        # The PNGs landed in the temp output dir, not results/.
        for f in ["quality_vs_runtime.png", "suite_heatmap.png", "runtime_breakdown.png"]:
            self.assertTrue((self.out / f).exists(), f)
        # Nothing was written to the repo's results/ directory.
        self.assertFalse((Path(self.tmp) / "LEADERBOARD.md").exists())

    def test_build_selection_yields_engine_delta(self):
        log = self._write_log(self._battery())
        sel = Path(self.tmp) / "sel.json"
        sel.write_text(json.dumps([
            {"family": "gemma-4-26B", "engine": "mei", "model_contains": "gemma-4-26b-a4b-it-4bit"},
            {"family": "gemma-4-26B", "engine": "llama.cpp", "model_contains": "gemma-4-26B-A4B"},
        ]))
        out = sbc.build(log_path=log, output_dir=self.out, selection_path=str(sel))
        # Shared family across both engine legs -> engine-delta now written.
        self.assertIsNotNone(out["written"]["engine_delta"])
        self.assertEqual(out["engine_delta_skipped"], [])
        self.assertTrue((self.out / "engine_delta.png").exists())

    def test_build_accepts_selection_and_filters_models(self):
        log = self._write_log(self._battery())
        sel = Path(self.tmp) / "sel.json"
        sel.write_text(json.dumps([
            {"family": "gemma-4-26B", "engine": "mei", "model_contains": "gemma-4-26b-a4b-it-4bit"},
        ]))
        out = sbc.build(log_path=log, output_dir=self.out, selection_path=str(sel))
        # Only the mei gemma group selected -> no llama.cpp leg for pairing.
        self.assertEqual(out["written"]["engine_delta"], None)
        self.assertIn("no llama.cpp", out["engine_delta_skipped"][0]["reason"])

    def test_build_engine_filter(self):
        log = self._write_log(self._battery())
        out = sbc.build(log_path=log, output_dir=self.out, engines=["mei"])
        # Engine filter keeps only the mei group in the selected set.
        selected_engines = {s["engine"] for s in out["selected"] if s["gs"] is not None}
        self.assertEqual(selected_engines, {"mei"})
        # With only one mei group there are not >=2 comparable points.
        self.assertIsNone(out["written"]["quality_vs_runtime"])


class SelectionSchemaValidationTests(_Base):
    def test_invalid_selection_rejected(self):
        bad = Path(self.tmp) / "bad.json"
        bad.write_text(json.dumps([{"family": "g"}]))  # missing engine + model matcher
        with self.assertRaises(ValueError):
            sbc.load_selection(bad)

    def test_valid_selection_accepted(self):
        good = Path(self.tmp) / "good.json"
        good.write_text(json.dumps([
            {"family": "g", "engine": "mei", "model_contains": "gemma"},
            {"family": "g", "engine": "llama.cpp", "model": "mudler/gemma", "config_hash": "abc"},
        ]))
        recs = sbc.load_selection(good)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[1]["model"], "mudler/gemma")
        self.assertEqual(recs[1]["config_hash"], "abc")

    def test_fragment_selection_schema_accepted(self):
        good = Path(self.tmp) / "good_frag.json"
        good.write_text(json.dumps([{
            "family": "gemma-4-26B", "engine": "mei", "fragments": [
                {"model_contains": "gemma-4-26b", "config_hash": "bc93f3cc55a1", "runner_git_sha": "06f997b70746"},
                {"model_contains": "gemma-4-26b", "config_hash": "bc93f3cc55a1", "runner_git_sha": "a171c0999673"},
            ],
        }]))
        recs = sbc.load_selection(good)
        self.assertEqual(len(recs), 1)
        self.assertEqual(len(recs[0]["fragments"]), 2)
        self.assertEqual(recs[0]["fragments"][1]["runner_git_sha"], "a171c0999673")

    def test_fragment_selection_empty_list_rejected(self):
        bad = Path(self.tmp) / "bad_frag.json"
        bad.write_text(json.dumps([{"family": "g", "engine": "mei", "fragments": []}]))
        with self.assertRaises(ValueError):
            sbc.load_selection(bad)

    def test_fragment_plus_single_matcher_rejected(self):
        bad = Path(self.tmp) / "bad_frag2.json"
        bad.write_text(json.dumps([
            {"family": "g", "engine": "mei", "model_contains": "gemma",
             "fragments": [{"model_contains": "gemma"}]},
        ]))
        with self.assertRaises(ValueError):
            sbc.load_selection(bad)

    def test_fragment_without_matcher_rejected(self):
        bad = Path(self.tmp) / "bad_frag3.json"
        bad.write_text(json.dumps([
            {"family": "g", "engine": "mei", "fragments": [{"config_hash": "abc"}]},
        ]))
        with self.assertRaises(ValueError):
            sbc.load_selection(bad)


class MultiFragmentSelectionTests(_Base):
    """A curated `fragments` list concatenates multiple leaderboard fragments
    into ONE combined group. This is how the final Gemma/Mei leg (a
    sanity+hermes_ops run under one runner sha + the coding suites under a later
    sha, same config = 25 rows) is represented as a single full group rather than
    silently selecting one fragment. The FULL_*_TASKS sizes are patched down
    module-wide (see setUpModule), so combined groups that meet the real full-suite
    counts are considered eligible here just as in production."""

    MODEL = "mlx-community/gemma-4-26b-a4b-it-4bit"
    CONFIG = "bc93f3cc55a1"
    SHA_FRAGA = "06f997b70746"   # sanity + hermes_ops leg
    SHA_FRAGB = "a171c0999673"   # coding leg

    def _fragA_rows(self):
        return self._leg(self.SHA_FRAGA, datetime(2026, 9, 5, 10, 0, 0), 1,
                         ["sanity", "sanity"] + ["hermes_ops"] * 8)

    def _fragB_rows(self):
        suites = ["kiem_mini"] * 5 + ["hearth_mini"] * 3 + ["kipclip_mini"] * 4 + ["hearth_full"] * 3
        return self._leg(self.SHA_FRAGB, datetime(2026, 9, 5, 11, 0, 0), 1, suites)

    def _leg(self, sha, base, step_min, suites):
        rows = []
        for i, suite in enumerate(suites):
            ts = (base + timedelta(minutes=i * step_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append(self._row(self.MODEL, "mei", suite, pass_=True, ts=ts,
                                  wall=60.0, config_hash=self.CONFIG, runner_sha=sha))
        return rows

    def _combined_record(self):
        return {"family": "gemma-4-26B", "engine": "mei", "fragments": [
            {"model_contains": "gemma-4-26b-a4b-it-4bit", "config_hash": self.CONFIG, "runner_git_sha": self.SHA_FRAGA},
            {"model_contains": "gemma-4-26b-a4b-it-4bit", "config_hash": self.CONFIG, "runner_git_sha": self.SHA_FRAGB},
        ]}

    def _resolve(self, rows):
        groups = sbc.group_rows(rows)
        gs = sbc.compute_group_stats(groups)
        eligible = {x["key"] for x in gs}
        return groups, gs, eligible

    def test_combine_two_fragments_into_one_eligible_group(self):
        rows = self._fragA_rows() + self._fragB_rows()
        groups, gs, eligible = self._resolve(rows)
        # Without fragments Gemma/Mei is split into two separate groups (the bug).
        self.assertEqual(len(gs), 2)
        selected = sbc.resolve_selection([self._combined_record()], gs, eligible, groups)
        self.assertEqual(len(selected), 1)
        entry = selected[0]
        self.assertTrue(entry["combined"] and entry["synthetic"])
        self.assertFalse(entry["partial"])
        self.assertTrue(entry["eligible"] and entry["synthetic_eligible"])
        cgs = entry["gs"]
        # 25 rows combined: 2 sanity + 8 hermes_ops + 15 coding.
        self.assertEqual(cgs["n_sanity"], 2)
        self.assertEqual(cgs["n_hermes_ops"], 8)
        self.assertEqual(cgs["n_coding"], 15)
        self.assertIn("curated", entry["label"])
        # Combined rows are surfaced under the synthetic key for later charts.
        self.assertIn(cgs["key"], groups)
        self.assertEqual(len(groups[cgs["key"]]), 25)

    def test_combined_runtime_spans_both_fragments(self):
        fragA = self._leg(self.SHA_FRAGA, datetime(2026, 9, 5, 10, 0, 0), 1, ["sanity", "hermes_ops"])
        fragB = self._leg(self.SHA_FRAGB, datetime(2026, 9, 5, 11, 0, 0), 5, ["kiem_mini", "kiem_mini"])
        _ga, gsA, _ = self._resolve(fragA)
        _gb, gsB, _ = self._resolve(fragB)
        totalA = gsA[0]["total_runtime_seconds"]
        totalB = gsB[0]["total_runtime_seconds"]
        rows = fragA + fragB
        groups, gs, eligible = self._resolve(rows)
        selected = sbc.resolve_selection([self._combined_record()], gs, eligible, groups)
        combined = selected[0]["gs"]["total_runtime_seconds"]
        # Recovered runtime spans first-fragment start → last-fragment end, so it
        # exceeds either fragment's own span and equals the reconstructed estimate.
        self.assertGreater(combined, totalA)
        self.assertGreater(combined, totalB)
        firstA = datetime.fromisoformat(fragA[0]["timestamp"].replace("Z", "+00:00"))
        lastB = datetime.fromisoformat(fragB[-1]["timestamp"].replace("Z", "+00:00"))
        expected = (lastB - (firstA - timedelta(seconds=60))).total_seconds()
        self.assertAlmostEqual(combined, expected, places=3)

    def test_combine_missing_fragment_surfaces_partial(self):
        # Only fragment A is in the log; fragment B's runner sha is absent.
        rows = self._fragA_rows()
        groups, gs, eligible = self._resolve(rows)
        selected = sbc.resolve_selection([self._combined_record()], gs, eligible, groups)
        self.assertEqual(len(selected), 1)
        entry = selected[0]
        self.assertTrue(entry["combined"])
        self.assertTrue(entry["partial"])
        self.assertFalse(entry["eligible"])
        self.assertIsNone(entry["gs"])
        self.assertIn("NO MATCH", entry["label"])
        self.assertIn("missing: runner=", entry["label"].lower())
        # No synthetic combined group is (silently) created.
        self.assertFalse(any(k[4].startswith("curated:") for k in groups))

    @unittest.skipUnless(_matplotlib_ok(), "matplotlib not available")
    def test_build_fragment_selection_writes_combined_group_charts(self):
        llama = [
            self._row("mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact", "llama.cpp", suite,
                      pass_=True,
                      ts=(datetime(2026, 9, 5, 9, 0, 0) + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      wall=60.0, config_hash="g2", runner_sha="ccc111111111")
            for i, suite in enumerate(["sanity", "hermes_ops", "kiem_mini"])
        ]
        rows = self._fragA_rows() + self._fragB_rows() + llama
        log = self._write_log(rows)
        sel = Path(self.tmp) / "sel.json"
        sel.write_text(json.dumps([
            self._combined_record(),
            {"family": "gemma-4-26B", "engine": "llama.cpp", "model_contains": "gemma-4-26B-A4B"},
        ]))
        out = sbc.build(log_path=log, output_dir=self.out, selection_path=str(sel))
        # Combined Gemma/Mei (admitted via synthetic_eligible) + the llama.cpp leg
        # give >=2 comparable points, and a same-family engine-delta pair.
        self.assertIsNotNone(out["written"]["quality_vs_runtime"])
        self.assertIsNotNone(out["written"]["engine_delta"])
        self.assertIsNotNone(out["written"]["suite_heatmap"])
        self.assertIsNotNone(out["written"]["runtime_breakdown"])
        # The combined group is charted with 8+15 task coverage on the full leg.
        combined = [s for s in out["selected"] if s.get("combined")]
        self.assertEqual(len(combined), 1)
        self.assertIsNotNone(combined[0]["gs"])
        self.assertEqual(combined[0]["gs"]["n_hermes_ops"], 8)
        self.assertEqual(combined[0]["gs"]["n_coding"], 15)


class PinnedSingleFragmentHeadlineTests(_Base):
    """An explicitly PINNED single-fragment selection (config_hash/runner_git_sha
    given) whose own stats clear the real full-suite + zero-harness-error bar is
    admitted to the headline charts even when rank_groups deduplicates that
    model/engine to a different (older/richer) fragment — so its key is NOT in the
    vanilla eligible_keys. A genuinely partial pinned record is NOT admitted.
    FULL_*_TASKS is patched to 1 module-wide (see setUpModule)."""

    MODEL = "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit"
    PINNED_CFG = "77d7ab43a6ee"
    PINNED_SHA = "84e884b96aee"
    RICHER_CFG = "22dac305d46e"
    RICHER_SHA = "622d0ad7d2bd"

    def _leg(self, config, sha, suites, start_hour=10):
        rows = []
        base = datetime(2026, 9, 5, start_hour, 0, 0)
        for i, suite in enumerate(suites):
            ts = (base + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append(self._row(self.MODEL, "mei", suite, pass_=True, ts=ts,
                                  wall=60.0, config_hash=config, runner_sha=sha))
        return rows

    def _complete_leg(self, config, sha):
        # n_sanity>=1, n_hermes_ops>=1, n_coding>=1 (FULL_*_TASKS patched to 1).
        return self._leg(config, sha, ["sanity", "hermes_ops", "kiem_mini"])

    def _partial_leg(self, config, sha):
        # No coding suite -> n_coding=0 -> not a complete full-suite leg.
        return self._leg(config, sha, ["sanity", "hermes_ops"])

    def _pinned_record(self):
        return {"family": "Ornith-1.5-35B", "engine": "mei",
                "model_contains": "ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit",
                "config_hash": self.PINNED_CFG, "runner_git_sha": self.PINNED_SHA}

    def _pinned_key(self):
        return (self.MODEL, "mei", None, self.PINNED_CFG, self.PINNED_SHA)

    def _headline_keys(self, out):
        """Mirror build()'s headline filter from its returned selected+ranked."""
        eligible_keys = {g["key"] for (_g, _s, g) in out["ranked"]}
        return {s["gs"]["key"] for s in out["selected"] if s["gs"] is not None and (
            s["gs"]["key"] in eligible_keys
            or s.get("synthetic_eligible") or s.get("pinned_eligible"))}

    def test_pinned_complete_group_outside_eligible_keys_is_admitted(self):
        rows = self._complete_leg(self.PINNED_CFG, self.PINNED_SHA) + \
               self._complete_leg(self.RICHER_CFG, self.RICHER_SHA)
        groups = sbc.group_rows(rows)
        gs = sbc.compute_group_stats(groups)
        # rank_groups dedupes this model/engine to the richer fragment (as in the
        # reported bug), so the pinned complete group's key is NOT eligible.
        eligible = {(self.MODEL, "mei", None, self.RICHER_CFG, self.RICHER_SHA)}
        selected = sbc.resolve_selection([self._pinned_record()], gs, eligible, groups)
        entry = selected[0]
        self.assertIsNotNone(entry["gs"])
        self.assertEqual(entry["gs"]["key"], self._pinned_key())
        self.assertTrue(entry["pinned_eligible"])
        self.assertTrue(entry["eligible"])
        self.assertFalse(entry["partial"])

    def test_pinned_partial_group_outside_eligible_keys_is_not_admitted(self):
        # Same pin, but only sanity + hermes_ops (n_coding=0) -> genuinely partial.
        rows = self._partial_leg(self.PINNED_CFG, self.PINNED_SHA) + \
               self._complete_leg(self.RICHER_CFG, self.RICHER_SHA)
        groups = sbc.group_rows(rows)
        gs = sbc.compute_group_stats(groups)
        eligible = {(self.MODEL, "mei", None, self.RICHER_CFG, self.RICHER_SHA)}
        selected = sbc.resolve_selection([self._pinned_record()], gs, eligible, groups)
        entry = selected[0]
        self.assertEqual(entry["gs"]["key"], self._pinned_key())
        self.assertFalse(entry["pinned_eligible"])
        self.assertFalse(entry["eligible"])
        self.assertTrue(entry["partial"])

    @unittest.skipUnless(_matplotlib_ok(), "matplotlib not available")
    def test_build_headline_charts_pinned_complete_group(self):
        rows = self._complete_leg(self.PINNED_CFG, self.PINNED_SHA) + \
               self._complete_leg(self.RICHER_CFG, self.RICHER_SHA)
        log = self._write_log(rows)
        sel = Path(self.tmp) / "sel.json"
        sel.write_text(json.dumps([
            {"family": "Ornith-1.5-35B", "engine": "mei", "model_contains": "ornith",
             "config_hash": self.RICHER_CFG, "runner_git_sha": self.RICHER_SHA},
            self._pinned_record(),
        ]))
        out = sbc.build(log_path=log, output_dir=self.out, selection_path=str(sel))
        self.assertIn(self._pinned_key(), self._headline_keys(out))
        # The richer + pinned complete groups are both admitted -> 2 comparable
        # points -> the headline chart actually renders.
        self.assertIsNotNone(out["written"]["quality_vs_runtime"])

    @unittest.skipUnless(_matplotlib_ok(), "matplotlib not available")
    def test_build_headline_excludes_pinned_partial_group(self):
        rows = self._partial_leg(self.PINNED_CFG, self.PINNED_SHA) + \
               self._complete_leg(self.RICHER_CFG, self.RICHER_SHA)
        log = self._write_log(rows)
        sel = Path(self.tmp) / "sel.json"
        sel.write_text(json.dumps([
            {"family": "Ornith-1.5-35B", "engine": "mei", "model_contains": "ornith",
             "config_hash": self.RICHER_CFG, "runner_git_sha": self.RICHER_SHA},
            self._pinned_record(),
        ]))
        out = sbc.build(log_path=log, output_dir=self.out, selection_path=str(sel))
        # The partial pinned group is NOT in the headline set.
        self.assertNotIn(self._pinned_key(), self._headline_keys(out))
        pinned = [s for s in out["selected"] if s["gs"] and s["gs"]["key"] == self._pinned_key()]
        self.assertEqual(len(pinned), 1)
        self.assertFalse(pinned[0]["pinned_eligible"])
        self.assertTrue(pinned[0]["partial"])


class ParetoTests(_Base):
    def test_pareto_efficient(self):
        # minimize x, maximize y
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [0.5, 0.3, 0.9, 0.95]
        eff = sbc.pareto_efficient(xs, ys)
        # (1.0,0.5) dominated by (2.0? no, 2>1). (2,0.3) dominated by (1,0.5).
        self.assertEqual(eff, [0, 2, 3])


if __name__ == "__main__":
    unittest.main()
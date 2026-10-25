"""Regression tests for runner/run_bench.py's speed gate.

Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import legacy_run_bench as rb


class HermesOpsTpsValuesTests(unittest.TestCase):
    """_hermes_ops_tps_values reads tokens_per_second from a hermes_ops
    --summary-out file — every task actually run, not one probe task (see
    MIN_HERMES_OPS_TOKENS_PER_SECOND's own comment for why a single-task
    probe was tried and rejected: the smallest-completion task reads
    systematically low even for genuinely fast models)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _summary(self, rows):
        p = Path(self.tmp) / "summary.json"
        p.write_text(json.dumps(rows))
        return p

    def test_reads_every_row_tokens_per_second(self):
        p = self._summary([
            {"task_id": "hermes_ops-selection", "tokens_per_second": 5.0},
            {"task_id": "hermes_ops-chaining", "tokens_per_second": 7.0},
        ])
        self.assertEqual(rb._hermes_ops_tps_values(p), [5.0, 7.0])

    def test_harness_error_rows_excluded(self):
        # A harness crash on one task isn't evidence about the MODEL's
        # speed — same exclusion build_leaderboard.py's avg tok/s uses.
        p = self._summary([
            {"task_id": "hermes_ops-selection", "tokens_per_second": 5.0},
            {"task_id": "hermes_ops-chaining", "tokens_per_second": None, "harness_error": True},
        ])
        self.assertEqual(rb._hermes_ops_tps_values(p), [5.0])

    def test_missing_summary_file_returns_none(self):
        # No speed evidence: the caller must stop as a harness failure,
        # not classify the model as slow or proceed to coding.
        self.assertIsNone(rb._hermes_ops_tps_values(Path(self.tmp) / "missing.json"))

    def test_unparseable_summary_returns_none(self):
        p = Path(self.tmp) / "bad.json"
        p.write_text("not json")
        self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_all_rows_missing_tokens_per_second_returns_none(self):
        p = self._summary([{"task_id": "hermes_ops-selection", "tokens_per_second": None}])
        self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_empty_summary_returns_none(self):
        self.assertIsNone(rb._hermes_ops_tps_values(self._summary([])))

    def test_malformed_summary_shapes_return_none(self):
        for rows in (None, {}, {"tokens_per_second": 5}, "rows", 5, True,
                     [None], [5], [[{"tokens_per_second": 5}]],
                     [{"tokens_per_second": 5}, None]):
            with self.subTest(rows=rows):
                self.assertIsNone(rb._hermes_ops_tps_values(self._summary(rows)))

    def test_unreadable_summary_returns_none(self):
        p = self._summary([{"tokens_per_second": 5}])
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("unreadable")):
            self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_invalid_utf8_summary_returns_none(self):
        p = Path(self.tmp) / "summary.json"
        p.write_bytes(b"\xff")
        self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_unusable_tps_values_return_none(self):
        for tps in (None, "5", True, False, {}, [], float("nan"),
                    float("inf"), float("-inf"), -1, 10 ** 400):
            with self.subTest(tps=tps):
                p = self._summary([{"tokens_per_second": tps}])
                self.assertIsNone(rb._hermes_ops_tps_values(p))

    def test_only_usable_numeric_tps_rows_are_read(self):
        p = self._summary([
            {"tokens_per_second": 0},
            {"tokens_per_second": 5.5},
            {"tokens_per_second": 7, "harness_error": True},
            {"tokens_per_second": "20"},
            {"tokens_per_second": True},
            {"tokens_per_second": float("nan")},
            {"tokens_per_second": float("inf")},
            {"tokens_per_second": -1},
            {},
        ])
        self.assertEqual(rb._hermes_ops_tps_values(p), [0, 5.5])


class HermesOpsHarnessGateTests(unittest.TestCase):
    """Exercise run_one without servers, weights or real append-only results."""

    def setUp(self):
        self.repo = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.repo / "results").mkdir()
        self.log = self.repo / "results" / "log.jsonl"
        self.log.write_bytes(b'{"historical":"untouched"}\n')
        self.speed_log = self.repo / "results" / "speed_gate.jsonl"
        self.config = self.repo / "config.yaml"
        # No raw_port: launch/unload paths are unnecessary for this gate.
        self.config.write_text(
            "model: test/model\ninference_engine: test\norchestration:\n"
            "  viable: full\n  hermes_provider: offline-test\n")
        self.enterContext(mock.patch.object(rb, "REPO", self.repo))
        self.suite_run = self.enterContext(mock.patch.object(rb, "run", side_effect=self.fake_suite))
        self.leaderboard = self.enterContext(mock.patch.object(rb, "_leaderboard"))
        self.enterContext(mock.patch.object(rb.subprocess, "Popen", side_effect=AssertionError("no processes")))
        self.enterContext(mock.patch.object(rb.urllib.request, "urlopen", side_effect=AssertionError("no network")))
        self.ops_returncode = 0
        self.ops_summary = json.dumps([{"tokens_per_second": 5}, {"tokens_per_second": 7.0}]).encode()

    def fake_suite(self, cmd, **_kwargs):
        suite = cmd[cmd.index("--suite") + 1]
        if "--summary-out" in cmd:
            summary = Path(cmd[cmd.index("--summary-out") + 1])
            if suite == "sanity":
                summary.write_text(json.dumps([
                    {"task_id": "sanity-basic", "pass": True},
                    {"task_id": "sanity-tool", "pass": True},
                ]))
            elif self.ops_summary is not None:
                summary.write_bytes(self.ops_summary)
        return SimpleNamespace(returncode=self.ops_returncode if suite == "hermes_ops" else 0)

    def invoke(self):
        self.suite_run.reset_mock()
        self.leaderboard.reset_mock()
        self.output = io.StringIO()
        suites = rb.parse_coding_suites(rb.build_arg_parser().parse_args(
            ["--config", str(self.config)]).coding_suites)
        with redirect_stdout(self.output):
            return rb.run_one(self.config, coding_suites=suites)

    def assert_harness_failure(self):
        self.assertFalse(self.invoke())
        self.assertEqual([call.args[0][call.args[0].index("--suite") + 1]
                          for call in self.suite_run.call_args_list], ["sanity", "hermes_ops"])
        self.assertIn("infrastructure/harness failure", self.output.getvalue())
        self.assertNotIn("Too slow", self.output.getvalue())
        self.assertFalse(self.speed_log.exists())
        self.assertEqual(self.log.read_bytes(), b'{"historical":"untouched"}\n')
        self.leaderboard.assert_called_once_with()

    def test_nonzero_subprocess_with_missing_summary_stops_before_coding(self):
        self.ops_summary = None
        for returncode in (1, -9):
            with self.subTest(returncode=returncode):
                self.ops_returncode = returncode
                self.assert_harness_failure()
                self.assertIn(f"returncode={returncode}", self.output.getvalue())

    def test_nonzero_subprocess_with_usable_summary_still_stops(self):
        self.ops_returncode = 1
        self.assert_harness_failure()

    def test_zero_return_missing_summary_stops_before_coding(self):
        self.ops_summary = None
        self.assert_harness_failure()

    def test_zero_return_unusable_summary_stops_before_coding(self):
        summaries = [b"not JSON", b"\xff", b"null", b"{}", b"[]", b"[null]",
                     b'[{"tokens_per_second": 5}, null]',
                     b'[{"tokens_per_second": 9, "harness_error": true}]',
                     b'[{}, {"tokens_per_second": null}]',
                     b'[{"tokens_per_second": "9"}, {"tokens_per_second": true}]',
                     b'[{"tokens_per_second": NaN}, {"tokens_per_second": Infinity}]']
        for summary in summaries:
            with self.subTest(summary=summary):
                self.ops_summary = summary
                self.assert_harness_failure()

    def test_zero_return_unreadable_summary_stops_before_coding(self):
        read_text = Path.read_text

        def unreadable_ops(path, *args, **kwargs):
            if path.name == "hermes_ops_summary.json":
                raise PermissionError("unreadable Ops summary")
            return read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", unreadable_ops):
            self.assert_harness_failure()

    def test_valid_fast_and_threshold_summaries_continue_to_full_coding(self):
        for values in ([5, 7.0], [rb.MIN_HERMES_OPS_TOKENS_PER_SECOND]):
            with self.subTest(values=values):
                self.ops_summary = json.dumps([{"tokens_per_second": tps} for tps in values]).encode()
                self.assertTrue(self.invoke())
                self.assertEqual([call.args[0][call.args[0].index("--suite") + 1]
                                  for call in self.suite_run.call_args_list],
                                 ["sanity", "hermes_ops", "kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"])
                self.assertFalse(self.speed_log.exists())
                self.assertNotIn("infrastructure/harness failure", self.output.getvalue())
                self.leaderboard.assert_called_once_with()

    def test_valid_slow_summary_still_records_speed_gate_and_skips_coding(self):
        values = [0, rb.MIN_HERMES_OPS_TOKENS_PER_SECOND / 2]
        self.ops_summary = json.dumps([{"tokens_per_second": tps} for tps in values]).encode()
        self.assertFalse(self.invoke())
        self.assertEqual([call.args[0][call.args[0].index("--suite") + 1]
                          for call in self.suite_run.call_args_list], ["sanity", "hermes_ops"])
        row, = [json.loads(line) for line in self.speed_log.read_text().splitlines()]
        self.assertEqual(row["model"], "test/model")
        self.assertEqual(row["inference_engine"], "test")
        self.assertEqual(row["measured_tokens_per_second"], values)
        self.assertEqual(row["avg_tokens_per_second"], sum(values) / len(values))
        self.assertEqual(row["threshold_tokens_per_second"], rb.MIN_HERMES_OPS_TOKENS_PER_SECOND)
        self.assertIn("Too slow", self.output.getvalue())
        self.assertNotIn("infrastructure/harness failure", self.output.getvalue())
        self.assertEqual(self.log.read_bytes(), b'{"historical":"untouched"}\n')
        self.leaderboard.assert_called_once_with()

    def test_cli_reports_harness_failure_as_nonzero_exit(self):
        self.ops_summary = None
        with mock.patch.object(sys, "argv", ["run_bench.py", "--config", str(self.config)]), \
                mock.patch.object(rb, "sweep_stale_run_dirs"), \
                redirect_stdout(io.StringIO()) as output, \
                self.assertRaises(SystemExit) as raised:
            rb.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("infrastructure/harness failure", output.getvalue())
        self.assertFalse(self.speed_log.exists())
        self.assertEqual(self.suite_run.call_count, 2)


class SpeedGateFailureRecordTests(unittest.TestCase):
    """_record_speed_gate_failure writes to results/speed_gate.jsonl, a
    dedicated append-only log kept separate from log.jsonl (whose task/
    suite-keyed schema every grouping/flakiness check in
    build_leaderboard.py assumes) and separate from the config YAML files
    (which stay hand-authored, not rewritten by this automated check)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp)
        (self.repo / "results").mkdir()
        self._orig_repo = rb.REPO
        rb.REPO = self.repo

    def tearDown(self):
        rb.REPO = self._orig_repo
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_one_jsonl_row_with_expected_fields(self):
        rb._record_speed_gate_failure(
            "m", "mlx", Path("configs/m/mlx.yaml"), "hash123", [0.18, 0.22, 0.31], 0.237,
        )
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model"], "m")
        self.assertEqual(rows[0]["measured_tokens_per_second"], [0.18, 0.22, 0.31])
        self.assertEqual(rows[0]["avg_tokens_per_second"], 0.237)
        self.assertEqual(rows[0]["threshold_tokens_per_second"], rb.MIN_HERMES_OPS_TOKENS_PER_SECOND)

    def test_appends_rather_than_overwrites(self):
        rb._record_speed_gate_failure("m1", "mlx", Path("c1.yaml"), "h1", [0.1], 0.1)
        rb._record_speed_gate_failure("m2", "gguf", Path("c2.yaml"), "h2", [0.2], 0.2)
        rows = [json.loads(l) for l in (self.repo / "results" / "speed_gate.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 2)


class MinTokensPerSecondValueTests(unittest.TestCase):
    """Guards the actual cutoff value — a deliberate user decision (lowered
    2026-08-23 from an initial 10 tok/s to 4 tok/s, to keep more variety in
    the results rather than narrowing the field this early), not something
    that should silently drift back to an earlier bar."""

    def test_threshold_is_four(self):
        self.assertEqual(rb.MIN_HERMES_OPS_TOKENS_PER_SECOND, 4.0)


class BackendHealthTimeoutTests(unittest.TestCase):
    """Raised 2026-08-26 from 600s to 1800s after two confirmed false
    negatives: a large GGUF's cold-cache first load (LiquidAI/LFM2.5-8B-
    A1B-GGUF:BF16, then ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M at
    ~17.5min) can genuinely exceed 600s while the server is loading fine —
    confirmed both times via the server log ("model loaded"/"listening")
    and a live curl, not a real hang. wait_for_health()'s own default must
    track BACKEND_HEALTH_TIMEOUT_SECONDS, not silently drift back to a
    hardcoded 600."""

    def test_constant_is_1800_seconds(self):
        self.assertEqual(rb.BACKEND_HEALTH_TIMEOUT_SECONDS, 1800)

    def test_wait_for_health_default_uses_the_constant(self):
        import inspect
        default = inspect.signature(rb.wait_for_health).parameters["timeout"].default
        self.assertEqual(default, rb.BACKEND_HEALTH_TIMEOUT_SECONDS)


class CodingSuitesDefaultTests(unittest.TestCase):
    """--coding-suites' default flipped from None (quick spot-check) to
    the full battery on 2026-08-25 — "run all tests"/"full benchmark run"
    kept getting the quick spot-check instead because the full battery was
    opt-in and easy to forget to ask for (see AGENTS.md). Guards both the
    CLI default itself and parse_coding_suites()'s "none" escape hatch."""

    def test_cli_default_is_the_full_battery_not_none(self):
        ap = rb.build_arg_parser()
        args = ap.parse_args(["--config", "configs/whatever/gguf.yaml"])
        self.assertEqual(args.coding_suites, "kiem_mini,hearth_mini,kipclip_mini,hearth_full")
        self.assertEqual(
            rb.parse_coding_suites(args.coding_suites),
            ["kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"],
        )

    def test_none_string_opts_out_to_the_quick_spot_check(self):
        for raw in ("none", "None", " NONE "):
            self.assertIsNone(rb.parse_coding_suites(raw))

    def test_none_value_also_opts_out(self):
        self.assertIsNone(rb.parse_coding_suites(None))

    def test_explicit_single_suite_still_works(self):
        self.assertEqual(rb.parse_coding_suites("kiem_mini"), ["kiem_mini"])

    def test_whitespace_around_suite_names_is_stripped(self):
        self.assertEqual(
            rb.parse_coding_suites(" kiem_mini , hearth_mini "),
            ["kiem_mini", "hearth_mini"],
        )


class AllSweepOrderingTests(unittest.TestCase):
    """_discover_ordered_configs drives the --all / engine sweep. Existing
    configs carry no orchestration.run_order, so they must enumerate in plain
    lexical order exactly as before; a deliberately-orderable model (Ling-3.0-
    tiny, whose directory would lexically sort before Ornith) must run LAST
    behind the four established Mei configs without renaming its directory and
    without perturbing any other config's relative order."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "configs").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, model, run_order=None, engine="mei", include_orchestration=True):
        d = self.tmp / "configs" / model
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"model: {model}", f"inference_engine: {engine}"]
        if include_orchestration:
            lines.append("orchestration:")
            if run_order is not None:
                lines.append(f"  run_order: {run_order}")
        (d / "mei.yaml").write_text("\n".join(lines) + "\n")

    def _names(self, **kw):
        return [p.parent.name for p in rb._discover_ordered_configs(self.tmp, **kw)]

    def test_existing_configs_keep_lexical_order_without_run_order(self):
        for m in ["Gemma-4-26B-A4B", "Ling-3.0-tiny", "Ornith-1.5-35B-A3B", "Qwen3.8-27B"]:
            self._write(m)
        self.assertEqual(self._names(), [
            "Gemma-4-26B-A4B", "Ling-3.0-tiny", "Ornith-1.5-35B-A3B", "Qwen3.8-27B",
        ])

    def test_high_run_order_places_model_last_behind_the_four(self):
        # Without run_order, Ling would run 2nd (lexically before Ornith).
        # With run_order it must run LAST behind the four established configs,
        # whose relative order is unchanged.
        self._write("Ling-3.0-tiny", run_order=1)
        for m in ["Gemma-4-26B-A4B", "Ornith-1.5-35B-A3B", "Qwen3.8-27B", "Qwen3.8-27B-Uncensored"]:
            self._write(m)
        got = self._names()
        self.assertEqual(got[-1], "Ling-3.0-tiny")
        self.assertEqual(got[:-1], [
            "Gemma-4-26B-A4B", "Ornith-1.5-35B-A3B", "Qwen3.8-27B", "Qwen3.8-27B-Uncensored",
        ])

    def test_engine_filter_applies_before_run_order_sort(self):
        self._write("Zzz-gguf", engine="llama.cpp")
        self._write("Ling-3.0-tiny", run_order=1, engine="mei")
        self._write("Ornith-1.5-35B-A3B", engine="mei")
        self.assertEqual(self._names(inference_engine="mei"), [
            "Ornith-1.5-35B-A3B", "Ling-3.0-tiny",
        ])

    def test_non_int_run_order_is_ignored(self):
        # Robustness: only int run_order is honored; a non-int (here a float)
        # falls back to 0 so a malformed value can't mis-order the sweep.
        self._write("Ling-3.0-tiny", run_order=1.5, engine="mei")
        self._write("Ornith-1.5-35B-A3B", engine="mei")
        self.assertEqual(self._names(inference_engine="mei"), [
            "Ling-3.0-tiny", "Ornith-1.5-35B-A3B",
        ])

    def test_config_without_orchestration_block_is_skipped(self):
        # A stray non-config .yaml must never become a run (finding L3).
        self._write("Aaa")
        (self.tmp / "configs" / "Notes").mkdir()
        (self.tmp / "configs" / "Notes" / "memo.yaml").write_text("not a config\n")
        self.assertEqual(self._names(), ["Aaa"])


if __name__ == "__main__":
    unittest.main()

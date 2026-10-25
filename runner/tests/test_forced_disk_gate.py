"""Explicit disk-only diagnostics stay auditable and outside headline rankings.

All launches, endpoint calls, agent runs and graders are mocked. Every write
lands in a disposable scratch repo, never the real append-only results.
Run: uv run --locked python -m unittest runner.tests.test_forced_disk_gate -v
"""
import builtins
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bench_common as bc
import build_leaderboard as bl
import build_summary_charts as charts
import plot_leaderboard as plot
import legacy_run_bench as rb
import run_fixture_suite as fixtures
import run_prompt_suite as prompts


DIAGNOSTIC = {"forced_gate": True, "exploratory": True, "rank_eligible": False}
GIB = 1024 ** 3


class ScratchRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.repo = Path(self.tmp).resolve()
        (self.repo / "results").mkdir()
        self.log = self.repo / "results" / "log.jsonl"
        self.log.write_bytes(b"\n")
        for module in (bc, rb, bl, charts, plot, prompts, fixtures):
            self.enterContext(mock.patch.object(module, "REPO", self.repo))
        self.enterContext(mock.patch.object(bl, "_is_v2_or_later", return_value=True))
        self.enterContext(mock.patch.object(bc, "git_sha", return_value="test-runner"))
        self.config = self.repo / "configs" / "Flint" / "mei.yaml"
        self.config.parent.mkdir(parents=True)

    def write_config(self, flags=None):
        cfg = {
            "model": "test/Flint", "inference_engine": "mei",
            "benchmark_launch_command": "never-start-a-server",
            "orchestration": {
                "raw_port": 8024, "served_model_id": "test-flint",
                "viable": "full", "hermes_provider": "test-provider",
                **(flags or {}),
            },
        }
        self.config.write_text(yaml.safe_dump(cfg))
        return cfg


class DiskGateTestCase(ScratchRepoTests):
    def setUp(self):
        super().setUp()
        self.write_config()
        self.enterContext(mock.patch.object(rb, "git_sha", return_value="test-runner"))
        self.free_bytes = 9 * GIB
        self.disk = self.enterContext(mock.patch.object(
            rb.shutil, "disk_usage", side_effect=lambda _p: SimpleNamespace(free=self.free_bytes)))
        self.suite_run = self.enterContext(mock.patch.object(rb, "run", side_effect=self.fake_suite))
        self.enterContext(mock.patch.object(rb, "clear_kv_cache_dir"))
        self.launch = self.enterContext(mock.patch.object(rb.subprocess, "Popen"))
        self.health = self.enterContext(mock.patch.object(rb, "wait_for_health", return_value=True))
        self.identity = self.enterContext(mock.patch.object(rb, "assert_serving_expected_model", return_value=True))
        self.completion = self.enterContext(mock.patch.object(rb, "assert_plain_completion", return_value=True))
        self.proxy = self.enterContext(mock.patch.object(rb, "assert_proxy_matches", return_value=True))
        self.enterContext(mock.patch.object(rb, "_leaderboard"))
        self.enterContext(mock.patch.object(rb.urllib.request, "urlopen", side_effect=AssertionError("no network")))
        self.enterContext(mock.patch.object(rb, "open", side_effect=self.scratch_open, create=True))
        self.ops_tps = rb.MIN_HERMES_OPS_TOKENS_PER_SECOND + 1
        self.sanity_pass = True

    def scratch_open(self, path, *args, **kwargs):
        # The runner's pre-existing server-log path is /tmp; do not touch it.
        if str(path).startswith("/tmp/bench_"):
            path = self.repo / Path(path).name
        return builtins.open(path, *args, **kwargs)

    def fake_suite(self, cmd, **_kw):
        if "--summary-out" in cmd:
            suite = cmd[cmd.index("--suite") + 1]
            rows = ([{"task_id": "sanity-basic", "pass": self.sanity_pass},
                     {"task_id": "sanity-tool", "pass": True}]
                    if suite == "sanity" else [{"tokens_per_second": self.ops_tps}])
            Path(cmd[cmd.index("--summary-out") + 1]).write_text(json.dumps(rows))
        return SimpleNamespace(returncode=0)

    def invoke(self, force=None, **kwargs):
        if force is not None:
            kwargs["force_disk_gate"] = force
        return rb.run_one(self.config, coding_suites=["kiem_mini"], **kwargs)

    def audit_rows(self):
        return [json.loads(line) for line in
                (self.repo / "results" / "disk_preflight.jsonl").read_text().splitlines()]

    def coding_calls(self):
        return [c for c in self.suite_run.call_args_list if "--hermes-provider" in c.args[0]]


class DiskGateTests(DiskGateTestCase):
    def test_default_ten_gib_refusal_and_boundary_unchanged(self):
        self.assertEqual(bc.MIN_FREE_DISK_GB_BEFORE_LAUNCH, 10.0)
        self.free_bytes = 10 * GIB - 1
        self.assertFalse(self.invoke())
        self.launch.assert_not_called()
        self.assertEqual(self.log.read_bytes(), b"\n")
        self.free_bytes = 10 * GIB
        self.assertTrue(self.invoke())
        self.launch.assert_called_once()

    def test_config_flags_alone_do_not_override_disk_gate(self):
        self.write_config(DIAGNOSTIC)
        self.assertFalse(self.invoke())
        self.launch.assert_not_called()

    def test_cli_opt_in_requires_every_literal_config_flag_even_above_floor(self):
        for key, expected in DIAGNOSTIC.items():
            for bad in ("absent", None, not expected, int(expected), str(expected).lower()):
                for free_bytes in (9 * GIB, 11 * GIB):
                    with self.subTest(key=key, bad=bad, free_bytes=free_bytes):
                        flags = dict(DIAGNOSTIC)
                        if bad == "absent":
                            flags.pop(key)
                        else:
                            flags[key] = bad
                        self.write_config(flags)
                        self.free_bytes = free_bytes
                        with self.assertRaisesRegex(SystemExit, "forced_gate.*exploratory.*rank_eligible"):
                            self.invoke(True)
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_forced_run_records_measured_shortfall_and_immutable_config(self):
        self.write_config(DIAGNOSTIC)
        original = self.config.read_bytes()
        self.assertTrue(self.invoke(True))
        self.assertEqual(len(self.coding_calls()), 1)
        entry, = self.audit_rows()
        self.assertEqual(entry["observed_free_bytes"], self.free_bytes)
        self.assertEqual(entry["floor_gib"], 10.0)
        self.assertEqual(entry["floor_bytes"], 10 * GIB)
        self.assertEqual(entry["shortfall_bytes"], GIB)
        self.assertIs(entry["disk_gate_overridden"], True)
        self.assertIs(entry["force_disk_gate"], True)
        for key, value in DIAGNOSTIC.items():
            self.assertIs(entry[key], value)
        self.assertEqual(entry["runner_git_sha"], "test-runner")
        self.assertEqual(entry["config_path"], "configs/Flint/mei.yaml")
        self.assertTrue(entry["timestamp"].endswith("Z"))
        self.assertEqual(entry["config_hash"], hashlib.sha256(original).hexdigest()[:12])
        self.assertEqual((self.repo / "results" / "configs" / f"{entry['config_hash']}.yaml").read_bytes(), original)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(self.log.read_bytes(), b"\n")
        self.health.assert_called_once()
        self.identity.assert_called_once()
        self.completion.assert_called_once()

    def test_opt_in_above_floor_remains_unranked_but_does_not_claim_override(self):
        self.write_config(DIAGNOSTIC)
        self.free_bytes = 11 * GIB
        self.assertTrue(self.invoke(True))
        entry, = self.audit_rows()
        self.assertIs(entry["disk_gate_overridden"], False)
        self.assertEqual(entry["shortfall_bytes"], 0)
        self.assertIs(entry["rank_eligible"], False)

    def test_forced_suites_use_the_immutable_diagnostic_not_an_edited_live_config(self):
        self.write_config(DIAGNOSTIC)
        original = self.config.read_bytes()
        # Simulate an edit while the server is loading, after disk admission.
        self.health.side_effect = lambda *_a, **_k: (self.write_config(), True)[1]
        self.assertTrue(self.invoke(True))
        calls = [call.args[0] for call in self.suite_run.call_args_list if "--config" in call.args[0]]
        self.assertEqual(len(calls), 3)  # sanity, Hermes Ops, coding
        for cmd in calls:
            suite_config = Path(cmd[cmd.index("--config") + 1])
            self.assertNotEqual(suite_config, self.config)
            self.assertEqual(suite_config.read_bytes(), original)

    def test_opt_in_is_local_full_diagnostic_only(self):
        for field, value in (("raw_port", None), ("viable", "coding_only"), ("viable", "sanity_only")):
            with self.subTest(field=field, value=value):
                cfg = self.write_config(DIAGNOSTIC)
                cfg["orchestration"][field] = value
                self.config.write_text(yaml.safe_dump(cfg))
                with self.assertRaises(SystemExit):
                    self.invoke(True)
        self.launch.assert_not_called()

    def test_opt_in_rejects_a_hosted_suite_even_with_a_local_port(self):
        cfg = self.write_config(DIAGNOSTIC)
        cfg["orchestration"].update(
            api_base_url="https://never.invalid/v1", api_key_env="OFFLINE_TEST_KEY")
        self.config.write_text(yaml.safe_dump(cfg))
        with mock.patch.dict("os.environ", {"OFFLINE_TEST_KEY": "test-only"}), \
                self.assertRaisesRegex(SystemExit, "local"):
            self.invoke(True)
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_malformed_config_refuses_opt_in_before_launch(self):
        for cfg in (None, [], "not a mapping", {"orchestration": True},
                    {"orchestration": [DIAGNOSTIC]}):
            with self.subTest(cfg=cfg):
                self.config.write_text(yaml.safe_dump(cfg))
                with self.assertRaises(SystemExit):
                    self.invoke(True)
        self.launch.assert_not_called()

    def test_config_change_or_corrupt_snapshot_refuses_launch_without_rewriting(self):
        self.write_config(DIAGNOSTIC)
        self.suite_run.reset_mock()
        # Change the authored config after admission validation, before audit.
        with mock.patch.object(rb, "clear_kv_cache_dir", side_effect=lambda _cfg: self.write_config()):
            with self.assertRaisesRegex(SystemExit, "config changed"):
                self.invoke(True)
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

        self.write_config(DIAGNOSTIC)
        config_hash, _ = bc.snapshot_config(self.config)
        snapshot = self.repo / "results" / "configs" / f"{config_hash}.yaml"
        snapshot.write_text("corrupt previous snapshot\n")
        with self.assertRaisesRegex(SystemExit, "snapshot does not match"):
            self.invoke(True)
        self.launch.assert_not_called()
        self.assertEqual(snapshot.read_text(), "corrupt previous snapshot\n")
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_teardown_uses_admitted_identity_even_if_authored_config_is_lost(self):
        def edit_authored(edit):
            if edit == "delete":
                self.config.unlink()
            elif edit == "malformed":
                self.config.write_text("orchestration: [\n")
            else:
                cfg = self.write_config()
                cfg["inference_engine"] = "not-mei"
                self.config.write_text(yaml.safe_dump(cfg))

        for edit in ("delete", "malformed", "different-engine"):
            for outcome in (True, False, RuntimeError("simulated load failure")):
                with self.subTest(edit=edit, outcome=outcome):
                    self.write_config(DIAGNOSTIC)
                    self.suite_run.reset_mock()

                    def during_load(*_args, **_kwargs):
                        edit_authored(edit)
                        if isinstance(outcome, Exception):
                            raise outcome
                        return outcome

                    self.health.side_effect = during_load
                    if isinstance(outcome, Exception):
                        with self.assertRaisesRegex(RuntimeError, "simulated load failure"):
                            self.invoke(True)
                    else:
                        self.assertEqual(bool(self.invoke(True)), outcome)
                    self.assertEqual(self.suite_run.call_args.args[0],
                                     ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_audit_fsync_failure_prevents_launch(self):
        self.write_config(DIAGNOSTIC)
        with mock.patch.object(rb.os, "fsync", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.invoke(True)
        self.launch.assert_not_called()

    def test_audit_is_append_only_and_failure_prevents_launch(self):
        self.write_config(DIAGNOSTIC)
        self.invoke(True)
        audit = self.repo / "results" / "disk_preflight.jsonl"
        before = audit.read_bytes()
        self.invoke(True)
        self.assertTrue(audit.read_bytes().startswith(before))
        self.assertEqual(len(self.audit_rows()), 2)
        self.launch.reset_mock()
        with mock.patch.object(rb, "_record_disk_preflight", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.invoke(True)
        self.launch.assert_not_called()

    def test_override_does_not_bypass_other_fail_fast_gates(self):
        self.write_config(DIAGNOSTIC)
        for failing in (self.health, self.identity, self.completion):
            with self.subTest(gate=failing):
                failing.return_value = False
                self.suite_run.reset_mock()
                self.assertFalse(self.invoke(True))
                self.assertFalse(self.coding_calls())
                failing.return_value = True
        self.sanity_pass = False
        self.assertFalse(self.invoke(True))
        self.assertFalse(self.coding_calls())
        self.sanity_pass = True
        self.ops_tps = rb.MIN_HERMES_OPS_TOKENS_PER_SECOND - 1
        self.assertFalse(self.invoke(True))
        self.assertFalse(self.coding_calls())
        self.assertTrue((self.repo / "results" / "speed_gate.jsonl").exists())
        cfg = yaml.safe_load(self.config.read_text())
        cfg["orchestration"].update(needs_proxy=True, proxy_parser="test-parser")
        self.config.write_text(yaml.safe_dump(cfg))
        self.proxy.return_value = False
        self.assertFalse(self.invoke(True))
        self.assertFalse(self.coding_calls())

    def test_forced_run_preserves_sanity_tool_and_harness_failure_gates(self):
        self.write_config(DIAGNOSTIC)
        for failure in ("exit", "missing", "corrupt", "harness-error", "sanity-tool"):
            with self.subTest(failure=failure):
                self.suite_run.reset_mock()

                def broken_sanity(cmd, **kwargs):
                    proc = self.fake_suite(cmd, **kwargs)
                    if "--suite" not in cmd or cmd[cmd.index("--suite") + 1] != "sanity":
                        return proc
                    summary = Path(cmd[cmd.index("--summary-out") + 1])
                    if failure == "exit":
                        return SimpleNamespace(returncode=1)
                    if failure == "missing":
                        summary.unlink()
                    elif failure == "corrupt":
                        summary.write_text("not JSON")
                    else:
                        rows = json.loads(summary.read_text())
                        if failure == "harness-error":
                            rows[0]["harness_error"] = True
                        else:
                            rows[1]["pass"] = False
                        summary.write_text(json.dumps(rows))
                    return proc

                self.suite_run.side_effect = broken_sanity
                self.assertFalse(self.invoke(True))
                self.assertFalse(self.coding_calls())
                prompt_suites = [c.args[0][c.args[0].index("--suite") + 1]
                                 for c in self.suite_run.call_args_list if "--suite" in c.args[0]]
                self.assertEqual(prompt_suites, ["sanity"])
                self.assertEqual(self.suite_run.call_args.args[0],
                                 ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_cli_defaults_off_and_forwards_single_config_opt_in(self):
        self.assertFalse(rb.build_arg_parser().parse_args(["--config", str(self.config)]).force_disk_gate)
        with mock.patch.object(sys, "argv", ["run_bench.py", "--config", str(self.config), "--force-disk-gate"]), \
                mock.patch.object(rb, "run_one", return_value=True) as run_one, \
                mock.patch.object(rb, "sweep_stale_run_dirs"):
            rb.main()
        self.assertIs(run_one.call_args.kwargs["force_disk_gate"], True)
        self.assertEqual(run_one.call_args.kwargs["coding_suites"],
                         ["kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"])

    def test_opt_in_rejects_sweeps_and_coding_only_before_side_effects(self):
        for target in (["--all"], ["--config", str(self.config), "--stage", "coding"]):
            with self.subTest(target=target), \
                    mock.patch.object(sys, "argv", ["run_bench.py", *target, "--force-disk-gate"]), \
                    mock.patch.object(rb, "run_one") as run_one, \
                    mock.patch.object(rb, "sweep_stale_run_dirs") as sweep:
                with self.assertRaises(SystemExit):
                    rb.main()
                run_one.assert_not_called()
                sweep.assert_not_called()
        self.write_config(DIAGNOSTIC)
        with self.assertRaises(SystemExit):
            self.invoke(True, stage="coding")
        self.launch.assert_not_called()


class DiagnosticRankingTests(ScratchRepoTests):
    def setUp(self):
        super().setUp()
        # Exercise the actual full-battery boundary, independent of small
        # fixture-size patches used by older leaderboard tests.
        self.enterContext(mock.patch.object(bl, "FULL_HERMES_OPS_TASKS", 8))
        self.enterContext(mock.patch.object(bl, "FULL_CODING_TASKS", 15))

    def group(self, model, flags=None, timestamp="2026-10-22T12:00:00Z", row_metadata=False):
        self.write_config(flags)
        config_hash, config_path = bc.snapshot_config(self.config)
        key = (model, "mei", None, config_hash, "test-runner")
        rows = []
        for suite, count in (("sanity", 2), ("hermes_ops", 8), ("kiem_mini", 15)):
            for i in range(count):
                row = {"model": model, "inference_engine": "mei", "suite": suite,
                       "task_id": f"{suite}-{i}", "pass": True, "grade_output": "PASS",
                       "config_hash": config_hash, "config_path": config_path,
                       "runner_git_sha": "test-runner", "timestamp": timestamp,
                       "wall_seconds": 10, "ttft_seconds": 2, "completion_tokens": 80,
                       "hermes_turns": 2}
                if row_metadata:
                    row["rank_eligible"] = not bool(flags)
                rows.append(row)
        return key, rows

    def test_snapshot_false_excludes_complete_group_and_chart_but_preserves_raw_rows(self):
        normal, normal_rows = self.group("ordinary")
        forced, forced_rows = self.group("forced-Flint", DIAGNOSTIC)
        groups = {normal: normal_rows, forced: forced_rows}
        stats = bl.compute_group_stats(groups)
        ranked = bl.rank_groups(stats)
        self.assertEqual([gs["key"] for _gate, _score, gs in ranked], [normal])
        self.assertIs(next(gs for gs in stats if gs["key"] == forced)["rank_eligible"], False)
        # Live config changes must not re-admit the immutable diagnostic.
        self.write_config()
        with self.log.open("ab") as f:
            for row in normal_rows + forced_rows:
                f.write((json.dumps(row) + "\n").encode())
        original = self.log.read_bytes()
        bl.main()
        text = (self.repo / "results" / "LEADERBOARD.md").read_text()
        overall = text.split("## Best overall", 1)[1].split("## Flaky tasks", 1)[0]
        self.assertNotIn("| forced-Flint |", overall)
        self.assertIn("| ordinary |", overall)
        self.assertIn("rank-ineligible", text)
        self.assertIn("| forced-Flint |", text.split("## Best overall", 1)[0])
        self.assertEqual([r["model"] for r in plot.build_ranked_rows(self.log)], ["ordinary"])
        self.assertEqual(self.log.read_bytes(), original)
        self.assertEqual(len([json.loads(line) for line in original.splitlines() if line]), 50)

    def test_forced_fragment_cannot_displace_ordinary_or_change_normalization(self):
        normal, normal_rows = self.group("same-model")
        forced, forced_rows = self.group("same-model", DIAGNOSTIC, "2026-10-22T23:00:00Z")
        for row in forced_rows:
            row.update(completion_tokens=800000, ttft_seconds=0.001)
        baseline = bl.rank_groups(bl.compute_group_stats({normal: normal_rows}))
        ranked = bl.rank_groups(bl.compute_group_stats({normal: normal_rows, forced: forced_rows}))
        self.assertEqual([(gate, score, gs["key"]) for gate, score, gs in ranked],
                         [(gate, score, gs["key"]) for gate, score, gs in baseline])

    def test_authorized_floor_waiver_ranks_normally_without_re_admitting_diagnostics(self):
        normal, normal_rows = self.group("ordinary")
        authorized, authorized_rows = self.group("authorized-Flint", {"disk_floor_override_authorized": True})
        forced, forced_rows = self.group("diagnostic", {**DIAGNOSTIC, "disk_floor_override_authorized": True})
        groups = {normal: normal_rows, authorized: authorized_rows, forced: forced_rows}
        stats = bl.compute_group_stats(groups)
        ranked_keys = {gs["key"] for _gate, _score, gs in bl.rank_groups(stats)}
        self.assertEqual(ranked_keys, {normal, authorized})
        self.assertIs(next(gs for gs in stats if gs["key"] == authorized)["rank_eligible"], True)
        for row in normal_rows + authorized_rows + forced_rows:
            with self.log.open("a") as f:
                f.write(json.dumps(row) + "\n")
        self.assertEqual({row["model"] for row in plot.build_ranked_rows(self.log)},
                         {"ordinary", "authorized-Flint"})
        record = {"family": "Flint", "engine": "mei", "model": "authorized-Flint",
                  "config_hash": authorized[3]}
        selected, = charts.resolve_selection([record], stats, ranked_keys, groups)
        self.assertIs(selected["eligible"], True)
        combined = {"family": "Flint", "engine": "mei", "fragments": [
            {"model": key[0], "config_hash": key[3]} for key in (normal, authorized)]}
        selected, = charts.resolve_selection([combined], stats, ranked_keys, groups)
        self.assertIs(selected["eligible"], True)

    def test_single_false_row_veto_survives_missing_snapshot_and_harness_error(self):
        key, rows = self.group("forced-Flint", DIAGNOSTIC)
        (self.repo / "results" / "configs" / f"{key[3]}.yaml").unlink()
        self.config.unlink()
        rows.append({**rows[0], "rank_eligible": False, "harness_error": True})
        self.assertEqual(bl.rank_groups(bl.compute_group_stats({key: rows})), [])

    def test_each_diagnostic_snapshot_marker_is_an_independent_veto(self):
        for flags in ({"rank_eligible": False}, {"forced_gate": True}, {"exploratory": True}):
            with self.subTest(flags=flags):
                key, rows = self.group("diagnostic", flags)
                self.assertEqual(bl.rank_groups(bl.compute_group_stats({key: rows})), [])

    def test_row_diagnostic_markers_veto_even_without_a_snapshot(self):
        key, rows = self.group("ordinary")
        (self.repo / "results" / "configs" / f"{key[3]}.yaml").unlink()
        self.config.unlink()
        for key_name, value in (("rank_eligible", False), ("forced_gate", True), ("exploratory", True)):
            with self.subTest(marker=key_name):
                diagnostic_rows = rows + [{**rows[0], key_name: value, "harness_error": True}]
                self.assertEqual(bl.rank_groups(bl.compute_group_stats({key: diagnostic_rows})), [])

    def test_legacy_configs_keep_eligibility_but_malformed_declarations_do_not(self):
        for cfg in ({}, {"model": "legacy"}, {"orchestration": None},
                    {"orchestration": {}}, {"orchestration": {"rank_eligible": True}}):
            with self.subTest(legacy=cfg):
                self.assertIs(bc.config_rank_eligible(cfg), True)
        for cfg in (None, [], {"orchestration": False}, {"orchestration": []}):
            with self.subTest(malformed=cfg):
                self.assertIs(bc.config_rank_eligible(cfg), False)
        for key_name, good in (("rank_eligible", True), ("forced_gate", False), ("exploratory", False)):
            for value in (None, int(good), str(good).lower(), not good):
                with self.subTest(marker=key_name, value=value):
                    self.assertIs(bc.config_rank_eligible({"orchestration": {key_name: value}}), False)

    def test_corrupt_snapshot_cannot_grant_ranking_permission(self):
        key, rows = self.group("ordinary")
        snapshot = self.repo / "results" / "configs" / f"{key[3]}.yaml"
        snapshot.write_text("orchestration: {rank_eligible: true}\n")
        self.assertEqual(bl.rank_groups(bl.compute_group_stats({key: rows})), [])

    def test_later_snapshot_only_diagnostic_vetoes_a_mixed_curated_combination(self):
        normal, normal_rows = self.group("same-model")
        forced, forced_rows = self.group("same-model", DIAGNOSTIC)
        groups = {normal: normal_rows, forced: forced_rows}
        stats = bl.compute_group_stats(groups)
        record = {"family": "Flint", "engine": "mei", "fragments": [
            {"model": "same-model", "config_hash": key[3]} for key in (normal, forced)]}
        selected, = charts.resolve_selection([record], stats, {normal}, groups)
        self.assertIs(selected["eligible"], False)

    def test_curated_pins_and_combination_cannot_re_admit_diagnostic(self):
        key, rows = self.group("forced-Flint", DIAGNOSTIC, row_metadata=True)
        groups = {key: rows}
        stats = bl.compute_group_stats(groups)
        record = {"family": "Flint", "engine": "mei", "model": "forced-Flint", "config_hash": key[3]}
        selected, = charts.resolve_selection([record], stats, set(), groups)
        self.assertIs(selected["eligible"], False)
        combined = {"family": "Flint", "engine": "mei", "fragments": [
            {"model": "forced-Flint", "config_hash": key[3]}]}
        selected, = charts.resolve_selection([combined], stats, set(), groups)
        self.assertIs(selected["eligible"], False)

    def test_curated_diagnostic_never_enters_engine_delta_comparisons(self):
        forced, forced_rows = self.group("forced-Flint", DIAGNOSTIC)
        normal, normal_rows = self.group("ordinary-gguf")
        normal = (normal[0], "llama.cpp", *normal[2:])
        for row in normal_rows:
            row["inference_engine"] = "llama.cpp"
        pinned = {"family": "Flint", "engine": "mei", "model": forced[0],
                  "config_hash": forced[3]}
        combined = {"family": "Flint", "engine": "mei", "fragments": [
            {"model": forced[0], "config_hash": forced[3]}]}
        ordinary = {"family": "Flint", "engine": "llama.cpp", "model": normal[0],
                    "config_hash": normal[3]}
        for diagnostic in (pinned, combined):
            with self.subTest(selection=diagnostic):
                groups = {normal: normal_rows, forced: forced_rows}
                stats = bl.compute_group_stats(groups)
                selected = charts.resolve_selection([diagnostic, ordinary], stats, {normal}, groups)
                self.assertIs(selected[0]["eligible"], False)
                pairs, skipped = charts.compute_engine_deltas(selected)
                self.assertEqual(pairs, [])
                self.assertEqual(skipped, [
                    {"family": "Flint", "reason": "no mei group selected (only llama.cpp)"}])


class AppendOnlySuiteMetadataTests(ScratchRepoTests):
    @contextmanager
    def no_repository_guard(self, _repo, result):
        result["changed"] = False
        yield

    def test_both_suite_writers_append_rank_ineligible_rows_and_keep_transcripts(self):
        self.assert_suite_metadata(DIAGNOSTIC, rank_eligible=False)

    def test_both_suite_writers_keep_authorized_waiver_rows_rank_eligible(self):
        self.assert_suite_metadata({"disk_floor_override_authorized": True}, rank_eligible=True)

    def test_current_direct_sanity_rows_are_scoped_and_never_legacy_ranked(self):
        self.assert_suite_metadata({}, rank_eligible=True, current=True)

    def assert_suite_metadata(self, flags, rank_eligible, current=False):
        self.write_config(flags)
        # Both disk exceptions pass this exact content-addressed path to suites.
        config_hash, _ = bc.snapshot_config(self.config)
        snapshot = self.repo / "results" / "configs" / f"{config_hash}.yaml"
        (self.repo / "tasks").mkdir()
        prompt_task = {"id": "offline-task", "prompt_spec": {"user_prompt": "offline"}, "check": {}}
        (self.repo / "tasks" / "sanity.yaml").write_text(yaml.safe_dump({"runner": "prompt", "tasks": [prompt_task]}))
        fixture_task = {"id": "offline-task", "prompt": "offline", "check": {"type": "command"}}
        (self.repo / "tasks" / "kiem_mini.yaml").write_text(yaml.safe_dump({"tasks": [fixture_task]}))
        sentinel = b'{"historical":"never rewrite me"}\n'
        self.log.write_bytes(sentinel)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(prompts, "git_sha", return_value="test-runner"))
            stack.enter_context(mock.patch.object(prompts, "PeakRSSSampler", return_value=SimpleNamespace(start=lambda: SimpleNamespace(stop=lambda: None))))
            stack.enter_context(mock.patch.object(prompts, "run_with_task_deadline", return_value=("{}", "", 0, False)))
            stack.enter_context(mock.patch.object(prompts.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="PASS")))
            stack.enter_context(mock.patch.object(sys, "argv", ["run_prompt_suite.py", "--suite", "sanity", "--base-url", "http://never.invalid/v1", "--model", "test/Flint", "--inference-engine", "mei", "--config", str(snapshot)]))
            prompts.main(_allow_archived_suites=not current)
        after_prompt = self.log.read_bytes()
        self.assertTrue(after_prompt.startswith(sentinel))
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(fixtures, "git_sha", return_value="test-runner"))
            stack.enter_context(mock.patch.object(fixtures, "PeakRSSSampler", return_value=SimpleNamespace(start=lambda: SimpleNamespace(stop=lambda: None))))
            stack.enter_context(mock.patch.object(fixtures, "reset_fixture"))
            stack.enter_context(mock.patch.object(fixtures, "preserve_repository", side_effect=self.no_repository_guard))
            stack.enter_context(mock.patch.object(fixtures, "run_hermes", return_value=("offline transcript", "", 0, 1.0, False)))
            stack.enter_context(mock.patch.object(fixtures, "extract_hermes_session_stats", return_value={}))
            stack.enter_context(mock.patch.object(fixtures, "grade_command", return_value=(True, "PASS", None)))
            stack.enter_context(mock.patch.object(sys, "argv", ["run_fixture_suite.py", "--suite", "kiem_mini", "--hermes-provider", "test", "--hermes-model", "test/Flint", "--inference-engine", "mei", "--config", str(snapshot)]))
            fixtures.main()
        raw = self.log.read_bytes()
        self.assertTrue(raw.startswith(after_prompt))
        rows = [json.loads(line) for line in raw[len(sentinel):].splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertIs(rows[0]["rank_eligible"], False if current else rank_eligible)
        self.assertIs(rows[1]["rank_eligible"], rank_eligible)
        if current:
            self.assertEqual(rows[0]["benchmark_scope"], "model-only-v1")
        self.assertTrue(all("forced_gate" not in row and "exploratory" not in row for row in rows))
        self.assertTrue(all(row["pass"] for row in rows))
        self.assertIn("offline transcript", (self.repo / rows[1]["transcript_path"]).read_text())
        self.assertEqual(rows[0]["config_hash"], rows[1]["config_hash"])


if __name__ == "__main__":
    unittest.main()

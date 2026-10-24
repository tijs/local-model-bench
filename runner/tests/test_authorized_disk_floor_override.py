"""Rank-eligible disk-floor waivers; all work stays offline in scratch repos.

No server, model, real profile, grader or append-only benchmark log is used.
"""
import json
import os
import stat
import sys
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

from runner.tests import test_forced_disk_gate as gates

rb = gates.rb
bc = gates.bc
GIB = gates.GIB
AUTHORIZED = {"disk_floor_override_authorized": True}


class AuthorizedDiskFloorOverrideTests(gates.DiskGateTestCase):
    def setUp(self):
        super().setUp()
        self.write_config(AUTHORIZED)

    def invoke(self, authorized=True, **kwargs):
        kwargs["allow_disk_floor_override"] = authorized
        return super().invoke(**kwargs)

    def test_opt_in_defaults_off_and_config_consent_alone_cannot_bypass_floor(self):
        args = rb.build_arg_parser().parse_args(["--config", str(self.config)])
        self.assertIs(args.allow_disk_floor_override, False)
        self.assertIs(args.force_disk_gate, False)
        self.assertFalse(self.invoke(False))
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())
        self.free_bytes = 10 * GIB
        self.assertTrue(self.invoke(False))
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_cli_requires_literal_config_consent_even_above_floor(self):
        for flags in [{}, *({"disk_floor_override_authorized": value}
                            for value in (None, False, 0, 1, "true", "false", [], {}))]:
            for free_bytes in (9 * GIB, 11 * GIB):
                with self.subTest(flags=flags, free_bytes=free_bytes):
                    self.write_config(flags)
                    self.free_bytes = free_bytes
                    with self.assertRaisesRegex(SystemExit, "disk_floor_override_authorized: true"):
                        self.invoke()
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_opt_in_cannot_turn_diagnostic_or_malformed_rank_flags_into_official_rows(self):
        for key, normal in (("forced_gate", False), ("exploratory", False), ("rank_eligible", True)):
            for value in (None, not normal, int(normal), str(normal).lower()):
                with self.subTest(key=key, value=value):
                    self.write_config({**AUTHORIZED, key: value})
                    with self.assertRaisesRegex(SystemExit, "rank-eligible"):
                        self.invoke()
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_scope_is_local_full_all_stage_only(self):
        for changes, kwargs in (({"raw_port": None}, {}),
                                ({"api_base_url": "https://never.invalid/v1"}, {}),
                                ({"viable": "coding_only"}, {}),
                                ({"viable": "sanity_only"}, {}),
                                ({"viable": "sanity_and_hermes_ops_only"}, {}),
                                ({"viable": "blocked"}, {}),
                                ({}, {"stage": "coding"})):
            with self.subTest(changes=changes, kwargs=kwargs):
                self.write_config({**AUTHORIZED, **changes})
                with self.assertRaisesRegex(SystemExit, "local.*viable: full.*--stage all"):
                    self.invoke(**kwargs)
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_audit_and_exact_snapshot_exist_before_launch_without_any_rank_veto(self):
        original = self.config.read_bytes()

        def verify_before_launch(*_args, **_kwargs):
            entry, = self.audit_rows()
            self.assertEqual(entry["observed_free_bytes"], 9 * GIB)
            self.assertEqual(entry["floor_gib"], 10.0)
            self.assertEqual(entry["floor_bytes"], 10 * GIB)
            self.assertEqual(entry["shortfall_bytes"], GIB)
            self.assertIs(entry["disk_gate_overridden"], True)
            self.assertIs(entry["disk_floor_override_authorized"], True)
            self.assertIs(entry["allow_disk_floor_override"], True)
            self.assertIs(entry["rank_eligible"], True)
            self.assertFalse({"forced_gate", "exploratory", "force_disk_gate"} & entry.keys())
            self.assertEqual(entry["config_path"], "configs/Flint/mei.yaml")
            full_hash = gates.hashlib.sha256(original).hexdigest()
            self.assertEqual(entry["config_hash"], full_hash[:12])
            self.assertEqual(entry["config_sha256"], full_hash)
            self.assertEqual(entry["config_snapshot"], f"results/configs/{full_hash[:12]}.yaml")
            self.assertEqual((self.repo / entry["config_snapshot"]).read_bytes(), original)
            self.assertEqual(entry["runner_git_sha"], "test-runner")
            datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
            self.assertEqual(self.log.read_bytes(), b"\n")
            return mock.Mock()

        self.launch.side_effect = verify_before_launch
        suites = rb.parse_coding_suites(rb.build_arg_parser().parse_args(
            ["--config", str(self.config)]).coding_suites)
        self.assertTrue(rb.run_one(self.config, coding_suites=suites, allow_disk_floor_override=True))
        self.assertEqual([call.args[0][call.args[0].index("--suite") + 1]
                          for call in self.suite_run.call_args_list if "--suite" in call.args[0]],
                         ["sanity", "hermes_ops", "kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"])
        self.health.assert_called_once()
        self.identity.assert_called_once()
        self.completion.assert_called_once()
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(self.suite_run.call_args.args[0],
                         ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_above_floor_and_exact_floor_do_not_claim_an_override(self):
        for free_bytes in (10 * GIB, 11 * GIB):
            with self.subTest(free_bytes=free_bytes):
                self.free_bytes = free_bytes
                self.assertTrue(self.invoke())
                entry = self.audit_rows()[-1]
                self.assertIs(entry["disk_gate_overridden"], False)
                self.assertIs(entry["disk_floor_override_authorized"], True)
                self.assertIs(entry["rank_eligible"], True)
                self.assertEqual(entry["shortfall_bytes"], 0)

    def test_waiver_is_per_invocation_append_only_and_snapshot_is_not_rewritten(self):
        audit = self.repo / "results" / "disk_preflight.jsonl"
        sentinel = b'{"historical":"do not rewrite"}\n'
        audit.write_bytes(sentinel)
        self.assertTrue(self.invoke())
        prefix = audit.read_bytes()
        self.assertTrue(prefix.startswith(sentinel))
        snapshot = self.repo / self.audit_rows()[-1]["config_snapshot"]
        snapshot_stat = snapshot.stat()
        self.assertTrue(self.invoke())
        self.assertTrue(audit.read_bytes().startswith(prefix))
        self.assertEqual(len(self.audit_rows()), 3)
        self.assertEqual(snapshot.stat().st_mtime_ns, snapshot_stat.st_mtime_ns)
        self.assertEqual(snapshot.stat().st_ino, snapshot_stat.st_ino)
        self.launch.reset_mock()
        self.assertFalse(self.invoke(False))
        self.launch.assert_not_called()
        self.assertEqual(len(self.audit_rows()), 3)
        self.assertEqual(self.log.read_bytes(), b"\n")

    def test_config_change_or_corrupt_snapshot_cannot_launch_or_rewrite_evidence(self):
        with mock.patch.object(rb, "clear_kv_cache_dir", side_effect=lambda _cfg: self.write_config()):
            with self.assertRaisesRegex(SystemExit, "config changed"):
                self.invoke()
        self.write_config(AUTHORIZED)
        config_hash, _ = bc.snapshot_config(self.config)
        snapshot = self.repo / "results" / "configs" / f"{config_hash}.yaml"
        snapshot.write_bytes(b"corrupt existing snapshot\n")
        with self.assertRaisesRegex(SystemExit, "snapshot does not match"):
            self.invoke()
        self.assertEqual(snapshot.read_bytes(), b"corrupt existing snapshot\n")
        self.launch.assert_not_called()
        self.assertFalse((self.repo / "results" / "disk_preflight.jsonl").exists())

    def test_mutable_symlink_is_not_an_immutable_snapshot(self):
        config_hash = gates.hashlib.sha256(self.config.read_bytes()).hexdigest()[:12]
        snapshot = self.repo / "results" / "configs" / f"{config_hash}.yaml"
        snapshot.parent.mkdir()
        snapshot.symlink_to(self.config)
        with self.assertRaisesRegex(SystemExit, "symlink"):
            self.invoke()
        self.launch.assert_not_called()
        self.assertTrue(snapshot.is_symlink())

    def test_evidence_write_flush_and_readback_failures_abort_before_launch(self):
        config_hash = gates.hashlib.sha256(self.config.read_bytes()).hexdigest()[:12]
        snapshot = self.repo / "results" / "configs" / f"{config_hash}.yaml"
        audit = self.repo / "results" / "disk_preflight.jsonl"
        for target, mode in ((snapshot, "xb"), (snapshot, "rb"), (audit, "ab"), (audit, "rb")):
            operations = ("open", "write", "short-write", "flush") if mode != "rb" else (
                "open", "read", "mismatch")
            for operation in operations:
                with self.subTest(target=target.name, mode=mode, operation=operation):
                    snapshot.unlink(missing_ok=True)
                    audit.unlink(missing_ok=True)

                    @contextmanager
                    def failing_open(path, actual_mode="r", *args, **kwargs):
                        matches = Path(path) == target and actual_mode == mode
                        if matches and operation == "open":
                            raise OSError("simulated evidence open failure")
                        with self.scratch_open(path, actual_mode, *args, **kwargs) as stream:
                            faulty = mock.Mock(wraps=stream) if matches else stream
                            if matches:
                                if operation in ("read", "write", "flush"):
                                    getattr(faulty, operation).side_effect = OSError("simulated evidence I/O failure")
                                elif operation == "mismatch":
                                    faulty.read.return_value = b"wrong readback"
                                elif operation == "short-write":
                                    faulty.write.return_value = 0
                            yield faulty

                    with mock.patch.object(rb, "open", side_effect=failing_open), \
                            self.assertRaises((OSError, SystemExit)):
                        self.invoke()
                    self.launch.assert_not_called()
                    self.assertEqual(self.suite_run.call_args.args[0],
                                     ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_snapshot_audit_and_directory_fsync_failures_abort_before_launch(self):
        original_fsync = os.fsync
        for target in ("snapshot", "audit", "directory"):
            with self.subTest(target=target):
                def failing_fsync(fd):
                    current = os.fstat(fd)
                    if target == "directory" and stat.S_ISDIR(current.st_mode):
                        raise OSError("simulated directory fsync failure")
                    path = self.repo / "results" / "disk_preflight.jsonl"
                    is_audit = path.exists() and current.st_ino == path.stat().st_ino
                    if stat.S_ISREG(current.st_mode) and (
                            (target == "audit" and is_audit) or (target == "snapshot" and not is_audit)):
                        raise OSError(f"simulated {target} fsync failure")
                    return original_fsync(fd)

                with mock.patch.object(rb.os, "fsync", side_effect=failing_fsync), \
                        self.assertRaisesRegex(OSError, "fsync failure"):
                    self.invoke()
                self.launch.assert_not_called()

    def test_all_suites_and_teardown_retain_admitted_identity_after_authored_config_loss(self):
        for edit in ("delete", "malformed", "different-engine"):
            for outcome in (True, False, RuntimeError("simulated load failure")):
                with self.subTest(edit=edit, outcome=outcome):
                    self.write_config(AUTHORIZED)
                    original = self.config.read_bytes()
                    self.suite_run.reset_mock()

                    def during_load(*_args, **_kwargs):
                        if edit == "delete":
                            self.config.unlink()
                        elif edit == "malformed":
                            self.config.write_text("orchestration: [\n")
                        else:
                            cfg = self.write_config(gates.DIAGNOSTIC)
                            cfg["inference_engine"] = "not-mei"
                            self.config.write_text(yaml.safe_dump(cfg))
                        if isinstance(outcome, Exception):
                            raise outcome
                        return outcome

                    self.health.side_effect = during_load
                    if isinstance(outcome, Exception):
                        with self.assertRaisesRegex(RuntimeError, "simulated load failure"):
                            self.invoke()
                    else:
                        self.assertEqual(bool(self.invoke()), outcome)
                    calls = [call.args[0] for call in self.suite_run.call_args_list
                             if "--config" in call.args[0]]
                    self.assertEqual(len(calls), 3 if outcome is True else 0)
                    for cmd in calls:
                        suite_config = Path(cmd[cmd.index("--config") + 1])
                        self.assertNotEqual(suite_config, self.config)
                        self.assertEqual(suite_config.read_bytes(), original)
                        self.assertIs(bc.config_rank_eligible(yaml.safe_load(suite_config.read_bytes())), True)
                    self.assertEqual(self.suite_run.call_args.args[0],
                                     ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_waiver_preserves_health_identity_completion_proxy_sanity_and_speed_gates(self):
        for failing in (self.health, self.identity, self.completion):
            with self.subTest(gate=failing):
                failing.return_value = False
                self.suite_run.reset_mock()
                self.assertFalse(self.invoke())
                self.assertFalse(self.coding_calls())
                failing.return_value = True
        self.suite_run.reset_mock()
        self.sanity_pass = False
        self.assertFalse(self.invoke())
        self.assertFalse(self.coding_calls())
        self.suite_run.reset_mock()
        self.sanity_pass = True
        self.ops_tps = rb.MIN_HERMES_OPS_TOKENS_PER_SECOND - 1
        self.assertFalse(self.invoke())
        self.assertFalse(self.coding_calls())
        self.assertTrue((self.repo / "results" / "speed_gate.jsonl").exists())
        self.suite_run.reset_mock()
        self.write_config({**AUTHORIZED, "needs_proxy": True, "proxy_parser": "test-parser"})
        self.proxy.return_value = False
        self.assertFalse(self.invoke())
        self.assertFalse(self.coding_calls())

    def test_waiver_preserves_sanity_tool_and_hermes_ops_harness_failure_gates(self):
        for suite, failure in (("sanity", "tool"), ("sanity", "exit"),
                               ("sanity", "missing"), ("sanity", "corrupt"),
                               ("sanity", "harness-error"), ("hermes_ops", "exit"),
                               ("hermes_ops", "missing"), ("hermes_ops", "corrupt"),
                               ("hermes_ops", "unusable"), ("hermes_ops", "harness-error")):
            with self.subTest(suite=suite, failure=failure):
                self.suite_run.reset_mock()

                def broken_suite(cmd, **kwargs):
                    proc = self.fake_suite(cmd, **kwargs)
                    if "--summary-out" not in cmd or cmd[cmd.index("--suite") + 1] != suite:
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
                        if failure == "tool":
                            rows[1]["pass"] = False
                        elif failure == "unusable":
                            rows[0]["tokens_per_second"] = True
                        else:
                            rows[0]["harness_error"] = True
                        summary.write_text(json.dumps(rows))
                    return proc

                self.suite_run.side_effect = broken_suite
                self.assertFalse(self.invoke())
                self.assertFalse(self.coding_calls())
                self.assertFalse((self.repo / "results" / "speed_gate.jsonl").exists())
                self.assertEqual(self.suite_run.call_args.args[0],
                                 ["bash", str(self.repo / "runner" / "stop_mei_server.sh")])

    def test_cli_forwards_waiver_with_default_full_battery(self):
        with mock.patch.object(sys, "argv", ["run_bench.py", "--config", str(self.config),
                                            "--allow-disk-floor-override"]), \
                mock.patch.object(rb, "run_one", return_value=True) as run_one, \
                mock.patch.object(rb, "sweep_stale_run_dirs"):
            rb.main()
        self.assertIs(run_one.call_args.kwargs["allow_disk_floor_override"], True)
        self.assertIs(run_one.call_args.kwargs["force_disk_gate"], False)
        self.assertEqual(run_one.call_args.kwargs["stage"], "all")
        self.assertEqual(run_one.call_args.kwargs["coding_suites"],
                         ["kiem_mini", "hearth_mini", "kipclip_mini", "hearth_full"])

    def test_cli_rejects_sweeps_coding_only_and_mixed_modes_before_side_effects(self):
        for args in (["--all"], ["--config", str(self.config), "--stage", "coding"],
                     ["--config", str(self.config), "--force-disk-gate"]):
            with self.subTest(args=args), \
                    mock.patch.object(sys, "argv", ["run_bench.py", *args, "--allow-disk-floor-override"]), \
                    mock.patch.object(rb, "run_one") as run_one, \
                    mock.patch.object(rb, "sweep_stale_run_dirs") as sweep:
                with self.assertRaises(SystemExit):
                    rb.main()
                run_one.assert_not_called()
                sweep.assert_not_called()
        with self.assertRaisesRegex(SystemExit, "mutually exclusive"):
            self.invoke(force_disk_gate=True)
        with self.assertRaises(SystemExit):
            self.invoke(1)
        self.launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Offline LFM2.5 config/launcher/profile gates. No inference or profile writes.

All external launch/health/suite calls in orchestration tests are explicit mocks;
mocked passing summaries are test fixtures, never saved as benchmark results.
"""
import contextlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench_common as bc
import run_bench as rb
import run_fixture_suite as rfs

REPO = Path(__file__).resolve().parents[2]
LANE = REPO / "configs" / "LiquidAI-LFM2.5-24B-A2B-MLX-4bit"
CONFIG = LANE / "mei.yaml"
EXPECTED_COUNTS = {"sanity": 2, "hermes_ops": 8, "kiem_mini": 5,
                   "hearth_mini": 3, "kipclip_mini": 4, "hearth_full": 3}


class LFM25ConfigTests(unittest.TestCase):
    def setUp(self):
        self.cfg = yaml.safe_load(CONFIG.read_text())

    def test_official_revisions_and_vendor_contract_are_preserved(self):
        c = self.cfg
        self.assertEqual(c["source_model_revision"], "1769516ac588c4c558089c94f27d96b0dc67b183")
        self.assertEqual(c["source_revision"], "667408d494bde191c2cb9dd4f4549827816b9275")
        self.assertEqual(c["context_cap"], 65536)
        self.assertEqual(c["hermes_ops_max_tokens"], 4096)
        self.assertEqual(c["prefill_step_size"], 64)
        self.assertEqual(c["generation_profiles"]["vendor"], {
            "temperature": 0.1, "top_k": 50, "top_p": 0.0, "min_p": 0,
            "repetition_penalty": 1.05})
        self.assertEqual(c["hermes_ops_generation_profile"], "vendor")
        self.assertNotIn("coding_reasoning_effort", c)
        argv = shlex.split(c["benchmark_launch_command"].replace("\\\n", " "))
        for flag, value in {"--temperature": "0.1", "--top-k": "50", "--top-p": "0",
                            "--repetition-penalty": "1.05", "--max-tokens": "4096",
                            "--context-cap": "65536", "--port": "8029",
                            "--model-profile": "lfm2.5-24b-a2b"}.items():
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(argv[argv.index("--vmlx-revision") + 1], c["mei_commit"])
        self.assertRegex(c["mei_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(c["mei_source_commit"], r"^[0-9a-f]{40}$")
        self.assertNotEqual(c["mei_commit"], "633fe166630ef04310aea7d5a1795555ab32970d")

    def test_non_null_profile_provider_template_targets_exact_endpoint_and_sampler(self):
        c = self.cfg
        orch = c["orchestration"]
        template = yaml.safe_load((LANE / "hermes-profile.example.yaml").read_text())
        self.assertEqual(orch["hermes_profile"], "bench-lfm25")
        self.assertEqual(orch["hermes_provider"], "lfm25-mei")
        self.assertEqual(orch["viable"], "full")
        self.assertEqual(orch["raw_port"], 8029)
        self.assertEqual(template["model"]["provider"], orch["hermes_provider"])
        provider = template["providers"][orch["hermes_provider"]]
        self.assertEqual(provider["api"], c["benchmark_endpoint"])
        self.assertEqual(provider["transport"], "chat_completions")
        self.assertEqual(template["model"]["base_url"], provider["api"])
        self.assertEqual(template["model"]["api_mode"], provider["transport"])
        self.assertEqual(provider["default_model"], orch["served_model_id"])
        self.assertEqual(provider["context_length"], c["context_cap"])
        self.assertEqual(template["model"]["context_length"], c["context_cap"])
        self.assertEqual(provider["extra_body"], {
            **c["generation_profiles"]["vendor"], "max_tokens": 4096,
            "reasoning_effort": None})
        self.assertNotIn("api_key", provider)
        self.assertEqual(template["terminal"]["cwd"], ".")

    def test_default_cli_inventory_has_all_25_tasks(self):
        args = rb.build_arg_parser().parse_args(["--config", str(CONFIG)])
        coding_suites = rb.parse_coding_suites(args.coding_suites)
        assert coding_suites is not None
        suites = ["sanity", "hermes_ops", *coding_suites]
        counts = {s: len(yaml.safe_load((REPO / "tasks" / (s + ".yaml")).read_text())["tasks"])
                  for s in suites}
        self.assertEqual(counts, EXPECTED_COUNTS)
        self.assertEqual(sum(counts.values()), 25)

    def test_all_suites_receive_profile_provider_and_no_shared_reset(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if "--summary-out" in cmd:
                suite = cmd[cmd.index("--suite") + 1]
                path = Path(cmd[cmd.index("--summary-out") + 1])
                # Explicitly mocked success/speed fixture: no result log writes.
                rows = [{"task_id": "sanity-basic", "pass": True},
                        {"task_id": "sanity-tool", "pass": True}] if suite == "sanity" else [
                            {"task_id": "offline-fixture", "tokens_per_second": 10.0}]
                path.write_text(json.dumps(rows))
            return subprocess.CompletedProcess(cmd, 0)

        args = rb.build_arg_parser().parse_args(["--config", str(CONFIG)])
        with mock.patch.object(rb, "run", side_effect=fake_run), \
                mock.patch.object(rb.subprocess, "Popen") as launch, \
                mock.patch.object(rb, "wait_for_health", return_value=True), \
                mock.patch.object(rb, "assert_serving_expected_model", return_value=True), \
                mock.patch.object(rb, "assert_plain_completion", return_value=True), \
                mock.patch.object(rb, "clear_kv_cache_dir"), \
                mock.patch.object(rb, "_leaderboard"), \
                mock.patch("builtins.open", mock.mock_open()), \
                contextlib.redirect_stdout(io.StringIO()):
            result = rb._run_one_impl(CONFIG, coding_suites=rb.parse_coding_suites(args.coding_suites))
        self.assertTrue(result)
        launch.assert_called_once()  # mocked: no real server launch
        self.assertFalse(any("reset_bench_profile.sh" in str(cmd) for cmd in calls))
        suites = [cmd[cmd.index("--suite") + 1] for cmd in calls if "--suite" in cmd]
        self.assertEqual(suites, list(EXPECTED_COUNTS))
        fixture_calls = [cmd for cmd in calls if any(str(x).endswith("run_fixture_suite.py") for x in cmd)]
        self.assertEqual(len(fixture_calls), 4)
        for cmd in fixture_calls:
            self.assertEqual(cmd[cmd.index("--hermes-profile") + 1], "bench-lfm25")
            self.assertEqual(cmd[cmd.index("--hermes-provider") + 1], "lfm25-mei")
            self.assertEqual(cmd[cmd.index("--hermes-model") + 1], self.cfg["model"])
            self.assertNotIn("--only-task", cmd)


class HermesProfileForwardingTests(unittest.TestCase):
    def test_chat_default_and_explicit_profile_provider_are_exact(self):
        for profile in (None, "bench-lfm25"):
            with self.subTest(profile=profile):
                proc = mock.Mock(returncode=0)
                proc.communicate.return_value = ("", "")
                with mock.patch.object(rfs, "sandbox_wrapped_command", side_effect=lambda cmd, cwd: (cmd, False)), \
                        mock.patch.object(rfs.subprocess, "Popen", return_value=proc) as popen:
                    kwargs = {} if profile is None else {"hermes_profile": profile}
                    rfs.run_hermes("offline prompt", REPO, "lfm25-mei", "model", 40, 30, **kwargs)
                cmd = popen.call_args.args[0]
                self.assertEqual(cmd[cmd.index("--profile") + 1], profile or "bench")
                self.assertEqual(cmd[cmd.index("--provider") + 1], "lfm25-mei")

    def test_session_export_uses_same_selected_profile(self):
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps({"messages": [], "api_call_count": 2}))
        with mock.patch.object(rfs.subprocess, "run", return_value=result) as export:
            stats = rfs.extract_hermes_session_stats("", "session_id: offline-id\n", hermes_profile="bench-lfm25")
        self.assertEqual(stats["hermes_turns"], 2)
        cmd = export.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--profile") + 1], "bench-lfm25")

    def test_profile_selection_rejects_default_paths_null_and_empty(self):
        self.assertEqual(bc.resolve_hermes_profile(), "bench")
        for value in ("default", None, "", "../bench", "/absolute", "a b", "--profile"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bc.resolve_hermes_profile(value)

    def test_fixture_cli_overrides_config_and_config_overrides_bench_default(self):
        with tempfile.TemporaryDirectory(prefix="lfm25-fixture-profile-") as td:
            root = Path(td)
            (root / "tasks").mkdir()
            (root / "tasks" / "offline.yaml").write_text("tasks: []\n")
            cfg = root / "config.yaml"
            for orch, override, expected in (({}, None, "bench"),
                                               ({"hermes_profile": "bench-lfm25"}, None, "bench-lfm25"),
                                               ({"hermes_profile": "bench-lfm25"}, "bench-other", "bench-other")):
                cfg.write_text(yaml.safe_dump({"orchestration": orch}))
                argv = ["run_fixture_suite.py", "--suite", "offline", "--hermes-provider", "p",
                        "--hermes-model", "m", "--inference-engine", "fake", "--config", str(cfg)]
                if override:
                    argv += ["--hermes-profile", override]
                with mock.patch.object(rfs, "REPO", root), \
                        mock.patch.object(rfs, "snapshot_config", return_value=("hash", "cfg")), \
                        mock.patch.object(rfs, "resolve_hermes_profile", wraps=bc.resolve_hermes_profile) as resolve, \
                        mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    rfs.main()
                resolve.assert_called_once_with(expected)


if __name__ == "__main__":
    unittest.main()

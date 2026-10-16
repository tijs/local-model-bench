"""Offline LFM2.5 config/launcher/profile gates. No inference or profile writes.

All external launch/health/suite calls in orchestration tests are explicit mocks;
mocked passing summaries are test fixtures, never saved as benchmark results.
"""
import contextlib
import hashlib
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
import run_mei_acceptance as acceptance

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
        self.assertEqual(c["prefill_step_size"], 1024)
        self.assertEqual(c["memory_limit_bytes"], 32000000000)
        self.assertIs(type(c["fused_gate_up_cache_limit_bytes"]), int)
        self.assertEqual(c["fused_gate_up_cache_limit_bytes"], 0)
        self.assertEqual(c["runtime_tuning_status"], "experimental-unmeasured")
        self.assertEqual(c["generation_profiles"]["vendor"], {
            "temperature": 0.1, "top_k": 50, "top_p": 0.0, "min_p": 0,
            "repetition_penalty": 1.05})
        self.assertEqual(c["hermes_ops_generation_profile"], "vendor")
        self.assertNotIn("coding_reasoning_effort", c)
        argv = shlex.split(c["benchmark_launch_command"].replace("\\\n", " "))
        for flag, value in {"--temperature": "0.1", "--top-k": "50", "--top-p": "0",
                            "--repetition-penalty": "1.05", "--max-tokens": "4096",
                            "--context-cap": "65536", "--port": "8029",
                            "--model-profile": "lfm2.5-24b-a2b",
                            "--prefill-step-size": str(c["prefill_step_size"]),
                            "--memory-limit-bytes": str(c["memory_limit_bytes"]),
                            "--fused-gate-up-cache-limit-bytes": "0",
                            "--cache-reuse": "true", "--max-cache-blocks": "4097", "--min-p": "0",
                            "--load-mmap": "false"}.items():
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(argv[argv.index("--vmlx-revision") + 1], c["mei_commit"])
        self.assertRegex(c["mei_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(c["mei_source_commit"], r"^[0-9a-f]{40}$")
        self.assertNotEqual(c["mei_commit"], "633fe166630ef04310aea7d5a1795555ab32970d")

    def test_dedicated_runtime_matches_launch_and_both_runner_stop_contracts(self):
        c = self.cfg
        runtime = "/Users/tijs/.local/share/local-model-bench/mei-runtime-lfm25"
        self.assertEqual(c["mei_runtime_base"], runtime)
        argv = acceptance.split_launch_command(c["benchmark_launch_command"])
        self.assertEqual(argv.count("--runtime-base"), 1)
        self.assertEqual(argv[argv.index("--runtime-base") + 1], runtime)
        self.assertEqual(bc.mei_stop_command(c, REPO), [
            "bash", str(REPO / "runner" / "stop_mei_server.sh"), "--runtime-base", runtime])
        # The acceptance launcher uses direct argv, not a shell. Literal
        # absolute paths must identify the same model/build as run_bench.
        for flag, expected in {
            "--model-dir": "/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-MLX-4bit",
            "--build-dir": "/Users/tijs/projects/mei-lfm25/.build",
            "--mei-repo": "/Users/tijs/projects/mei-lfm25",
            "--vmlx-repo": "/Users/tijs/projects/vmlx-swift-lfm25",
        }.items():
            self.assertEqual(argv[argv.index(flag) + 1], expected)
        self.assertNotIn("$", c["benchmark_launch_command"])

    def test_connect_watchdog_override_is_explicit_and_changes_attempt_identity(self):
        self.assertEqual(self.cfg["hermes_ops_connect_timeout"], 300)
        self.assertIs(type(self.cfg["hermes_ops_connect_timeout"]), int)
        self.assertNotEqual(hashlib.sha256(CONFIG.read_bytes()).hexdigest()[:12],
                            "0fb346ed9077")
        setting = next(s for s in self.cfg["settings"]
                       if s["name"] == "hermes_ops_connect_timeout")
        self.assertIn("runner/run_prompt.py", setting["source"])
        self.assertIn("0fb346ed9077", setting["source"])
        self.assertIn("142.058s", setting["value"])
        self.assertIn("full recovery remains unverified", setting["value"])

    def test_runtime_candidate_is_unmeasured_and_distinct_from_prior_attempts(self):
        self.assertIs(type(self.cfg["prefill_step_size"]), int)
        self.assertIs(type(self.cfg["memory_limit_bytes"]), int)
        current_hash = hashlib.sha256(CONFIG.read_bytes()).hexdigest()[:12]
        self.assertNotIn(current_hash, ("0fb346ed9077", "a4be8e840181", "e4f67e0554e2",
                                       "137b34e01f9f", "3b818db1c96a", "e95f694ede91", "63f2b2fa27ff"))
        settings = {s["name"]: s for s in self.cfg["settings"]}
        for name in ("prefill_chunking", "memory_limit"):
            with self.subTest(setting=name):
                self.assertIn("EXPERIMENTAL/UNMEASURED", settings[name]["value"])
                self.assertIn("a4be8e840181", settings[name]["value"])
        self.assertIn("--prefill-step-size 1024", settings["prefill_chunking"]["value"])
        self.assertIn("3b818db1c96a", settings["prefill_chunking"]["value"])
        self.assertIn("peak scratch", settings["prefill_chunking"]["value"])
        self.assertIn("ModelTuning.swift", settings["prefill_chunking"]["source"])
        self.assertIn("32000000000", settings["memory_limit"]["value"])
        self.assertIn("28.712 GiB", settings["memory_limit"]["value"])
        self.assertIn("not proven safe or optimal", settings["memory_limit"]["value"])
        self.assertIn("Engine.swift", settings["memory_limit"]["source"])
        self.assertIn("docs/BENCHMARKING.md", settings["memory_limit"]["source"])

    def test_fused_cache_candidate_is_explicit_child_only_and_unmeasured(self):
        setting = next(s for s in self.cfg["settings"]
                       if s["name"] == "fused_gate_up_cache_limit")
        self.assertIn("EXPERIMENTAL/UNMEASURED", setting["value"])
        self.assertIn("VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0", setting["value"])
        self.assertIn("e4f67e0554e2", setting["value"])
        self.assertIn("512 MiB per layer", setting["value"])
        self.assertIn("SwitchLayers.swift", setting["source"])
        self.assertIn("LFM2MoE.swift", setting["source"])
        argv = acceptance.split_launch_command(self.cfg["benchmark_launch_command"])
        self.assertEqual(argv[:2], ["bash", "runner/start_mei_server.sh"])
        self.assertEqual(argv.count("--fused-gate-up-cache-limit-bytes"), 1)
        # The wrapper, not an outer shell/global export, owns the assignment.
        self.assertNotIn("VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0", argv)

    def test_candidate4_enables_only_bounded_paged_prefix_reuse(self):
        argv = acceptance.split_launch_command(self.cfg["benchmark_launch_command"])
        self.assertEqual(argv.count("--cache-reuse"), 1)
        self.assertEqual(argv[argv.index("--cache-reuse") + 1], "true")
        self.assertEqual(argv.count("--max-cache-blocks"), 1)
        self.assertEqual(argv[argv.index("--max-cache-blocks") + 1], "4097")
        self.assertIs(type(self.cfg["max_cache_blocks"]), int)
        self.assertEqual(self.cfg["max_cache_blocks"], 4097)
        self.assertEqual(argv[argv.index("--fused-gate-up-cache-limit-bytes") + 1], "0")
        for flag in ("--cache-limit-bytes", "--kv-cache-dir", "--kv-bits",
                     "--ssm-anchor-boundaries"):
            self.assertNotIn(flag, argv)
        setting = next(s for s in self.cfg["settings"] if s["name"] == "kv_cache")
        for text in ("EXPERIMENTAL/UNMEASURED", "137b34e01f9f", "--cache-reuse true",
                     "--max-cache-blocks 4097", "65536", "includes one null sentinel", "not per-generation",
                     "much slower", "no --skip-cache"):
            self.assertIn(text, setting["value"])
        self.assertIn("Engine.swift", setting["source"])
        self.assertIn("ServerConfig.swift", setting["source"])

    def test_tracked_staging_provenance_pins_integrity_not_loadability(self):
        c = self.cfg
        p = json.loads((REPO / c["staging_provenance"]).read_text())
        self.assertEqual(c["staging_status"], "staged-complete-loadability-pending")
        self.assertEqual(p["status"], c["staging_status"])
        self.assertEqual(p["repo"], c["model"])
        self.assertEqual(p["revision"], c["source_revision"])
        self.assertEqual(p["source_model_revision"], c["source_model_revision"])
        self.assertEqual(p["target"],
                         "/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-MLX-4bit")
        v = p["verification"]
        self.assertIs(v["passed"], True)
        self.assertEqual(v["reasons"], [])
        self.assertEqual(v["shard_count"], 3)
        self.assertEqual(v["file_bytes"], 13567294335)
        self.assertEqual(v["file_bytes"], c["model_bytes"])
        self.assertEqual(v["expected_weight_bytes"], c["model_bytes"])
        self.assertEqual(v["payload_bytes"], 13567188992)
        self.assertEqual(v["index_bytes"], v["payload_bytes"])
        self.assertEqual(v["header_overhead_bytes"], 105343)
        self.assertEqual(v["file_bytes"] - v["payload_bytes"], v["header_overhead_bytes"])
        self.assertEqual(p["model"], {
            "architecture": "Lfm2MoeForCausalLM", "model_type": "lfm2_moe",
            "quantization": {"bits": 4, "group_size": 64, "mode": "affine"},
            "config_sha256": "4901707c3cef43e3cf68a0dedc3e39687de43413cab30578a32c63c643984244"})
        shards = p["weight_shards"]
        self.assertEqual([(s["path"], s["bytes"], s["sha256"]) for s in shards], [
            ("model-00001-of-00003.safetensors", 5318453801,
             "17e953456c62314a498f1ef5ee8a5f1b51ac83f6b6bb684f160dde4f92cd11c0"),
            ("model-00002-of-00003.safetensors", 5344895125,
             "c3ae09dba31b3786c325425435021cf5d5bf06c1a79acb31a741e15a47e5bb14"),
            ("model-00003-of-00003.safetensors", 2903945409,
             "9814144af5045ea8c96e2f1352148fdbe9f8a0085b76df6d6760efbe916e9840")])
        self.assertTrue(all(s["remote_lfs_sha256_match"] is True for s in shards))
        self.assertEqual(sum(s["bytes"] for s in shards), v["file_bytes"])
        files = [*shards, *p["other_files"]]
        self.assertEqual(len(files), 12)
        self.assertEqual(len({f["path"] for f in files}), 12)
        self.assertEqual(sum(f["bytes"] for f in files), 13585304293)
        for f in files:
            self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
        self.assertIs(p["remote_metadata_check"]["verified"], True)
        self.assertTrue(p["loadability"].startswith("PENDING:"))

    def test_read_only_alignment_audit_requires_no_mmap_and_preserves_official_artifact(self):
        p = json.loads((REPO / self.cfg["staging_provenance"]).read_text())
        audit = p["alignment_audit"]
        self.assertIs(audit["read_only"], True)
        self.assertIs(audit["original_files_repacked"], False)
        self.assertEqual(audit["target"], p["target"])
        self.assertEqual(audit["shards"], [
            {"path": "model-00001-of-00003.safetensors", "data_start": 43049,
             "tensors": 358, "unaligned_tensors": 358, "unaligned_bytes": 5318410752},
            {"path": "model-00002-of-00003.safetensors", "data_start": 40341,
             "tensors": 331, "unaligned_tensors": 331, "unaligned_bytes": 5344854784},
            {"path": "model-00003-of-00003.safetensors", "data_start": 21953,
             "tensors": 181, "unaligned_tensors": 181, "unaligned_bytes": 2903923456}])
        self.assertEqual(audit["total_tensors"], 870)
        self.assertEqual(sum(s["tensors"] for s in audit["shards"]), audit["total_tensors"])
        self.assertEqual(audit["unaligned_tensors"], audit["total_tensors"])
        self.assertEqual(sum(s["unaligned_bytes"] for s in audit["shards"]), audit["unaligned_bytes"])
        self.assertEqual(audit["unaligned_bytes"], p["verification"]["payload_bytes"])
        self.assertIs(audit["memory_safety_setting"]["load_mmap"], False)
        self.assertEqual(audit["memory_safety_setting"]["launch_flag"], "--load-mmap false")
        argv = acceptance.split_launch_command(self.cfg["benchmark_launch_command"])
        self.assertEqual(argv.count("--load-mmap"), 1)
        self.assertEqual(argv[argv.index("--load-mmap") + 1], "false")
        self.assertEqual(argv[argv.index("--model-dir") + 1], p["target"])
        self.assertNotIn("align_safetensors", self.cfg["benchmark_launch_command"])

    def test_sustained_preload_gate_preserves_raw_evidence_but_requires_fresh_recheck(self):
        p = json.loads((REPO / self.cfg["staging_provenance"]).read_text())
        gate = p["pre_load_memory_gate"]
        raw = (REPO / gate["evidence"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), gate["evidence_sha256"])
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        self.assertEqual(len(rows), 11)
        self.assertEqual(gate["sample_count"], len(rows))
        self.assertEqual([r["sample"] for r in rows], list(range(1, 12)))
        self.assertEqual(rows[0]["at_utc"], gate["started_at_utc"])
        self.assertEqual(rows[-1]["at_utc"], gate["finished_at_utc"])
        self.assertEqual(gate["reclaimable_floor_gib"], 10)
        self.assertEqual(min(r["reclaimable_gib"] for r in rows), 21.151)
        self.assertEqual(max(r["reclaimable_gib"] for r in rows), 21.546)
        self.assertEqual(gate["reclaimable_min_gib"], 21.151)
        self.assertEqual(gate["reclaimable_max_gib"], 21.546)
        self.assertEqual(gate["physical_bytes"], 34359738368)
        for row in rows:
            self.assertEqual(round((row["free_pages"] + row["inactive_pages"])
                                   * row["page_bytes"] / 1024 ** 3, 3), row["reclaimable_gib"])
            self.assertGreaterEqual(row["reclaimable_gib"], gate["reclaimable_floor_gib"])
            self.assertEqual(row["physical_bytes"], gate["physical_bytes"])
            self.assertEqual(row["inference_owners"], [])
            self.assertEqual(row["port_8029_listener"], "")
            self.assertIn("used = 0.00M", row["swap"])
        self.assertIs(gate["passed"], True)
        self.assertEqual(gate["swap_used_bytes_all_samples"], 0)
        self.assertIs(gate["no_inference_owners_all_samples"], True)
        self.assertIs(gate["port_free_all_samples"], True)
        self.assertEqual(gate["port"], 8029)
        self.assertIs(gate["recheck_required_immediately_before_launch"], True)
        self.assertIs(gate["model_loaded"], False)

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
        self.assertEqual(template["model"]["default"], orch["served_model_id"])
        self.assertEqual(provider["default_model"], orch["served_model_id"])
        self.assertEqual(provider["context_length"], c["context_cap"])
        self.assertEqual(template["model"]["context_length"], c["context_cap"])
        self.assertIs(provider["discover_models"], False)
        self.assertEqual(provider["extra_body"], {
            **c["generation_profiles"]["vendor"], "max_tokens": 4096,
            "reasoning_effort": None})
        self.assertNotIn("api_key", provider)

    def test_profile_template_pins_benchmark_cli_policy(self):
        # Read the repository template only, never an installed profile.
        template = yaml.safe_load((LANE / "hermes-profile.example.yaml").read_text())
        self.assertEqual(template["agent"]["max_turns"], 40)
        # YAML 1.1 parses bare off as False; the mode must remain a string.
        self.assertEqual(template["approvals"]["mode"], "off")
        self.assertEqual(template["platform_toolsets"]["cli"], [
            "clarify", "code_execution", "connections", "file", "terminal", "todo"])
        self.assertEqual(template["skills"]["external_dirs"], [
            "/Users/tijs/.hermes/skills", "/Users/tijs/.hermes/shared-skills"])
        self.assertEqual(template["plugins"]["enabled"], [])
        self.assertEqual(template["model"]["max_tokens"], 4096)
        self.assertEqual(template["model"]["max_tokens"],
                         template["providers"]["lfm25-mei"]["extra_body"]["max_tokens"])
        self.assertEqual(template["terminal"]["cwd"], ".")
        self.assertIs(template["memory"]["memory_enabled"], False)
        self.assertIs(template["memory"]["user_profile_enabled"], False)

    def test_readme_provisioning_arguments_cover_every_template_leaf(self):
        # Parse documentation only: do NOT execute Hermes or write profile state.
        template = yaml.safe_load((LANE / "hermes-profile.example.yaml").read_text())
        commands = [shlex.split(line, comments=True)
                    for line in (LANE / "README.md").read_text().splitlines()
                    if line.startswith("hermes ")]
        self.assertIn(["hermes", "profile", "create", "bench-lfm25"], commands)
        self.assertFalse(any("--clone" in arg or arg == "use"
                             for cmd in commands for arg in cmd))
        settings = {}
        for cmd in commands:
            if cmd == ["hermes", "profile", "create", "bench-lfm25"]:
                continue
            self.assertEqual(cmd[:4], ["hermes", "--profile", "bench-lfm25", "config"])
            if cmd[4] == "set":
                self.assertEqual(len(cmd), 7, cmd)
                key, value = cmd[5:]
                self.assertNotIn(key, settings, f"duplicate provisioning key: {key}")
                settings[key] = value

        def leaves(mapping, prefix=""):
            for key, value in mapping.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    yield from leaves(value, path)
                else:
                    yield path, value

        expected = dict(leaves(template))
        self.assertEqual(settings.keys(), expected.keys())
        for key, value in expected.items():
            with self.subTest(key=key):
                # The recipe uses JSON syntax for non-string arguments, with
                # lists shell-quoted as ONE argv value. This is a docs/template
                # consistency gate, not an emulation of Hermes's config loader.
                actual = settings[key] if isinstance(value, str) else json.loads(settings[key])
                self.assertEqual(actual, value)
        self.assertIn(["hermes", "--profile", "bench-lfm25", "config", "check"], commands)

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
        launch_argv = acceptance.split_launch_command(launch.call_args.args[0])
        self.assertEqual(launch_argv[launch_argv.index("--cache-reuse") + 1], "true")
        self.assertEqual(launch_argv[launch_argv.index("--max-cache-blocks") + 1], "4097")
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
            self.assertNotIn("--connect-timeout", cmd)


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

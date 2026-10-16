"""Model-free community OptiQ contract; no real models, services or endpoints.

Only metadata-only dry-run fixtures and explicitly mocked orchestration run.
The immutable cache-off config is the execution baseline, not the cache-on arm.
"""
from collections import Counter
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_common as bc
import run_mei_acceptance as acceptance
import test_start_mei_server_sh as launches
import test_run_prompt_suite as prompts

REPO = Path(__file__).resolve().parents[2]
BASE = "83d06b3978210b850c42e61e09d28c240a86d7e5"
PREDECESSOR = launches.CACHE_OFF_REVALIDATION_CONFIG_PATH
CONFIG = REPO / launches.OPTIQ_CONFIG_PATH
LANE = CONFIG.parent
MODEL = "mlx-community/LFM2.5-24B-A2B-OptiQ-4bit"
OLD_MODEL = "LiquidAI/LFM2.5-24B-A2B-MLX-4bit"
MODEL_DIR = "/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-OptiQ-4bit"
OLD_MODEL_DIR = "/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-MLX-4bit"
REVISION = "b5552f7f7e597e2ca02653f89098dea86b8818af"
MEI = "faf48a331b6bede352c334e0c6e3d4d4d7e10372"
VMLX = "22969e9555b5e86df862e43e3d7356575d3dd053"


def base_file(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=REPO)


class LFM25OptiQConfigTests(unittest.TestCase):
    def setUp(self):
        self.cfg = yaml.safe_load(CONFIG.read_text())
        self.raw_predecessor = base_file(PREDECESSOR)
        self.assertEqual(hashlib.sha256(self.raw_predecessor).hexdigest(),
                         "e6be308f5709d4a0ef3a49cc158b50d44bd9c2047a8a47594873c038c3f1babb")
        self.predecessor = yaml.safe_load(self.raw_predecessor)

    def test_complete_parsed_execution_contract_and_raw_command_match_cache_off(self):
        # Enumerate ONLY documentary/quant identity fields. Any new execution
        # field, omission or mutation must fail this whole-mapping comparison.
        identity = {"model", "source_revision", "source_model", "source_model_revision",
                    "model_bytes", "staging_status", "staging_provenance", "source_provenance",
                    "quant_family", "settings", "known_gaps"}
        separately_checked = {"benchmark_launch_command", "orchestration"}
        omit = identity | separately_checked
        self.assertEqual({k: v for k, v in self.cfg.items() if k not in omit},
                         {k: v for k, v in self.predecessor.items() if k not in omit})
        self.assertEqual(self.cfg["model"], MODEL)
        self.assertEqual(self.cfg["orchestration"],
                         {**self.predecessor["orchestration"], "served_model_id": MODEL})
        expected = self.predecessor["benchmark_launch_command"].replace(
            OLD_MODEL_DIR, MODEL_DIR).replace(OLD_MODEL, MODEL)
        self.assertEqual(self.cfg["benchmark_launch_command"], expected)
        self.assertEqual(acceptance.split_launch_command(self.cfg["benchmark_launch_command"]), [
            "bash", "runner/start_mei_server.sh", "--model-dir", MODEL_DIR,
            "--served-model-id", MODEL, "--port", "8029", "--context-cap", "65536",
            "--max-tokens", "4096", "--temperature", "0.1", "--top-p", "0",
            "--top-k", "50", "--min-p", "0", "--repetition-penalty", "1.05",
            "--emit-reasoning", "true", "--cache-reuse", "false",
            "--model-profile", "lfm2.5-24b-a2b", "--prefill-step-size", "1024",
            "--memory-limit-bytes", "32000000000", "--fused-gate-up-cache-limit-bytes", "0",
            "--load-mmap", "false", "--runtime-base",
            "/Users/tijs/.local/share/local-model-bench/mei-runtime-lfm25",
            "--build-dir", "/Users/tijs/projects/mei-lfm25/.build",
            "--mei-repo", "/Users/tijs/projects/mei-lfm25",
            "--vmlx-repo", "/Users/tijs/projects/vmlx-swift-lfm25", "--vmlx-revision", VMLX,
        ])
        for field, value in {"prefill_step_size": 1024, "memory_limit_bytes": 32000000000,
                             "fused_gate_up_cache_limit_bytes": 0, "context_cap": 65536,
                             "hermes_ops_max_tokens": 4096, "hermes_ops_connect_timeout": 300}.items():
            self.assertIs(type(self.cfg[field]), int)
            self.assertEqual(self.cfg[field], value)
        self.assertEqual(self.cfg["mei_source_commit"], MEI)
        self.assertEqual(self.cfg["mei_commit"], VMLX)
        self.assertNotIn("max_cache_blocks", self.cfg)
        self.assertNotIn("coding_reasoning_effort", self.cfg)
        self.assertEqual(self.cfg["generation_profiles"], {"vendor": {
            "temperature": 0.1, "top_p": 0.0, "top_k": 50,
            "min_p": 0, "repetition_penalty": 1.05}})
        self.assertEqual(self.cfg["hermes_ops_generation_profile"], "vendor")
        self.assertEqual(bc.mei_stop_command(self.cfg, REPO),
                         bc.mei_stop_command(self.predecessor, REPO))

    def test_full_emitted_argv_and_only_identity_delta_with_metadata_fixtures(self):
        fixture = launches.MeiConfigDryRunTests()
        self.addCleanup(fixture.doCleanups)
        res, paths = fixture._config_dry_run(self.cfg)
        self.assertEqual(launches._launch_argv(res), [
            "env", "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0",
            str(Path(paths["--build-dir"]) / "release/mei"),
            "--model-dir", paths["--model-dir"], "--served-model-id", MODEL,
            "--host", "127.0.0.1", "--port", "8029", "--context-cap", "65536",
            "--temperature", "0.1", "--top-p", "0", "--top-k", "50",
            "--emit-reasoning", "true", "--cache-reuse", "false",
            "--max-tokens", "4096", "--prefill-step-size", "1024",
            "--min-p", "0", "--repetition-penalty", "1.05",
            "--model-profile", "lfm2.5-24b-a2b", "--memory-limit-bytes", "32000000000",
            "--load-mmap", "false",
        ])
        self.assertNotIn("--max-cache-blocks", launches._launch_argv(res))
        self.assertIn(f"--revision {VMLX} --build-dir {paths['--build-dir']} --dry-run", res.stdout)
        old, old_paths = fixture._config_dry_run(self.predecessor)
        def fixture_normalized(result, fixture_paths):
            argv = launches._launch_argv(result)
            for flag, value in fixture_paths.items():
                argv = [token.replace(value, "{" + flag + "}") for token in argv]
            return argv
        argv = fixture_normalized(res, paths)
        argv[argv.index("--served-model-id") + 1] = OLD_MODEL
        self.assertEqual(argv, fixture_normalized(old, old_paths))

    def test_all_baseline_configs_are_byte_identical_and_only_four_named_files_added(self):
        files = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "--", "configs"],
            cwd=REPO, text=True).splitlines()
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path):
                self.assertEqual((REPO / path).read_bytes(), base_file(path))
        actual = {str(p.relative_to(REPO)) for p in (REPO / "configs").rglob("*") if p.is_file()}
        self.assertEqual(actual, set(files) | {
            launches.OPTIQ_CONFIG_PATH,
            str((LANE / "README.md").relative_to(REPO)),
            str((LANE / "source-provenance.json").relative_to(REPO)),
            str((LANE / "local-staging-verification.json").relative_to(REPO)),
        })

    def test_remote_inventory_and_lfs_expectations_are_not_local_verification(self):
        p = json.loads((REPO / self.cfg["source_provenance"]).read_text())
        self.assertEqual((p["repo"], p["revision"]), (MODEL, REVISION))
        self.assertEqual(self.cfg["source_revision"], REVISION)
        self.assertEqual(p["upstream_base_model"], "LiquidAI/LFM2.5-24B-A2B")
        self.assertIsNone(p["upstream_conversion_input_revision"])
        self.assertIsNone(self.cfg["source_model_revision"])
        self.assertEqual(self.cfg["staging_status"], "local-integrity-verified-loadability-unverified")
        self.assertEqual(self.cfg["staging_provenance"],
                         "configs/LiquidAI-LFM2.5-24B-A2B-OptiQ-4bit/local-staging-verification.json")
        # Verify the committed copy of the parent's staging evidence only.
        # Do not inspect the staged model or reinterpret remote-only evidence.
        source_raw = (REPO / self.cfg["source_provenance"]).read_bytes()
        self.assertEqual(hashlib.sha256(source_raw).hexdigest(),
                         "010347c5b824ad0d71d53e1dc42c47a1420c02cf86dc5c2597b9825c36c6f07f")
        staged_raw = (REPO / self.cfg["staging_provenance"]).read_bytes()
        self.assertEqual(len(staged_raw), 5347)
        manifest_hash = "664f52331286087bf3057ecfc0b09374bf57d5a8ecf9fbdd5121d4dc7079a93a"
        self.assertEqual(hashlib.sha256(staged_raw).hexdigest(), manifest_hash)
        staged = json.loads(staged_raw)
        self.assertEqual((staged["repo"], staged["pinned_revision"], staged["resolved_commit"]),
                         (MODEL, REVISION, REVISION))
        self.assertEqual(staged["base_model"], self.cfg["source_model"])
        self.assertEqual(staged["loadability"], "NOT CHECKED (GPU-gated)")
        inventory = p["remote_inventory"]
        entries = inventory["entries"]
        files = [e for e in entries if e["type"] == "file"]
        shards = [e for e in files if e["path"].endswith(".safetensors")]
        expected_shards = sorted(e["path"] for e in shards)
        self.assertEqual(staged["verify"], {
            "config_quantization_maps_identical": True, "containers_validated": True,
            "incomplete_downloads": [], "index_payload_bytes": 16672595968,
            "ok": True, "reasons": [], "shard_bytes": 16672710010,
            "shards": expected_shards, "unexpected_safetensors": [],
        })
        self.assertEqual(staged["weight_files"], expected_shards)
        self.assertEqual(staged["weight_bytes"], self.cfg["model_bytes"])
        self.assertEqual((staged["tree_entries"], staged["tree_file_count"],
                          staged["total_file_bytes"]), (16, 15, 16690854530))
        self.assertEqual(staged["payload_bytes"], 16672595968)
        self.assertEqual(staged["index_payload_bytes"], staged["payload_bytes"])
        self.assertEqual(staged["header_overhead_bytes"], 114042)
        self.assertEqual(staged["weight_bytes"] - staged["payload_bytes"],
                         staged["header_overhead_bytes"])
        staged_files = staged["files"]
        self.assertEqual(len(staged_files), 15)
        self.assertEqual(len({e["path"] for e in staged_files}), 15)
        self.assertEqual(
            [(e["path"], e["size_bytes"], e["hub_lfs_sha256"]) for e in staged_files],
            [(e["path"], e["size"], e.get("lfs", {}).get("oid")) for e in files])
        self.assertEqual(sum(e["size_bytes"] for e in staged_files), staged["total_file_bytes"])
        by_path = {e["path"]: e for e in staged_files}
        for entry in staged_files:
            with self.subTest(local_manifest_path=entry["path"]):
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
                if entry["hub_lfs_sha256"] is not None:
                    self.assertEqual(entry["sha256"], entry["hub_lfs_sha256"])
        for retrieval in p["retrieval"]:
            local = by_path.get(retrieval["path"].removeprefix("hf-").replace("optiq-", "optiq/"))
            if local is not None:
                self.assertEqual((local["sha256"], local["size_bytes"]),
                                 (retrieval["sha256"], retrieval["bytes"]))
        self.assertEqual(staged["default_quantization"], {"bits": 4, "group_size": 64, "mode": "affine"})
        self.assertEqual(staged["per_layer_bits_counts"], {"4": 94, "8": 165})
        self.assertEqual(staged["per_layer_quant_entries"], 259)
        readme = (LANE / "README.md").read_text()
        self.assertIn(manifest_hash, readme)
        self.assertIn(hashlib.sha256(CONFIG.read_bytes()).hexdigest(), readme)
        self.assertIn("no model load/admission yet", next(
            s["value"] for s in self.cfg["settings"] if s["name"] == "fresh_live_gates_required"))
        self.assertIn("live model admission remains pending", self.cfg["known_gaps"][-1])
        for gate in ("loadability", "resource admission", "speed",
                     "native streaming/non-streaming tool parsing"):
            self.assertIn(gate, self.cfg["known_gaps"][0].split("Still unverified:", 1)[1])
        self.assertEqual((len(entries), len(files), len(shards)), (16, 15, 4))
        self.assertEqual(len({e["path"] for e in entries}), 16)
        self.assertEqual([(e["path"], e["size"], e["lfs"]["oid"]) for e in shards], [
            ("model-00001-of-00004.safetensors", 5304487785,
             "4d7098a0724e7366d465bd6f27a049cb02a283d4b175b508eb487925bbd162c9"),
            ("model-00002-of-00004.safetensors", 5366869129,
             "0618aa025a4d5f61317f342ec24fcd4bd1c3f57602e57623c0c805fbec2680db"),
            ("model-00003-of-00004.safetensors", 5303873260,
             "8255962bf517936bae8741218c201796c91f4089c1e32eb54dc00b6597fc0d3c"),
            ("model-00004-of-00004.safetensors", 697479836,
             "a1677ef46d752b53b1b0cdfd980cfa305f1fc39c0d8418450cd6a53704c24e2d"),
        ])
        self.assertEqual(sum(e["size"] for e in shards), 16672710010)
        self.assertEqual(inventory["weight_file_bytes"], self.cfg["model_bytes"])
        self.assertEqual(inventory["weight_shard_count"], 4)
        self.assertEqual(inventory["entry_count"], 16)
        self.assertEqual(inventory["file_count"], 15)
        self.assertEqual(inventory["directory_count"], 1)
        self.assertEqual(sum(e["size"] for e in files), 16690854530)
        self.assertEqual(inventory["all_file_bytes"], 16690854530)
        self.assertEqual(inventory["index_tensor_payload_bytes"], 16672595968)
        self.assertEqual(inventory["index_tensor_count"], 946)
        self.assertEqual(inventory["index_weight_files"], sorted(e["path"] for e in shards))
        self.assertIsNone(inventory["pagination_link"])
        self.assertEqual(len(p["retrieval"]), 10)
        for source in p["retrieval"]:
            self.assertIn(REVISION, source["url"])
            self.assertNotIn(".safetensors?", source["url"])
            self.assertFalse(source["url"].endswith(".safetensors"))
            self.assertEqual(source["status"], 200)
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        for key, value in p["verification_boundary"].items():
            if key != "note":
                self.assertIs(value, False, key)

    def test_full_mixed_precision_maps_and_generation_provenance(self):
        p = json.loads((REPO / self.cfg["source_provenance"]).read_text())
        c = p["remote_config_json_parsed"]
        self.assertEqual(c["architectures"], ["Lfm2MoeForCausalLM"])
        self.assertEqual(c["model_type"], "lfm2_moe")
        quant = c["quantization"]
        self.assertEqual(quant, c["quantization_config"])
        self.assertEqual({k: v for k, v in quant.items() if not isinstance(v, dict)},
                         {"bits": 4, "group_size": 64, "mode": "affine"})
        overrides = [v for v in quant.values() if isinstance(v, dict)]
        self.assertEqual(len(overrides), 259)
        self.assertEqual(Counter(v["bits"] for v in overrides), {4: 94, 8: 165})
        self.assertTrue(all(v["group_size"] == 64 and
                            v.get("mode", quant["mode"]) == "affine" for v in overrides))
        digest = hashlib.sha256(json.dumps(quant, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, "032aaa2f4f103d46718dfa37ccbce73c0a8964567dbe11a48632861c4242787f")
        self.assertEqual(p["quantization_summary"]["canonical_quantization_sha256"], digest)
        self.assertIs(p["quantization_summary"]["quantization_equals_quantization_config"], True)
        self.assertEqual(p["optiq_metadata_summary"]["n_high_bits"], 158)
        self.assertEqual(p["optiq_metadata_summary"]["n_low_bits"], 94)
        for key in ("temperature", "top_k", "repetition_penalty"):
            self.assertEqual(p["generation_config_json_parsed"][key],
                             self.cfg["generation_profiles"]["vendor"][key])
        config_retrieval = next(s for s in p["retrieval"] if s["path"] == "hf-config.json")
        self.assertEqual(config_retrieval["sha256"],
                         "4feddba177b137076d08b01c087c3d6b2acbe2913c6395154536539a92bf47fc")

    def test_real_prompt_config_parser_preserves_entire_predecessor_child_vector(self):
        # Reuse the existing explicit mock fixture; only disposable summaries
        # and rows are written, not actual benchmark evidence.
        fixture = prompts.HermesOpsConnectTimeoutTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        current = fixture._invoke(self.cfg)
        old = fixture._invoke(self.predecessor)
        for command in (current, old):
            command[command.index("--spec") + 1] = "<private-spec>"
        self.assertEqual(current, old)
        for flag, value in {"--connect-timeout": "300", "--temperature": "0.1",
                            "--top-p": "0.0", "--top-k": "50", "--min-p": "0",
                            "--repetition-penalty": "1.05", "--max-tokens": "4096",
                            "--max-turns": "40", "--timeout": "1000",
                            "--first-progress-timeout": "600", "--stream-idle-timeout": "300"}.items():
            self.assertEqual(current.count(flag), 1)
            self.assertEqual(current[current.index(flag) + 1], value)
        self.assertNotIn("--reasoning-effort", current)

    def test_mocked_admission_keeps_exact_id_context_and_probe_failure(self):
        with tempfile.TemporaryDirectory(prefix="optiq-admission-offline-") as td:
            root = Path(td)
            model = root / "metadata-only-model"
            model.mkdir()
            (model / "config.json").write_text("{}\n")
            cfg = dict(self.cfg)
            cfg["benchmark_launch_command"] = cfg["benchmark_launch_command"].replace(MODEL_DIR, str(model))
            path = root / "configs" / "optiq.yaml"
            path.parent.mkdir()
            path.write_text(yaml.safe_dump(cfg))
            process = mock.Mock()
            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command,
                    1 if any(str(x).endswith("probe_mei.py") for x in command) else 0,
                    stdout="explicit offline fixture", stderr="")
            with mock.patch.object(acceptance, "REPO", root), \
                    mock.patch.dict(os.environ, {"HOME": str(root / "home")}), \
                    mock.patch.object(acceptance.subprocess, "Popen", return_value=process) as launch, \
                    mock.patch.object(acceptance, "wait_ready"), \
                    mock.patch.object(acceptance.subprocess, "run", side_effect=fake_run) as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                args = argparse.Namespace(skip_context=False, skip_cache=True)
                record = acceptance.run_config(path, args)
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["probe_rc"], 1)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0], acceptance.split_launch_command(cfg["benchmark_launch_command"]))
            probe = next(c.args[0] for c in run.call_args_list
                         if any(str(x).endswith("probe_mei.py") for x in c.args[0]))
            self.assertIn("--skip-cache", probe)
            self.assertNotIn("--skip-context", probe)
            self.assertEqual(probe[probe.index("--model") + 1], MODEL)
            self.assertEqual(probe[probe.index("--tokenizer") + 1], str(model))
            self.assertEqual(probe[probe.index("--context-cap") + 1], "65536")
            process.terminate.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

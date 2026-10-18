"""Model/network-free MiniCPM-V 4.7 config and launcher contract tests.

The real binary, model, projector, servers, probes and benchmark runners are
never executed. A scratch argv printer checks the shell boundary only.
Run: uv run --locked python -m unittest discover -s runner/tests -v
"""
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_bench
import run_prompt

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "configs/MiniCPM-V-4.7-35B-A3B/gguf-official-q4km.yaml"
GGUF_REPO = "openbmb/MiniCPM-V-4.7-35B-A3B-gguf"
GGUF_REVISION = "77ec40de8445999bf3076aeff9ff45d40a2713cc"
MODEL_FILE = "MiniCPM-V-4_7-35B-A3B-Q4_K_M.gguf"
MODEL_PATH = (
    "/Users/tijs/.cache/huggingface/hub/"
    "models--openbmb--MiniCPM-V-4.7-35B-A3B-gguf/snapshots/"
    f"{GGUF_REVISION}/{MODEL_FILE}"
)
SERVER = "/Users/tijs/projects/llama.cpp-minicpm-v47-1268edac/build/bin/llama-server"
EXPECTED_LAUNCH = (
    f"{SERVER} \\\n"
    f"  --model {MODEL_PATH} \\\n"
    "  --offline --no-mmproj --no-webui \\\n"
    "  --host 127.0.0.1 --port 8017 \\\n"
    "  --ctx-size 65536 --parallel 1 --n-gpu-layers 99 --flash-attn on \\\n"
    "  --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 \\\n"
    "  --cache-prompt --cache-ram 0 \\\n"
    "  --temp 0.7 --top-p 0.95 --top-k 100 --min-p 0.0 \\\n"
    "  --repeat-penalty 1.03 --repeat-last-n 65536 --presence-penalty 0.0 --frequency-penalty 0.0 \\\n"
    "  --samplers 'penalties;temperature;top_k;top_p;min_p' \\\n"
    "  --jinja --reasoning off --chat-template-kwargs '{\"enable_thinking\":false}' \\\n"
    "  --timeout 1800\n"
)
EXPECTED_ARGS = [
    "--model", MODEL_PATH,
    "--offline", "--no-mmproj", "--no-webui",
    "--host", "127.0.0.1", "--port", "8017",
    "--ctx-size", "65536", "--parallel", "1", "--n-gpu-layers", "99",
    "--flash-attn", "on", "--batch-size", "512", "--ubatch-size", "128",
    "--cache-type-k", "f16", "--cache-type-v", "f16",
    "--cache-prompt", "--cache-ram", "0",
    "--temp", "0.7", "--top-p", "0.95", "--top-k", "100", "--min-p", "0.0",
    "--repeat-penalty", "1.03", "--repeat-last-n", "65536",
    "--presence-penalty", "0.0", "--frequency-penalty", "0.0",
    "--samplers", "penalties;temperature;top_k;top_p;min_p",
    "--jinja", "--reasoning", "off",
    "--chat-template-kwargs", '{"enable_thinking":false}',
    "--timeout", "1800",
]
EXPECTED_PROFILE = {
    "temperature": 0.7, "top_p": 0.95, "top_k": 100, "min_p": 0.0,
    "presence_penalty": 0.0, "repetition_penalty": 1.03,
    "frequency_penalty": 0.0,
}


class MiniCPMV47ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load(CONFIG.read_text())

    def test_exact_official_base_quant_and_publisher_hash(self):
        expected = {
            "model": f"{GGUF_REPO}:Q4_K_M",
            "base_model": "openbmb/MiniCPM-V-4.7-35B-A3B",
            "base_source_revision": "0bbda78419a0b505a58234574ff40b1c344a86fc",
            "source_revision": GGUF_REVISION,
            "model_file": MODEL_FILE,
            "model_bytes": 21166255008,
            "model_sha256": "bf3d1c67f7843193e4483aebd26c5dea6b6d1f6a06ffa03c2387a6f3cc6d7df5",
            "quant_family": "GGUF Q4_K_M (official OpenBMB)",
        }
        self.assertEqual({key: self.cfg[key] for key in expected}, expected)

    def test_projector_is_separately_pinned_but_never_required_or_loaded(self):
        self.assertEqual(self.cfg["projector"], {
            "repository": GGUF_REPO, "source_revision": GGUF_REVISION,
            "filename": "mmproj-model-f16.gguf", "quant": "F16",
            "bytes": 1119575840,
            "sha256": "bff3b688e14c300eca273092c37c50a0ddfcc2054e079af1a0480edeed5d20f1",
            "loaded": False, "staging_required": False,
        })
        command = self.cfg["benchmark_launch_command"]
        self.assertIn("--no-mmproj", command)
        for forbidden in ("--mmproj ", "mmproj-model", "--image", "--video", "--audio"):
            self.assertNotIn(forbidden, command)

    def test_runtime_identity_and_metal_are_pinned_not_homebrew(self):
        runtime = self.cfg["runtime"]
        expected = {
            "repository": "ggml-org/llama.cpp",
            "revision": "1268edac579110aeb1407f7928f53193ed4e28d4",
            "minicpm_v47_support_commit": "69f201a2051ea9b9e9b50c3cc56afd9e2ae64414",
            "version": "0.7.0-dev", "build_number": 11707,
            "reported_commit": "1268edac5",
            "binary_sha256": "04415c5a3b5945f3e3d51f267c3dafe606829b00eb2a18232663ff23e5960ab1",
            "metal": True,
        }
        self.assertEqual({key: runtime[key] for key in expected}, expected)
        self.assertIn("-DGGML_METAL=ON", runtime["build_command"])
        self.assertIn("-DGGML_METAL_EMBED_LIBRARY=ON", runtime["build_command"])
        self.assertEqual(self.cfg["inference_engine"], "llama.cpp")
        self.assertEqual(self.cfg["orchestration"]["server_binary"], SERVER)
        self.assertNotIn("homebrew", self.cfg["benchmark_launch_command"])

    def test_launch_block_and_runner_output_are_exact(self):
        self.assertEqual(self.cfg["benchmark_launch_command"], EXPECTED_LAUNCH)
        self.assertEqual(run_bench.server_command(self.cfg), EXPECTED_LAUNCH.strip())

    def test_shell_receives_entire_argv_with_alias_and_optional_seed(self):
        # Replace only the executable, not any arguments. This evaluates real
        # shell quoting without inspecting or invoking a runtime/model file.
        alias = "bench-" + hashlib.sha256(CONFIG.read_bytes()).hexdigest()[:12]
        with tempfile.TemporaryDirectory(prefix="minicpm47-argv-") as td:
            printer = Path(td) / "capture_argv.py"
            printer.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
            for selected_alias, seed in ((None, None), (alias, None), (alias, 17)):
                with self.subTest(alias=selected_alias, seed=seed):
                    command = run_bench.server_command(self.cfg, alias=selected_alias)
                    expected_text = EXPECTED_LAUNCH.strip()
                    expected_args = list(EXPECTED_ARGS)
                    if selected_alias:
                        expected_text += f" --alias {selected_alias}"
                        expected_args += ["--alias", selected_alias]
                    self.assertEqual(command, expected_text)
                    command = run_bench.with_seed(command, seed)
                    if seed is not None:
                        expected_args += ["--seed", str(seed)]
                    self.assertTrue(command.startswith(SERVER + " \\\n"))
                    inert = (
                        shlex.quote(sys.executable) + " " + shlex.quote(str(printer))
                        + command[len(SERVER):]
                    )
                    result = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c", inert],
                        text=True, capture_output=True, timeout=10, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), expected_args)
                    self.assertEqual(result.stderr, "")

    def test_instruct_profile_is_valid_and_reaches_body_without_invented_effort(self):
        self.assertEqual(self.cfg["generation_profiles"], {"instruct": EXPECTED_PROFILE})
        self.assertEqual(self.cfg["hermes_ops_generation_profile"], "instruct")
        profile = run_prompt.normalize_generation_overrides(
            self.cfg["generation_profiles"]["instruct"]
        )
        self.assertEqual(profile, EXPECTED_PROFILE)
        body = run_prompt.build_chat_body(
            model=self.cfg["model"], messages=[{"role": "user", "content": "hello"}],
            tools=None, max_tokens=4096, **profile,
        )
        self.assertEqual({key: body[key] for key in profile}, EXPECTED_PROFILE)
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("coding_reasoning_effort", self.cfg)
        self.assertEqual(self.cfg["temperature"], EXPECTED_PROFILE["temperature"])
        self.assertEqual(self.cfg["reasoning_mode"], "instruct")
        self.assertEqual(self.cfg["context_cap"], 65536)

    def test_deterministic_sanity_body_stays_separate_from_instruct_profile(self):
        body = run_prompt.build_chat_body(
            model=self.cfg["model"], messages=[{"role": "user", "content": "hello"}],
            tools=None, temperature=0, max_tokens=4096,
        )
        self.assertEqual(body["temperature"], 0)
        self.assertNotIn("top_k", body)
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("system_prompt_suffix", self.cfg)
        self.assertNotIn("hermes_ops_max_tokens", self.cfg)

    def test_loopback_routing_has_no_unverified_proxy_or_download_selection(self):
        self.assertEqual(self.cfg["benchmark_endpoint"], "http://127.0.0.1:8017/v1")
        self.assertEqual(self.cfg["orchestration"], {
            "raw_port": 8017, "needs_proxy": False,
            "hermes_provider": "minicpm-v47-gguf",
            "server_binary": SERVER, "viable": "full",
        })
        for forbidden in ("--hf-repo", "-hf ", "--model-url", "--hf-file", "dspark", "--model-draft"):
            self.assertNotIn(forbidden, self.cfg["benchmark_launch_command"])
        self.assertIn("--offline", self.cfg["benchmark_launch_command"])

    def test_corrected_bench_provider_route_is_explicit(self):
        route = self.cfg["hermes_provider_route"]
        self.assertEqual(route, {
            "profile": "bench",
            "provider": "minicpm-v47-gguf",
            "endpoint": "http://127.0.0.1:8017/v1",
            "transport": "chat_completions",
            "model": "openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M",
            "context_length": 65536,
        })
        self.assertEqual(route["provider"], self.cfg["orchestration"]["hermes_provider"])
        self.assertEqual(route["endpoint"], self.cfg["benchmark_endpoint"])
        self.assertEqual(route["model"], self.cfg["model"])
        self.assertEqual(route["context_length"], self.cfg["context_cap"])

    def test_per_model_sources_and_unrun_gates_remain_explicit(self):
        settings = {item["name"]: item for item in self.cfg["settings"]}
        required = {
            "model_citation_and_scope", "official_artifact_and_projector_identity",
            "runtime_build_and_support", "generation_profiles_policy",
            "sampler_order_and_penalty_window", "instruct_template_and_tool_path",
            "context_offload_prefill_cache_and_network_policy",
        }
        self.assertEqual(set(settings), required)
        for name, item in settings.items():
            with self.subTest(setting=name):
                self.assertTrue(item["value"])
                self.assertIn("https://", item["source"])
        self.assertIn("0bbda78419a0b505a58234574ff40b1c344a86fc", settings["model_citation_and_scope"]["source"])
        self.assertIn(GGUF_REVISION, settings["official_artifact_and_projector_identity"]["source"])
        self.assertIn("Text", CONFIG.read_text())
        gaps = "\n".join(self.cfg["known_gaps"])
        for required_gate in ("PREPARATION ONLY", "Parent must recheck", "SHA-256", "admission", "No quality", "2.0 methodology"):
            self.assertIn(required_gate, gaps)


if __name__ == "__main__":
    unittest.main()

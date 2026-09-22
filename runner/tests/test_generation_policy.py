"""Focused policy tests for the task-specific generation CONTRACT (2026-09-22).

This is the per-front-runner POLICY layer that sits on top of the named
generation-profile infrastructure (the infrastructure itself is tested in
test_generation_overrides.py: option semantics, fail-closed validation,
CLI/payload propagation, run_bench wiring, coding --reasoning plumbing).

Contract invariants under test here (durable plan
7f5c67e7-b564-4df3-8209-14f7443b56e2):

  - every policy-enabled front-runner config declares `generation_profiles`
    with BOTH named lanes (`capability` = the explicit high/xhigh
    capability-ceiling overlay, `practical` = the explicit medium comparison
    overlay), each lane declaring `reasoning_effort` explicitly (a lane is
    never implicit);
  - `hermes_ops_generation_profile` resolves to a declared profile (the
    explicit general/vendor default for Hermes Ops) and `coding_reasoning_effort`
    stays inside the `hermes chat --reasoning` vocabulary (the model-specific
    coding profile);
  - every policy-enabled config carries a source-backed immutable citation in
    its own `settings` under a `generation_profiles_policy` name;
  - selection actually reaches the wire: a real front-runner config driving
    run_prompt_suite.main() sends its resolved lane fields in the HTTP
    payload;
  - every result records the resolved lane immutably: the log row carries
    `generation_profile` / `generation_overrides` / `generation` and the
    run_prompt.py result carries the same `generation` sampler/effort fields
    the backend received — the historic no-profile lane records
    `{"temperature": 0}`, never a silent sampler invention;
  - a candidate with a distinct engine keeps its engine/model separation
    under the policy (llama.cpp-prism is never presented as stock llama.cpp).

No inference backend, model download, or benchmark run is involved: payloads
are inspected through a recording local SSE server (same pattern as
test_generation_overrides.py / test_run_prompt_timeouts.py).

Run: uv run --locked python -m unittest discover -s runner/tests -q
"""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_prompt
import run_prompt_suite

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The front-runners configured with policy in this contract (configs/README.md
# "Policy-enabled configs" table). Each declares generation_profiles with
# capability + practical, hermes_ops_generation_profile, and
# coding_reasoning_effort.
POLICY_CONFIGS = [
    "configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml",
    "configs/Ornith-1.5-35B-A3B/mei.yaml",
    "configs/Ornith-1.5-35B-A3B/gguf.yaml",
    "configs/Ornith-1.5-35B-A3B/gguf-thinking.yaml",
    "configs/Qwen3.6-35B-A3B/mei.yaml",
    "configs/Qwen3.6-35B-A3B-textonly/mei.yaml",
    "configs/Qwen3.6-35B-A3B/gguf-official-q4km.yaml",
    "configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml",
    "configs/Qwen3.8-27B/gguf.yaml",
    "configs/Qwen3.8-27B/mei.yaml",
]


def _load_yaml(path):
    import yaml
    return yaml.safe_load(Path(path).read_text())


class PolicyConfigCoverageTests(unittest.TestCase):
    """Every policy-enabled front-runner config is well-formed policy: named
    lanes exist, effort is explicit and in-vocabulary, selectors resolve,
    fields normalize — and nothing is silently invented (no max_tokens inside
    profiles, no unknown override fields)."""

    def test_policy_configs_exist(self):
        for rel in POLICY_CONFIGS:
            self.assertTrue(
                (REPO_ROOT / rel).is_file(),
                f"policy config missing: {rel}",
            )

    def test_every_policy_config_declares_both_lanes_with_explicit_effort(self):
        import run_fixture_suite as rfs
        for rel in POLICY_CONFIGS:
            cfg = _load_yaml(REPO_ROOT / rel)
            profiles = cfg.get("generation_profiles")
            self.assertIsInstance(
                profiles, dict, f"{rel}: generation_profiles must be a mapping"
            )
            for lane in ("capability", "practical"):
                self.assertIn(
                    lane, profiles,
                    f"{rel}: generation_profiles must declare the "
                    f"{lane!r} lane (explicit capability-ceiling and medium "
                    f"comparison overlays)",
                )
                profile = profiles[lane]
                # The named lanes are explicit: effort is declared out loud,
                # never left to a silent default.
                self.assertIn(
                    "reasoning_effort", profile,
                    f"{rel}: generation_profiles[{lane!r}] must declare "
                    f"reasoning_effort explicitly (no implicit lane)",
                )
                self.assertIn(
                    profile["reasoning_effort"], rfs.HERMES_REASONING_LEVELS,
                    f"{rel}: generation_profiles[{lane!r}].reasoning_effort "
                    f"{profile['reasoning_effort']!r} is not a hermes chat "
                    f"--reasoning level",
                )
                # Fail-closed: every declared field must normalize without
                # error (unknown field / wrong type would raise).
                run_prompt.normalize_generation_overrides(profile)

    def test_every_policy_config_selector_resolves(self):
        for rel in POLICY_CONFIGS:
            cfg = _load_yaml(REPO_ROOT / rel)
            selector = cfg.get("hermes_ops_generation_profile")
            self.assertIsNotNone(
                selector,
                f"{rel}: hermes_ops_generation_profile must be set (the "
                f"explicit general/vendor default for Hermes Ops)",
            )
            self.assertIn(
                selector, cfg.get("generation_profiles", {}),
                f"{rel}: hermes_ops_generation_profile {selector!r} is not "
                f"declared in generation_profiles",
            )

    def test_every_policy_config_coding_effort_is_in_vocabulary(self):
        import run_fixture_suite as rfs
        for rel in POLICY_CONFIGS:
            cfg = _load_yaml(REPO_ROOT / rel)
            effort = cfg.get("coding_reasoning_effort")
            self.assertIsNotNone(
                effort,
                f"{rel}: coding_reasoning_effort must be set (the "
                f"model-specific coding profile)",
            )
            self.assertIn(
                effort, rfs.HERMES_REASONING_LEVELS,
                f"{rel}: coding_reasoning_effort {effort!r} is not a hermes "
                f"chat --reasoning level",
            )

    def test_every_policy_config_has_a_source_backed_settings_entry(self):
        # The acceptance criterion is a source-backed immutable policy
        # citation: each policy-enabled config must document its
        # generation_policy in settings under the generation_profiles_policy
        # name, sourced to its vendor/model card (never an invented value).
        for rel in POLICY_CONFIGS:
            cfg = _load_yaml(REPO_ROOT / rel)
            settings = cfg.get("settings", [])
            self.assertIsInstance(
                settings, list, f"{rel}: settings must be a list"
            )
            self.assertTrue(
                any(
                    isinstance(entry, dict)
                    and str(entry.get("name", "")).startswith(
                        "generation_profiles_policy"
                    )
                    and entry.get("source")
                    for entry in settings
                ),
                f"{rel}: settings must carry a generation_profiles_policy "
                f"entry with a source citation",
            )

    def test_no_profile_carries_max_tokens_or_unknown_fields(self):
        for rel in POLICY_CONFIGS:
            cfg = _load_yaml(REPO_ROOT / rel)
            for lane, profile in cfg.get("generation_profiles", {}).items():
                self.assertNotIn(
                    "max_tokens", profile,
                    f"{rel}: generation_profiles[{lane!r}] must not carry "
                    f"max_tokens (hermes_ops_max_tokens is the single source)",
                )
                for key in profile:
                    self.assertIn(
                        key, run_prompt._GENERATION_OVERRIDE_TYPES,
                        f"{rel}: generation_profiles[{lane!r}] field "
                        f"{key!r} is not a supported override",
                    )

    def test_bonsai_engine_and_model_stay_distinct_under_policy(self):
        # The Prism fork candidate is llama.cpp-prism, NEVER stock llama.cpp;
        # the policy must not blur that separation.
        bonsai = _load_yaml(
            REPO_ROOT / "configs" / "Ternary-Bonsai-2-27B-PTQ1_0" / "prism-gguf.yaml"
        )
        self.assertEqual(bonsai["inference_engine"], "llama.cpp-prism")
        self.assertTrue(bonsai["model"].startswith("prism-ml/Ternary-Bonsai-2-27B"))
        # The card documents xhigh as the default effort; capability carries it.
        self.assertEqual(
            bonsai["generation_profiles"]["capability"]["reasoning_effort"], "xhigh"
        )
        self.assertEqual(
            bonsai["generation_profiles"]["practical"]["reasoning_effort"], "medium"
        )
        self.assertEqual(bonsai["coding_reasoning_effort"], "xhigh")


def _chunk(**delta):
    return json.dumps({
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
    })


class _RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            self.server.last_request_body = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.server.last_request_body = None
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(f"data: {_chunk(content='hello there')}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class RecordingSSEServer:
    def __init__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
        self.httpd.daemon_threads = True
        self.httpd.last_request_body = None
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.httpd.shutdown()
        self.httpd.server_close()


class PolicyResolutionEndToEndTests(unittest.TestCase):
    """A REAL front-runner config drives run_prompt_suite.main(): the selected
    lane must (a) reach the HTTP payload and (b) be recorded immutably in the
    log row. REPO is redirected to a throwaway tree; the config file is copied
    in so snapshot_config() and the durable result paths stay inside the fake
    tree (the real results/ is never opened)."""

    QWEN38_GGUF = "configs/Qwen3.8-27B/gguf.yaml"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "runner").mkdir()
        (self.tmp / "tasks").mkdir()
        (self.tmp / "results").mkdir()
        real_runner = Path(run_prompt.__file__).parent
        for name in ("run_prompt.py", "grade_prompt.py"):
            shutil.copy2(real_runner / name, self.tmp / "runner" / name)
        self.config_path = self.tmp / "frontrunner_config.yaml"
        shutil.copy2(REPO_ROOT / self.QWEN38_GGUF, self.config_path)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write_suite(self, name):
        import yaml
        spec = {
            "suite": name,
            "runner": "prompt",
            "timeout_seconds": 20,
            "max_turns": 3,
            "tasks": [{
                "id": f"{name}-one",
                "type": "prompt-response",
                "prompt_spec": {"user_prompt": "hello"},
                "check": {"type": "contains", "text": "hello there"},
            }],
        }
        (self.tmp / "tasks" / f"{name}.yaml").write_text(yaml.safe_dump(spec))

    def _run(self, suite, base_url):
        import bench_common
        argv = [
            "run_prompt_suite.py", "--suite", suite,
            "--base-url", base_url, "--model", "fake-model",
            "--inference-engine", "fake",
            "--config", str(self.config_path),
            "--summary-out", str(self.tmp / "summary.json"),
        ]
        with unittest.mock.patch.object(run_prompt_suite, "REPO", self.tmp), \
                unittest.mock.patch.object(bench_common, "REPO", self.tmp), \
                unittest.mock.patch.object(sys, "argv", argv):
            run_prompt_suite.main()
        return json.loads((self.tmp / "summary.json").read_text())

    def test_capability_lane_reaches_payload_and_row(self):
        cfg = _load_yaml(self.config_path)
        expected = cfg["generation_profiles"]["capability"]
        self._write_suite("hermes_ops")
        with RecordingSSEServer() as server:
            rows = self._run("hermes_ops", server.url)
            body = server.httpd.last_request_body
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # The payload carries every declared lane field, values verbatim.
        for key, value in expected.items():
            self.assertEqual(
                body[key], value,
                f"payload field {key} did not carry the lane value",
            )
        # Immutable row metadata: profile name, resolved overrides, and the
        # exact wire fields the backend received.
        self.assertEqual(row["generation_profile"], "capability")
        self.assertEqual(row["generation_overrides"], expected)
        self.assertEqual(row["generation"], {
            "temperature": expected["temperature"],
            "top_p": expected["top_p"],
            "top_k": expected["top_k"],
            "min_p": expected["min_p"],
            "presence_penalty": expected["presence_penalty"],
            "repetition_penalty": expected["repetition_penalty"],
            "reasoning_effort": expected["reasoning_effort"],
        })

    def test_no_profile_lane_records_historic_metadata(self):
        # sanity never selects a profile: the row must record the historic
        # lane (None profile, no overrides, temperature 0 on the wire) — the
        # exact metadata shape a reader needs to identify a legacy row.
        self._write_suite("sanity")
        with RecordingSSEServer() as server:
            rows = self._run("sanity", server.url)
            body = server.httpd.last_request_body
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNone(row["generation_profile"])
        self.assertIsNone(row["generation_overrides"])
        self.assertEqual(body["temperature"], 0)
        self.assertNotIn("top_p", body)
        self.assertEqual(row["generation"], {"temperature": 0})


class RunPromptResultGenerationMetadataTests(unittest.TestCase):
    """The durable run_prompt.py result carries the exact sampler/effort
    fields the backend received (`generation`), so durable result files are
    self-describing even without the suite row."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.spec = self.tmp / "spec.json"
        self.spec.write_text(json.dumps({"user_prompt": "hello"}))

    def _run(self, *extra):
        with RecordingSSEServer() as server:
            cmd = [sys.executable, str(Path(run_prompt.__file__)),
                   "--base-url", server.url, "--model", "m",
                   "--spec", str(self.spec), "--max-turns", "1",
                   *extra]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            body = server.httpd.last_request_body
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_result_records_the_configured_generation_fields(self):
        result = self._run(
            "--temperature", "1.0", "--top-p", "0.95", "--top-k", "20",
            "--min-p", "0", "--presence-penalty", "0",
            "--repetition-penalty", "1.0", "--reasoning-effort", "xhigh",
        )
        self.assertEqual(result["generation"], {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0,
            "presence_penalty": 0,
            "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
        })

    def test_no_profile_result_records_temperature_zero_only(self):
        result = self._run("--temperature", "0")
        self.assertEqual(result["generation"], {"temperature": 0})


if __name__ == "__main__":
    unittest.main()
"""Regression tests for the isolated oMLX runner integration."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_bench
import probe_omlx
import run_omlx_acceptance


class OmlxIdentityTests(unittest.TestCase):
    def test_served_model_id_requires_exact_match_for_omlx(self):
        """A source repository name must not accept a stale oMLX directory ID.

        oMLX's /v1/models exposes model-directory/alias IDs, unlike the source
        Hugging Face repository recorded in the benchmark config. The runner
        must insist on the config's stable served ID rather than fall back to
        a fuzzy source-ID comparison.
        """
        payload = json.dumps({"data": [{"id": "bench-qwen-omlx-stale"}]}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return payload

        with patch("run_bench.urllib.request.urlopen", return_value=Response()):
            self.assertFalse(
                run_bench.assert_serving_expected_model(
                    8020,
                    "Jundot/Qwen3.8-27B-oQ4e-fp16-mtp",
                    served_model_id="bench-qwen38-oq4e-fp16-mtp",
                )
            )

    def test_plain_completion_requires_nonempty_content(self):
        """Endpoint health/model identity alone is insufficient for a run."""
        payload = json.dumps({"choices": [{"message": {"content": ""}}]}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return payload

        with patch("run_bench.urllib.request.urlopen", return_value=Response()):
            self.assertFalse(
                run_bench.assert_plain_completion(
                    "http://127.0.0.1:8020/v1", "bench-lfm", timeout=1
                )
            )


class OmlxLauncherTests(unittest.TestCase):
    def test_dry_run_isolated_cold_launch_uses_explicit_no_cache(self):
        """The wrapper must show the exact isolated cold-launch command.

        This prevents a future edit from silently using ~/.omlx, another
        backend's port, or oMLX's default SSD cache for a cold baseline.
        """
        script = Path(__file__).resolve().parent.parent / "start_omlx_server.sh"
        with tempfile.TemporaryDirectory() as td:
            model_dir = Path(td) / "models" / "bench-lfm"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}")
            result = subprocess.run(
                [
                    "bash", str(script), "--model-dir", str(model_dir.parent),
                    "--served-model-id", "bench-lfm", "--port", "8020",
                    "--context-cap", "65536", "--cache-mode", "cold",
                    "--dry-run",
                ],
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--base-path", result.stdout)
        self.assertIn("--no-cache", result.stdout)
        self.assertIn("--port 8020", result.stdout)
        self.assertIn("--memory-guard safe", result.stdout)
        self.assertIn("--no-hf-cache", result.stdout)

    def test_hot_mode_persists_hot_only_cache_identity(self):
        script = Path(__file__).resolve().parent.parent / "start_omlx_server.sh"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model_dir = root / "models" / "bench-lfm"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}")
            base = root / "state"
            result = subprocess.run(
                [
                    "bash", str(script), "--model-dir", str(model_dir.parent),
                    "--served-model-id", "bench-lfm", "--port", "8020",
                    "--context-cap", "65536", "--cache-mode", "hot",
                    "--cache-dir", str(root / "cache"),
                    "--base-path", str(base), "--dry-run",
                ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            settings = json.loads((base / "settings.json").read_text())
            model_settings = json.loads((base / "model_settings.json").read_text())
        self.assertTrue(settings["cache"]["enabled"])
        self.assertTrue(settings["cache"]["hot_cache_only"])
        self.assertEqual(settings["cache"]["ssd_cache_dir"], str(root / "cache"))
        self.assertEqual(settings["sampling"]["max_context_window_policy"], 65536)
        self.assertEqual(model_settings["models"]["bench-lfm"]["max_tokens"], 32768)


class OmlxProbeTests(unittest.TestCase):
    def test_tool_validator_requires_exact_schema_and_finish_reason(self):
        good = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {"tool_calls": [{"function": {
                    "name": "add_numbers", "arguments": '{"a":15,"b":27}'
                }}]},
            }]
        }
        self.assertEqual(probe_omlx.validate_add_call(good)["arguments"], {"a": 15, "b": 27})
        bad = json.loads(json.dumps(good))
        bad["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"a":15,"b":28}'
        with self.assertRaises(AssertionError):
            probe_omlx.validate_add_call(bad)

    def test_request_json_rejects_http_200_error_envelope(self):
        response = Mock()
        response.status = 200
        response.read.return_value = json.dumps({"error": {"message": "guard rejected"}}).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(probe_omlx.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "HTTP 200 error payload"):
                probe_omlx.request_json("http://127.0.0.1:1/v1/completions", {})

    def test_acceptance_runner_strips_yaml_shell_continuations(self):
        command = "bash runner/start.sh --model foo \\\n   --port 8020"
        self.assertEqual(
            run_omlx_acceptance.split_launch_command(command),
            ["bash", "runner/start.sh", "--model", "foo", "--port", "8020"],
        )


class OmlxCleanupTests(unittest.TestCase):
    def test_fail_fast_path_still_invokes_isolated_teardown(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "omlx.yaml"
            config.write_text("framework: omlx\n")
            with patch("run_bench._run_one_impl", side_effect=RuntimeError("boom")), \
                    patch("run_bench.run") as run:
                with self.assertRaises(RuntimeError):
                    run_bench.run_one(config)
        run.assert_called_once()
        self.assertIn("stop_omlx_server.sh", str(run.call_args.args[0]))


class OmlxFocusedRerunTests(unittest.TestCase):
    def test_runner_exposes_coding_only_stage_for_contaminated_reruns(self):
        runner = Path(__file__).resolve().parent.parent / "run_bench.py"
        proc = subprocess.run(
            [sys.executable, str(runner), "--help"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--stage", proc.stdout)
        self.assertIn("coding", proc.stdout)


if __name__ == "__main__":
    unittest.main()

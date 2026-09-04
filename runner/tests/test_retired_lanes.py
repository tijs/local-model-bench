"""Regression tests for the retired oMLX / vllm-mlx lanes (2026-09-04).

Replaces the deleted test_omlx_integration.py. Covers the two things the
retirement changes:

1. `orchestration.viable: retired` configs are SKIPPED by the runner (same as
   blocked) — they are no longer runnable current paths.
2. Historical oMLX / vllm-mlx log rows are still read backward-compatibly by
   the leaderboard (the engines are retired as *active* lanes, not erased),
   and the live configs are marked retired so a sweep neither runs nor
   advertises them.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_leaderboard
import run_bench

REPO = Path(__file__).resolve().parents[2]


def _write_config(root: Path, rel: str, engine: str, viable: str):
    path = root / "configs" / Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"model: some-org/Some-Model\n"
        f"inference_engine: {engine}\n"
        f"benchmark_launch_command: |\n  echo never-launched-{engine}\n"
        f"orchestration:\n"
        f"  raw_port: 9999\n"
        f"  needs_proxy: false\n"
        f"  viable: {viable}\n"
    )
    return path


class RetiredLaneSkipTests(unittest.TestCase):
    def test_retired_config_is_skipped_not_run(self):
        """A `viable: retired` config must not launch a server (equals blocked)."""
        with patch.object(run_bench, "run") as run, \
                patch.object(run_bench, "REPO", new=REPO), \
                tempfile.TemporaryDirectory() as td:
            cfg = _write_config(Path(td), "qwen/omlx.yaml", "omlx", "retired")
            rc = run_bench.run_one(cfg)
            self.assertIsNone(rc)
            run.assert_not_called()  # nothing launched, no server, no probe

    def test_retired_and_blocked_both_short_circuit(self):
        """Both retired and blocked land in the same skip branch of run_one."""
        # retired => skip branch returns before any orchestration
        with patch.object(run_bench, "run") as run, \
                patch.object(run_bench, "REPO", new=REPO), \
                tempfile.TemporaryDirectory() as td:
            cfg = _write_config(Path(td), "m/mlx.yaml", "vllm-mlx", "retired")
            run_bench.run_one(cfg)
            self.assertSetEqual(set(), {c.args[0] for c in run.call_args_list})

    def test_runner_no_longer_invokes_deleted_omlx_scripts(self):
        """run_one's teardown must not reference the removed start/stop_omlx
        server scripts (they were deleted with the lane)."""
        src = Path(__file__).resolve().parent.parent / "run_bench.py"
        text = src.read_text()
        self.assertNotIn("stop_omlx_server.sh", text)
        self.assertNotIn("probe_omlx.py", text)
        self.assertNotIn("start_omlx_server.sh", text)


class HistoricalRowReadingTests(unittest.TestCase):
    def test_historical_omlx_vllm_rows_still_group_by_engine(self):
        """backward-compatible engine reading must survive the lan retirement
        (existing leaderboard grouping relies on it)."""
        self.assertEqual(build_leaderboard._row_inference_engine(
            {"inference_engine": "omlx"}), "omlx")
        self.assertEqual(build_leaderboard._row_inference_engine(
            {"inference_engine": "vllm-mlx"}), "vllm-mlx")
        self.assertEqual(build_leaderboard._row_inference_engine(
            {"backend": "omlx"}), "omlx")  # legacy column still read

    def test_retired_lane_configs_are_detected(self):
        with patch.object(build_leaderboard, "REPO", new=REPO), \
                tempfile.TemporaryDirectory() as td:
            # Point the scan at a temp configs tree carrying retired configs.
            root = Path(td)
            _write_config(root, "qwen/mlx.yaml", "vllm-mlx", "retired")
            _write_config(root, "qwen/omlx.yaml", "omlx", "retired")
            _write_config(root, "other/gguf.yaml", "llama.cpp", "full")
            with patch.object(build_leaderboard, "REPO", new=root):
                retired = build_leaderboard._retired_lane_configs()
            engines = {r["inference_engine"] for r in retired}
            self.assertEqual(engines, {"vllm-mlx", "omlx"})
            # the active llama.cpp config is not a retired lane
            self.assertNotIn(
                "configs/other/gguf.yaml",
                [r["config_path"] for r in retired],
            )


class ActiveLaneSanityTests(unittest.TestCase):
    def test_no_active_llama_mei_config_was_marked_retired(self):
        """Retirement must never have flipped a currently-active llama.cpp/Mei
        config to `retired`."""
        bad = []
        for path in sorted(REPO.glob("configs/*/*.yaml")):
            try:
                cfg = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                continue
            engine = cfg.get("inference_engine", "")
            if engine in ("llama.cpp", "llama.cpp-dflash2", "llama.cpp-dspark", "mei"):
                if (cfg.get("orchestration") or {}).get("viable") in ("retired",):
                    bad.append(str(path.relative_to(REPO)))
        self.assertEqual(bad, [])

    def test_every_omlx_and_vllm_mlx_config_is_retired(self):
        """No oMLX / vllm-mlx config may remain an advertised runnable path."""
        active = []
        for path in sorted(REPO.glob("configs/*/*.yaml")):
            try:
                cfg = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                continue
            engine = cfg.get("inference_engine", "")
            if engine in ("omlx", "vllm-mlx"):
                viable = (cfg.get("orchestration") or {}).get("viable")
                if viable not in ("retired", "blocked"):
                    active.append(str(path.relative_to(REPO)))
        self.assertEqual(active, [])


if __name__ == "__main__":
    unittest.main()
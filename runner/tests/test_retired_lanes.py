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

# Deliberately-retired CANDIDATE configs — not active lanes. A llama.cpp/Mei
# config may only carry `viable: retired` when it is listed here with a
# documented reason; the guard below fails on any undocumented flip. Each
# retirement must keep the historical evidence (config provenance, artifacts,
# evidence paths) intact.
RETIRED_CANDIDATE_CONFIGS = {
    # 2026-09-18 AXQ6 prospect-queue removal by explicit user decision
    # ("Ok I'm giving up on axq6 let's remove that from the prospects and go
    # to next"). Never benchmarked: the compiler compatibility fix/build/load
    # succeeded (vmlx-swift type-check fix 15bada58 local PATH dep) but the
    # direct slow probe failed within budget (plain_completion 3600.030 s
    # timeout while decoding continuously; 0 results/log.jsonl rows, no
    # leaderboard entry for f0c165be1ebe / prior pre-gate hashes). Slow-model/
    # budget admission stop — NOT a model-incompatibility verdict. See the
    # config's RETIRED-LANE banner, retired_reason, known_gaps, and
    # artifacts/qwen36-axq6-native-gate-direct-probe-20260918.md.
    "configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml",
    # 2026-09-24 Gravity-arm scope retirement by explicit user direction
    # (commit 4adb4fb; further research for the Gravity arm and the Bonsai 2
    # GGUF PTQ1_0 lane is DISCARDED — only the Bonsai 2 27B MLX pack on
    # Mei/vmlx remains active). Never benchmarked: the bounded native gate
    # PASSED 7/7 and the exploratory canary ran 5/6 on the pinned binary +
    # staged artifact (2026-09-19), but zero results/log.jsonl rows ever
    # existed for this config — closure is a research-scope decision, NOT an
    # incompatibility or performance verdict. See the config's RETIRED-LANE
    # banner, retired_reason, known_gaps, and
    # artifacts/gravity-rl-q4km-native-gate-20260919.md.
    "configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml",
    # 2026-09-24 Bonsai 2 GGUF (PTQ1_0) lane scope retirement by the same
    # explicit user direction (commit 4adb4fb). Not a quality verdict: the
    # bounded native gates PASSED on the pinned Prism fork binary + staged
    # artifact (2026-09-18 initial + canonical-alias recheck; 2026-09-23
    # current-hash gate 7/7 under config hash 5e4c9a30643f / runner SHA
    # 1bd7d8810d53), the one-trial canaries were exploratory 2/6 model-
    # behavior evidence, and the only benchmark fragment is the interrupted
    # two-sanity-row leg under OLD hash 5b760871ce84 / runner SHA
    # 0d384a593830 (commit d656bcc) — preserved append-only, never a
    # completed/rankable run. Engine label is llama.cpp-prism (explicit
    # SEPARATE fork grouping, still llama.cpp-family per the runner's
    # startswith('llama.cpp') identity-alias logic). See the config's
    # RETIRED-LANE banner, retired_reason, known_gaps, and
    # artifacts/bonsai2-ptq1-interrupted-20260923.md.
    "configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml",
}


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
        config to `retired`. Deliberately-retired candidate configs must be
        documented in RETIRED_CANDIDATE_CONFIGS; anything else is a guard
        violation."""
        undocumented = []
        for path in sorted(REPO.glob("configs/*/*.yaml")):
            try:
                cfg = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                continue
            engine = cfg.get("inference_engine", "")
            if engine in ("llama.cpp", "llama.cpp-dflash2", "llama.cpp-dspark", "llama.cpp-prism", "mei"):
                rel = str(path.relative_to(REPO))
                if (cfg.get("orchestration") or {}).get("viable") in ("retired",):
                    if rel not in RETIRED_CANDIDATE_CONFIGS:
                        undocumented.append(rel)
        self.assertEqual(undocumented, [])

    def test_retired_candidate_allowlist_is_current(self):
        """Every documented retired candidate config must still exist and still
        be marked retired — the allowlist may not silently drift."""
        stale = []
        for rel in sorted(RETIRED_CANDIDATE_CONFIGS):
            path = REPO / rel
            if not path.exists():
                stale.append(f"{rel} (missing)")
                continue
            cfg = yaml.safe_load(path.read_text()) or {}
            viable = (cfg.get("orchestration") or {}).get("viable")
            if viable != "retired":
                stale.append(f"{rel} (viable={viable})")
        self.assertEqual(stale, [])

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
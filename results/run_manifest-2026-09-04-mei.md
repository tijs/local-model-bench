# Mei-only fresh benchmark run — run manifest

Date: 2026-09-04 (UTC times)
Harness: local-model-bench @ `b293b2de057f` (clean; the oMLX/vllm-mlx lane-retirement
commit — retirement implementation commit for the append-only Mei run)
Runner: `uv run --locked python runner/run_bench.py --config configs/<model>/mei.yaml`
Methodology tags: `benchmark-v3` grading (sanity + hermes_ops + four coding suites).

## Headline

- **Gemma-4-26B-A4B/mei.yaml** — COMPLETED (full harness pass to terminal).
- **Ornith-1.5-35B-A3B/mei.yaml** — COMPLETED (full fertile suite battery).
- **Qwen3.8-27B-Uncensored/mei.yaml** — IN PROGRESS (hermes_ops phase; run left
  running in background). Dense 27B on the large ~64K hermes_ops prompts is
  impractically slow on this 32 GB M1 Max: each task 10–20+ min and several
  fail via `exceeded max_turns (40)` tool-loops; per-task tok/s is far below
  the 4.0 viability gate, so the harness is expected to speed-gate this leg.
- **Qwen3.8-27B/mei.yaml** — NOT YET RUN. Blocked sequentially by the
  one-server-at-a-time discipline while the (very slow) Uncensored leg occupies
  the Mei stack; same dense architecture is expected to exhibit the same
  catastrophic slowness/speed-gate.

This is a genuinely fresh, append-only run. The earlier Mei run (rows keyed to
`runner_git_sha 622d0ad`, config_hash `22dac305…`/Ornith-…) is NOT overwritten;
all new rows are keyed to `b293b2de057f` with fresh config hashes/timestamps.

## Clean-start checks (performed before each launch)

1. Verified no benchmark server/process was listening on bench ports
   (80xx range: 8012/8016/8017/8018/8020/8024/8025/8026/8027) and no
   `mei`/`vllm`/`llama-server`/`omlx` process was running. `run_bench.py`'s
   own `unload_all.sh` start-gate re-verified and stopped the benchmark's
   configured candidate backends (CoCore + fitness-profile mara-mlx), which
   is this repo's normal, documented start behavior.
2. Cleared stale Mei runtime/cache state from the earlier contaminated first
   run so cached KV/prefix state was not reused: removed the disposable
   `~/.local/share/local-model-bench/mei-runtime/kv-ornith-35B/` KV cache and
   the stale runtime `logs/`; removed the disposable gitignored
   `runner/.omlx-runtime/` (oMLX retired). Model weights under
   `~/…/mei-models/` and all historical `results/*` evidence were preserved.
3. Each Mei server is a fresh process on the config's dedicated port
   (Gemma 8027, Ornith 8024, Uncensored 8026, Qwen3.8-27B 8025), built from
   the pinned-scratch Swift build (below); in-memory paged KV starts fresh
   per launch.

## Exact configs (committed files → run-time config_hash)

| config | served model | port | config_hash (b293b2de rows) |
|---|---|---|---|
| configs/Gemma-4-26B-A4B/mei.yaml | mlx-community/gemma-4-26b-a4b-it-4bit | 8027 | `c9417ad40f57` |
| configs/Ornith-1.5-35B-A3B/mei.yaml | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | 8024 | `dc3e7e62a965` |
| configs/Qwen3.8-27B-Uncensored/mei.yaml | orcarouter/Qwen3.8-27B-Uncensored-MLX | 8026 | `9a0bccfab07b` |
| configs/Qwen3.8-27B/mei.yaml | mlx-community/Qwen3.8-27B-4bit | 8025 | `d23c67ad6d2d` (not yet run) |

Verbatim config snapshots saved by `bench_common.snapshot_config()` to
`results/configs/<config_hash>.yaml` on first run (append-only).

## Model roots / staging

All weights pre-staged under `~/.local/share/local-model-bench/mei-models/`
with provenance JSON alongside (preserved, not modified):
`gemma-4-26b-a4b-it-4bit`, `Ornith-1.5-35B-A3B-MLX-4bit-aligned`,
`Qwen3.8-27B-Uncensored-MLX-4bit`, `Qwen3.8-27B-4bit`.

## Runtime / build identity (Mei server)

- Mei Swift package: `~/projects/mei` (NOT part of this repo; not modified).
- Pinned scratch build dir: `~/.local/share/local-model-bench/mei-build-pinned-91fed8be/`
  serving binary `release/mei` (built 2026-09-04, resolves vmlx-swift at the
  pinned fork revision per `start_mei_server.sh`'s documented provenance).
- Launcher: `runner/start_mei_server.sh`; stop: `runner/stop_mei_server.sh`
  (always invoked in `run_bench.py`'s `finally` so no stale Metal model
  strands). Acceptance probe: `runner/probe_mei.py` → `run_mei_acceptance.py`
  per config (run_bench runs its own identity/load/completion gates too).

## Suite coverage (configured `orchestration.viable: full` for all four)

- sanity (2 tasks) — always run (fail-fast gate).
- hermes_ops — always run; speed gate applies (skip coding below 4.0 tok/s).
- coding suites: kiem_mini, hearth_mini, kipclip_mini, hearth_full (all tasks).

## Results collected so far (append-only, `results/log.jsonl` keyed to b293b2de)

| config | sanity | hermes_ops | coding (kiem/heart/kipclip/heart_full) | status |
|---|---|---|---|---|
| Gemma-4-26B-A4B | 2/2 | 6/8 | — (speed-gated) | complete |
| Ornith-1.5-35B-A3B | 2/2 | 6/8 | 4/5 · 3/3 · 4/4 · 3/3 | complete |
| Qwen3.8-27B-Uncensored | 2/2 | 1/3 so far | — (hermes_ops slow, in progress) | in progress |
| Qwen3.8-27B | — | — | — | not yet run |

Failure classification (all `harness_error: false` — model/engine-level):
- Gemma / Uncensored hermes_ops FAILs: model output shape / tool-loop issues
  (`max_turns` exhaustion, unexpected tool-name calls) = **model/engine**.
- Uncensored slowness: measured per-task tok/s far below the 4.0 viability
  gate = **model/engine speed** (harness speed-gate policy is expected to stop
  the coding suite, as it did for Gemma at avg 2.00 tok/s).
- No harness/environment errors in any fresh row.

## Skipped / blocked rows

- Github-Qwen dense models: coding-suite rows skipped by harness **speed gate**
  (not a harness bug) once hermes_ops clears below 4.0 t/s.
- **Qwen3.8-27B not yet run** — sequential discipline + the very slow Uncensored
  leg. Not fabricated; exact blocker is the dense-model throughput on the large
  hermes_ops prompts on this hardware, which the harness records honestly.
- Leaderboard rebuilt from the full append-only log (historical oMLX/vllm-mlx
  rows intact); oMLX/vllm-mlx configs render in the "Retired lanes" section.
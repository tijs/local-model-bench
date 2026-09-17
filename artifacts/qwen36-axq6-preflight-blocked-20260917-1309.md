# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 13:09 CEST)

**Status: BLOCKED.** The authorized AXQ 6-bit gate (plan todo 20) remains
blocked. No model was downloaded or staged, no probe ran, no server was
started/stopped, no benchmark ran, and no build was executed during this tick.

This is a report-only, CPU-only preflight artifact for the next authorized
research unit. Kiem was read-only; `results/` remains append-only; nothing was
committed or pushed.

## Tick facts (independently re-checked against the current checkout)

| Fact | Value | Label |
| --- | --- | --- |
| Tick timestamp | 2026-09-17 13:10 CEST (artifact fixed name 13:09) | measured |
| Pre-write checkout | `67ae7feb3c5c2e5133e25d133a8c7c5ce75ecbd4` on `main`, clean, ahead 64 of origin/main, nothing pushed | measured |
| Kiem CLI | `0.4.2` at `/Users/tijs/bin/kiem` | measured |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open todos at public indexes 13 (daily discovery), **20 (AXQ 6-bit gate — this unit)**, **21 (Gravity RL — queued)**; todo 19 (AXQ 4-bit) is closed | measured |
| Authorized serialized queue | AXQ 4-bit (COMPLETE, committed) -> **AXQ 6-bit (this unit, BLOCKED)** -> Gravity RL (queued) | decision |
| AXQ 4-bit commit evidence | config `48e4bbe` -> 25-row results `49b248d` -> audit re-pin `141e799` -> reconciliation `ddcdc18` on main | measured |
| Kiem mutation | none (read-only inspection) | measured |
| Physical memory | `34,359,738,368 B = 32 GiB` | measured |
| Overlapping benchmark/model process | none observed | measured |

## Disk gate (binding blocker: disk)

Fresh `shutil.disk_usage` sample of the data volume:

- Free (audited baseline): `55,836,782,592 B = 52.002056 GiB`
- Free (measured re-sample, first of four): `55,835,414,528 B = 52.000782 GiB`
  (samples ranged 52.000614–52.000782 GiB; delta vs baseline
  `1,368,064 B ≈ 1.30 MiB = 0.0024%` — sampling noise, immaterial)

Pinned AXQ 6-bit package/tree (carried pin, re-confirmed in plan todo 20 and
`artifacts/qwen36-decision-audit-post-mannix-complete-20260916.md`): **23 files,
`26,985,603,183 B = 25.132301 GiB`** at immutable revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`
(AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP, 5 shards, mlx/vision sidecars).

Gates (plan todo 20 requires all of: >= 51.5 GiB before staging, >= 30 GiB at
launch, >= 20 GiB post-staging):

- 51.5 GiB pre-staging component (`55,297,703,936 B`): free 52.002 GiB — **passes
  alone, but is not sufficient**
- **Required free before staging for the 30 GiB launch floor** (floor +
  tree = `32,212,254,720 + 26,985,603,183`): **`59,197,857,903 B =
  55.132301 GiB`** — **FAIL**
- **Shortfall: `3,361,075,311 B = 3.130245 GiB`** — **FAIL**

Hypothetical staging math (baseline free minus pinned tree):

- Post-stage free: `55,836,782,592 − 26,985,603,183 = 28,851,179,409 B =
  26.869755 GiB` — **below the 30 GiB launch gate (`32,212,254,720 B`) — FAIL**
  (would satisfy the 20 GiB post-staging floor, but the launch gate is binding)
- Physical memory 32 GiB is sufficient; **disk is the binding blocker**

All arithmetic re-verified independently (required, shortfall, post-stage — see
verification in final handoff). The AXQ 6-bit leg cannot start until a fresh
single-writer audit shows >= 59,197,857,903 B free before staging.

## Inventory, processes, evidence

- Expected staged path absent: `~/.local/share/local-model-bench/mei-models/`
  contains `AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (the completed prior leg) but
  **no** AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP entry or provenance (measured).
- Expected cache path absent: `~/.cache/huggingface/hub` holds no AXQ model
  entries (only EigenLabs/ManniX/mlx-community dirs) (measured).
- `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-*` does not exist (only the AXQ
  4-bit config dir) — no committed Mei config for this leg (measured).
- Process/listener preflight: zero benchmark/backend workload processes
  (mei/llama/mlx/run_bench/probe sweep) and **no listeners** on ports 8012,
  8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027 (measured). No process was
  stopped or restarted.
- Append-only evidence unchanged during this tick (measured):
  - `results/log.jsonl`: **4,145 nonblank rows**, `4,622,708` bytes. AXQ 4-bit:
    one complete 25-row group — `config_hash 984425a7e143`, `runner_git_sha
    48e4bbe5c88c`, model `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`,
    21 pass / 4 task-level grade fail, `run_error` none on all 25 (0 harness
    errors). **AXQ 6-bit: 0 rows.**
  - `results/LEADERBOARD.md`: `231,134` bytes, untouched.
- No result/config snapshot/transcript was generated (measured).

## Next gate

Do not download, stage, configure, probe, or benchmark AXQ 6-bit until a fresh
single-writer audit proves all of:

1. >= 59,197,857,903 B (55.132301 GiB) free before staging (30 GiB launch floor
   + pinned tree), and the plan's >= 51.5 GiB pre-staging component
2. >= 30 GiB free at launch
3. >= 20 GiB free post-staging
4. sufficient memory and one-server ownership

When eligible, run only served identity
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP` at pinned revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` with a committed Mei config on a
free 8020-family port (8025 unless a fresh audit selects another),
`VMLX_ENABLE_UNSAFE_COMPILE=0`, no unsafe compiled decode, plain and streaming
generation, native tools, and the 25-row battery (2 + 8 + 5 + 3 + 4 + 3). Keep
the result unranked until a complete current 25-row run passes. AXQ 6-bit must
complete and be committed before the queued Gravity RL slot
(`7f5c67e7…` todo 21) starts; do not reopen prior legs (OptiQ, DwarfStar,
Whittle, Nemotron, calibrated conversion, or cache deletion).

## Preservation rules

Preserve: committed config snapshot with exact identity/revision, append-only
log rows, all raw transcripts/prompt results, server log, runner SHA,
provenance, failure classification, and teardown/free-port evidence. Keep
`results/log.jsonl` and `results/LEADERBOARD.md` append-only; never hand-edit.
No push and no GitHub activity for this artifact; the parent orchestrator
commits it after handoff.

## Scope note

This tick performed **no model action**: nothing downloaded, staged, launched,
probed, benchmarked, killed, restarted, or built. Kiem and the repo were
read-only; change is limited to this single report artifact.
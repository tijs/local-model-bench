# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 14:16 CEST)

**Status: BLOCKED.** The authorized AXQ 6-bit gate (plan todo 20) remains
blocked. No model was downloaded or staged, no probe ran, no server was
started/stopped, no benchmark ran, and no build was executed during this tick.

This is a report-only, CPU-only preflight artifact for the next authorized
research unit. Kiem was read-only; `results/` remains append-only; nothing was
committed or pushed.

## Tick facts (independently re-checked against the current checkout)

| Fact | Value | Label |
| --- | --- | --- |
| Tick timestamp | 2026-09-17 14:16 CEST (artifact fixed name 14:16) | measured |
| Pre-write checkout | `687b3027447382b2cd8ccf86542159e0a696d8ed` on `main`, clean, ahead 65 of origin/main, nothing pushed | measured |
| Kiem CLI | `0.4.2` at `/Users/tijs/bin/kiem` | measured |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open todos at public indexes 13 (daily discovery), **20 (AXQ 6-bit gate — this unit)**, **21 (Gravity RL — queued)**; todo 19 (AXQ 4-bit) does not appear among open todos (closed) | measured |
| Authorized serialized queue | AXQ 4-bit (COMPLETE, committed) -> **AXQ 6-bit (this unit, BLOCKED)** -> Gravity RL (queued) | decision |
| Kiem mutation | none (read-only inspection only) | measured |
| Physical memory | `34,359,738,368 B = 32 GiB`; system-wide memory free 92% (`memory_pressure`); swap total 3,072 MB / used 1,398.81 MB | measured |
| Overlapping benchmark/model process | none observed; no foreign process terminated | measured |

## Disk gate (binding blocker: disk; both sub-gates now FAIL)

Fresh `shutil.disk_usage` samples of the data volume (four consecutive):

- Free (audited baseline, first tick 13:09): `55,835,414,528 B = 52.000782 GiB`
- Free (measured re-sample, 4 samples, all identical): `54,936,621,056 B =
  51.163715 GiB` (delta vs prior tick `−898,793,472 B ≈ −0.857 GiB`; the disk
  has continued to shrink; one earlier single sample read
  `54,936,637,440 B` — ±16 KiB sampling noise, immaterial)
- `df -k` cross-check: Available `53,648,944` KiB = `54,936,518,656 B`
  (≈ 116 KiB below the shutil sample; same apparent free, immaterial)

Pinned AXQ 6-bit package/tree (plan todo 20): **`26,985,603,183 B =
25.132301 GiB`** at immutable revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`
(AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP).

Gates (plan todo 20 requires all of: >= 51.5 GiB before staging, >= 30 GiB at
launch, >= 20 GiB post-staging):

- 51.5 GiB pre-staging component (`55,297,703,936 B`): free 51.164 GiB —
  **FAIL by `361,082,880 B = 0.336285 GiB`** (was passing alone at 13:09)
- **Required free before staging for the 30 GiB launch floor** (floor +
  tree = `32,212,254,720 + 26,985,603,183`): **`59,197,857,903 B =
  55.132301 GiB`** — **FAIL**
- **Shortfall vs required: `4,261,236,847 B = 3.968586 GiB`** — **FAIL**

Hypothetical staging math (measured free minus pinned tree):

- Post-stage free: `54,936,621,056 − 26,985,603,183 = 27,951,017,873 B =
  26.031414 GiB` — **below the 30 GiB launch gate (`32,212,254,720 B`) — FAIL**
  (would satisfy the 20 GiB post-staging floor, but the launch gate is binding)
- Physical memory 32 GiB is sufficient; **disk is the binding blocker**, and
  the situation has worsened since the 13:09 tick (free dropped ~0.86 GiB).

All arithmetic re-verified independently in this tick (required, shortfall,
post-stage — see final handoff). The AXQ 6-bit leg cannot start until a fresh
single-writer audit shows >= 59,197,857,903 B free before staging.

## Inventory, processes, evidence

- Expected staged path absent (measured): `~/.local/share/local-model-bench/
  mei-models/` contains `AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (+ provenance,
  `axq4-staging.log`, `verify_axq4_tree.py`) and prior legs, but **no**
  AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP entry or provenance.
- Expected cache path absent (measured): `~/.cache/huggingface/hub` holds only
  EigenLabs/ManniX/mlx-community entries — **no AXQ entries**.
- `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-*` does not exist (only the AXQ
  4-bit config dir); no tracked or untracked AXQ 6-bit config (measured).
- Process/listener preflight: zero benchmark/backend/model workload processes
  (mei/mei_server/llama/mlx_lm/vmlx/gguf/run_bench/probe sweep) and **no
  listeners** on ports 8012, 8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027
  (measured). Only Hermes infrastructure processes present (gateway 46167,
  dashboard 96369, MCP servers, tailnet router, kernel runner). No process was
  stopped or restarted.
- Append-only evidence unchanged during this tick (measured):
  - `results/log.jsonl`: **4,145 nonblank rows**, `4,622,708` bytes. AXQ 4-bit:
    one complete 25-row group — `config_hash 984425a7e143`, `runner_git_sha
    48e4bbe5c88c`, model `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`,
    suite mix 2 sanity + 8 hermes_ops + 5 kiem_mini + 3 hearth_mini +
    4 kipclip_mini + 3 hearth_full = 25, **21 pass / 4 task-level grade fail**,
    `run_error` none on all 25 and `harness_error` empty on all 25
    (0 harness errors). **AXQ 6-bit: 0 rows.** Reconciliation only; no rows
    edited.
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
# Qwen3.6 AXQ 4-bit — preflight blocker (2026-09-17 07:55 CEST)

**Status: BLOCKED.** The authorized AXQ 4-bit gate remains blocked. No model was
downloaded or staged, no probe ran, no server was started/stopped, no benchmark
ran, and no build was executed during this tick.

This is a report-only, CPU-only preflight artifact for the current research
tick. Kiem was read-only; results remain append-only.

## Tick facts

| Fact | Value | Label |
| --- | --- | --- |
| Tick timestamp | 2026-09-17 07:55 CEST | measured |
| Pre-write checkout HEAD | `ae7d759dd4cca9acdbc81f772456730d0d98bd12` on `main`, ahead 57 / behind 0 of origin/main, clean | measured |
| Prior artifact commit | `artifacts: record AXQ 4-bit preflight blocker 2026-09-17 06:50` | carried |
| Kiem CLI | 0.4.2 | measured |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2` (read-only); target todo 19 (AXQ 4-bit) and todo 20 (AXQ 6-bit) open | measured |
| Authorized serialized queue | AXQ 4-bit -> AXQ 6-bit -> gated Gravity | decision |
| Kiem mutation | none | measured |
| Hermes cron writer job | `ba2552668fdf` (Qwen3.6 writer, 60-minute schedule) | measured |
| Hermes cron discovery job | daily, scheduled 08:00 | measured |
| Overlapping benchmark/model process | none observed | measured |

## Disk gate (binding)

Fresh `shutil.disk_usage` sample:

- Free: `54,307,774,464 B = 50.578056335449 GiB = 54.307774464 decimal GB`
- Pre-staging threshold required: `51.5 GiB = 55,297,703,936 B`
- Shortfall: `989,929,472 B = 0.921943664551 GiB` — **FAIL**

## Hypothetical staging math

Carried pinned AXQ 4-bit public package size: `23,120,765,421 B`, revision
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24` (carried).

If staged hypothetically:

- Remaining disk: `31,187,009,043 B = 29.045165556483 GiB`
- Launch gate: `30 GiB`; shortfall `1,025,245,677 B = 0.954834443517 GiB` — **FAIL**
- Post-staging floor would have margin `9,712,172,563 B = 9.045165556483 GiB`
  vs the 20 GiB floor, but this does not override the failed pre-staging and
  launch gates
- Physical memory: `34,359,738,368 B (32 GiB)` — sufficient; disk is binding

## Inventory, processes, evidence

- Bounded inventory found zero AXQ/AutomatosX matches under repo `configs/`,
  `~/.local/share/local-model-bench/mei-models/`, and
  `~/.cache/huggingface/hub`; no existing-cache path and no Mei/vmlx
  compatibility evidence (measured).
- Process/listener preflight found zero matching benchmark/server workload
  processes and no listeners on benchmark ports 8012, 8016, 8017, 8018, 8020,
  8024, 8025, 8026, 8027 (also no listeners on 8080, 8082, 8090, 11434). No
  process was stopped or restarted (measured).
- Append-only evidence unchanged (measured):
  - `results/log.jsonl`: 4,591,611 bytes, 4,120 nonblank rows, SHA-256
    `e25da61d7ef02eeb84b8aaeb8fcf242c89323284d7b2f257abebedfbeefe20ae`
  - `results/LEADERBOARD.md`: 229,585 bytes, SHA-256
    `54998b73df523f1b69f97fe3b637892d021aee2a8e813832d51c2308e803e0df`
  - Last completed ManniX row: `f4e4206eab5c / hearth_full-testwrite`
- No result/config snapshot/transcript was generated (measured).

## Next gate

Do not download, stage, configure, probe, or benchmark AXQ 4-bit until a fresh
single-writer audit proves:

1. >= 51.5 GiB free before staging
2. >= 30 GiB free at launch
3. >= 20 GiB free post-staging
4. sufficient memory

When eligible, run only served identity
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` at pinned revision
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24` with safe decode
(`VMLX_ENABLE_UNSAFE_COMPILE=0`, no unsafe compiled decode), port 8024, and the
25-row shape 2 + 8 + 5 + 3 + 4 + 3. Keep AXQ 6-bit/Gravity behind it. Do not
reopen OptiQ, DwarfStar, Whittle, Nemotron, calibrated conversion, or cache
deletion.
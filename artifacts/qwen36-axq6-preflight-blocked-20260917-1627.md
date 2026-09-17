# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 16:27 CEST)

**Status: BLOCKED (binding disk gate).** The authorized AXQ 6-bit gate (plan
todo 20) remains blocked: the free-disk requirement to retain the 30 GiB launch
floor after staging is not met. No model was downloaded, staged, probed, built,
launched, stopped, benchmarked, or killed during this tick.

This tick performed **CPU-side reconciliation only** — read-only re-checks of
the repository, disk, memory, process/port inventory, staging/cache paths, and
config identity; no writes outside this single report artifact. Kiem was
read-only; `results/` remains append-only; nothing was pushed.

## Tick facts (measured versus carried)

| Fact | Value | Label |
| --- | --- | --- |
| Tick timestamp | 2026-09-17 16:27 CEST (artifact fixed name 16:27; written 16:28) | measured |
| Pre-write checkout | `819c3dcab3a52176b34087258f8941fc014039fa` on `main`, clean (no tracked or untracked changes), ahead 67 of origin/main, nothing pushed | measured |
| Kiem CLI | `0.4.2` at `/Users/tijs/bin/kiem` | measured |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos at public indexes **13 (daily discovery)**, **20 (AXQ 6-bit gate — this unit)**, **21 (Gravity RL — queued)**; todo 19 (AXQ 4-bit) absent from open todos (prior terminal committed leg) | carried (read-only Kiem inspection) |
| Kiem mutation | none (read-only `--help`/`todos`/`show` only) | measured |
| Authorized serialized queue | AXQ 4-bit (COMPLETE, committed) -> **AXQ 6-bit (this unit, BLOCKED)** -> Gravity RL (queued) | decision |
| Physical memory | `34,359,738,368 B = 32 GiB` exactly; `memory_pressure` pages free `1,467,840` × 16,384 = `24,049,090,560 B ≈ 22.397 GiB` free pages — sufficient; disk is the binding blocker | measured |
| Overlapping benchmark/model process | none observed; no foreign process terminated | measured |
| Pinned AXQ 6-bit tree | `26,985,603,183 B = 25.132301434 GiB` at immutable Hub revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` (AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP) | carried (pinned Hub listing; not staged locally) |
| Parent-carried free (prior preflight) | `56,020,873,216 B = 52.173503876 GiB` | carried |

## Disk gate (binding blocker: disk)

Fresh preflight `shutil.disk_usage` samples of the data volume — three
consecutive samples, all identical:

- Free (preflight): **`56,017,743,872 B = 52.170589447 GiB`**

Independent cross-check at tick start, `df -k`: `54,706,780` KiB =
`56,019,742,720 B` — within ~2 MiB of the shutil samples (immaterial sampling
drift on a draining disk; the shutil value is used for all gate arithmetic
below). Versus the parent-carried `56,020,873,216 B`, the fresh measurement is
`3,129,344 B ≈ 0.002914 GiB ≈ 2.98 MiB` **lower** — materially unchanged; the
expected continued-block outcome is confirmed.

Pinned AXQ 6-bit package/tree (plan todo 20): **`26,985,603,183 B =
25.132301434 GiB`** at revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`.

Gates (plan todo 20 requires all of: >= 51.5 GiB before staging, >= 30 GiB at
launch, >= 20 GiB post-staging):

- 51.5 GiB pre-staging component (`55,297,703,936 B`, exactly 51.5 GiB):
  `56,017,743,872 − 55,297,703,936 = 720,039,936 B = 0.670589447 GiB` — **PASS**
  (component only)
- **Required free before staging for the 30 GiB launch floor** (floor +
  tree = `32,212,254,720 + 26,985,603,183`): **`59,197,857,903 B =
  55.132301434 GiB`** — **FAIL**
- **Shortfall vs required: `59,197,857,903 − 56,017,743,872 = 3,180,114,031 B =
  2.961711987 GiB`** — **FAIL**

Hypothetical staging math (preflight free minus pinned tree):

- Post-stage free: `56,017,743,872 − 26,985,603,183 = 29,032,140,689 B =
  27.038288013 GiB` — **below the 30 GiB launch gate (`32,212,254,720 B`) —
  FAIL** (short by the same `3,180,114,031 B = 2.961711987 GiB`; it would
  satisfy the 20 GiB post-staging floor `21,474,836,480 B` with `7,557,304,209
  B` to spare, but the binding launch gate is not met)
- Physical memory 32 GiB is sufficient; **disk is the binding blocker**. The
  fresh measurement is ~1.06 GiB better than the prior tick's (15:21: free was
  `56,032,436,224 B / 52.184272766 GiB`, shortfall `3,165,421,679 B ≈ 2.948
  GiB`), but essentially unchanged and still short of the binding requirement.

All arithmetic re-verified independently in this tick (pass margin, required,
shortfall, post-stage, 20 GiB floor). The AXQ 6-bit leg cannot start until a
fresh single-writer audit shows >= 59,197,857,903 B free before staging.

## Inventory, processes, evidence

- Expected staged path absent (measured): `~/.local/share/local-model-bench/
  mei-models/` contains `AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (+ provenance,
  `axq4-staging.log`, `verify_axq4_tree.py`) and prior legs, but **no**
  AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP entry, provenance, or staging log.
- Expected cache path absent (measured): `~/.cache/huggingface/hub` holds no
  AXQ entries (only EigenLabs mixed-4bit, ManniX GGUF, mlx-community 4bit /
  4bit-DWQ).
- `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-*` does not exist; only the AXQ
  4-bit config dir (`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/mei.yaml`) is
  present; no tracked or untracked AXQ 6-bit config (measured; working tree
  fully clean).
- Process/listener preflight: zero benchmark/backend/model workload processes
  (mei/mei_server/llama/mlx_lm/vmlx/run_bench/probe sweep — only system
  daemons and the unrelated hermes marktplaats capability server matched
  "server") and **no listeners** on ports 8012, 8016, 8017, 8018, 8020, 8024,
  8025, 8026, 8027 (measured). No process was stopped, started, or restarted.
- Append-only evidence unchanged during this tick (measured):
  - `results/log.jsonl`: **4,145 rows**, `4,622,708` bytes — identical to the
    prior tick's counts, untouched. AXQ 6-bit: 0 rows. Reconciliation only; no
    rows edited.
  - `results/LEADERBOARD.md`: `231,134` bytes — identical to the prior tick's
    count, untouched.
- No result/config snapshot/transcript was generated (measured).

## Next gate

Do not download, stage, configure, probe, or benchmark AXQ 6-bit until a fresh
single-writer audit proves all of:

1. **>= 59,197,857,903 B (55.132301434 GiB) free before staging** (30 GiB
   launch floor + pinned tree `26,985,603,183 B`), and the plan's >= 51.5 GiB
   pre-staging component
2. >= 30 GiB free at launch
3. >= 20 GiB free post-staging
4. sufficient memory and one-server ownership, plus launch/identity/teardown
   requirements (served identity, pinned revision, free 8020-family port —
   pin 8025 unless a fresh audit selects another, committed Mei config,
   VMLX_ENABLE_UNSAFE_COMPILE=0, plain and streaming generation, native tools,
   teardown/free-port evidence)

Do not consider Gravity RL (plan todo 21) until AXQ 6-bit is terminal and
committed; do not reopen prior legs (OptiQ, DwarfStar, Whittle, Nemotron,
calibrated conversion, or cache deletion).

## Preservation rules

Preserve: committed config snapshot with exact identity/revision, append-only
log rows, all raw transcripts/prompt results, server log, runner SHA,
provenance, failure classification, and teardown/free-port evidence. Keep
`results/log.jsonl` and `results/LEADERBOARD.md` append-only; never hand-edit.
No push and no GitHub activity.

## Scope note

This tick performed **no model action**: nothing downloaded, staged, launched,
probed, benchmarked, killed, restarted, or built. Kiem and the repo were
read-only; the only change is this single report artifact
(`artifacts/qwen36-axq6-preflight-blocked-20260917-1627.md`), committed alone
with a focused message.
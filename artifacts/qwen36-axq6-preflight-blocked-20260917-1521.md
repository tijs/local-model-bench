# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 15:21 CEST)

**Status: BLOCKED (binding disk gate).** The authorized AXQ 6-bit gate (plan
todo 20) remains blocked: the free-disk requirement to retain the 30 GiB launch
floor after staging is not met. No model was downloaded or staged, no probe
ran, no server was started/stopped, no benchmark ran, and no build was executed
during this tick.

This tick performed **CPU-side reconciliation only** — read-only re-checks of
the repository, disk, memory, process/port inventory, staging/cache paths, and
config identity; no writes outside this single report artifact. Kiem was
read-only; `results/` remains append-only; nothing was pushed.

## Tick facts (measured versus carried)

| Fact | Value | Label |
| --- | --- | --- |
| Tick timestamp | 2026-09-17 15:21 CEST (artifact fixed name 15:21; written 15:22) | measured |
| Pre-write checkout | `916fbd42d259fa3f70266f2119b715c1716c52dc` on `main`, clean, ahead 66 of origin/main, nothing pushed | measured |
| Kiem CLI | `0.4.2` at `/Users/tijs/bin/kiem` | measured |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos at public indexes **13 (daily discovery)**, **20 (AXQ 6-bit gate — this unit)**, **21 (Gravity RL — queued)**; todo 19 (AXQ 4-bit) does not appear among open todos (closed; AXQ 4-bit is the prior terminal committed leg) | carried (read-only Kiem inspection) |
| Kiem mutation | none (read-only inspection only) | measured |
| Authorized serialized queue | AXQ 4-bit (COMPLETE, committed) -> **AXQ 6-bit (this unit, BLOCKED)** -> Gravity RL (queued) | decision |
| Physical memory | `34,359,738,368 B = 32 GiB`; system-wide memory free 92% (`memory_pressure`); swap total `2048.00M`, used `1253.81M`, free `794.19M` | measured |
| Overlapping benchmark/model process | none observed; no foreign process terminated | measured |
| Pinned AXQ 6-bit tree | `26,985,603,183 B = 25.132301434 GiB` at immutable Hub revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` (AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP) | carried (pinned Hub listing; not staged locally) |

## Disk gate (binding blocker: disk)

Fresh preflight `shutil.disk_usage` samples of the data volume — three
consecutive samples, all identical:

- Free (preflight): **`56,032,436,224 B = 52.184272766 GiB`**

Independent re-check during this tick (three consecutive samples, all
identical): `56,031,866,880 B = 52.183742523 GiB` — `569,344 B ≈ 0.000530 GiB`
lower than the preflight sample (≈ 556 KiB). The difference is immaterial
sampling drift on a disk that has been draining between ticks; the preflight
value is used for all gate arithmetic below.

Pinned AXQ 6-bit package/tree (plan todo 20): **`26,985,603,183 B =
25.132301434 GiB`** at revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`.

Gates (plan todo 20 requires all of: >= 51.5 GiB before staging, >= 30 GiB at
launch, >= 20 GiB post-staging):

- 51.5 GiB pre-staging component (`55,297,703,936 B`, exactly 51.5 GiB):
  `56,032,436,224 − 55,297,703,936 = 734,732,288 B = 0.684272766 GiB` — **PASS**
- **Required free before staging for the 30 GiB launch floor** (floor +
  tree = `32,212,254,720 + 26,985,603,183`): **`59,197,857,903 B =
  55.132301434 GiB`** — **FAIL**
- **Shortfall vs required: `59,197,857,903 − 56,032,436,224 = 3,165,421,679 B =
  2.948028668 GiB`** — **FAIL**

Hypothetical staging math (preflight free minus pinned tree):

- Post-stage free: `56,032,436,224 − 26,985,603,183 = 29,046,833,041 B =
  27.051971332 GiB` — **below the 30 GiB launch gate (`32,212,254,720 B`) —
  FAIL** (and short by the same `3,165,421,679 B = 2.948028668 GiB`; it would
  satisfy the 20 GiB post-staging floor, but the binding launch gate is not
  met)
- Physical memory 32 GiB is sufficient; **disk is the binding blocker**. This
  tick's measurement is ~10.9 GiB better than the prior tick's (14:16: free
  was 54,936,621,056 B / 51.163715 GiB, shortfall 4,261,236,847 B ≈ 3.97 GiB),
  but still short of the binding requirement.

All arithmetic re-verified independently in this tick (pass margin, required,
shortfall, post-stage). The AXQ 6-bit leg cannot start until a fresh
single-writer audit shows >= 59,197,857,903 B free before staging.

## Inventory, processes, evidence

- Expected staged path absent (measured): `~/.local/share/local-model-bench/
  mei-models/` contains `AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (+ provenance,
  `axq4-staging.log`, `verify_axq4_tree.py`) and prior legs, but **no**
  AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP entry or provenance.
- Expected cache path absent (measured): `~/.cache/huggingface/hub` holds no
  AXQ entries.
- `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-*` does not exist; only the AXQ
  4-bit config dir (`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`) is present;
  no tracked or untracked AXQ 6-bit config (measured).
- Process/listener preflight: zero benchmark/backend/model workload processes
  (mei/mei_server/llama/mlx_lm/vmlx/run_bench/probe sweep) and **no listeners**
  on ports 8012, 8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027 (measured).
  No process was stopped, started, or restarted.
- Append-only evidence unchanged during this tick (measured):
  - `results/log.jsonl`: **4,145 rows**, `4,622,708` bytes, untouched. AXQ
    6-bit: 0 rows. Reconciliation only; no rows edited.
  - `results/LEADERBOARD.md`: `231,134` bytes, untouched.
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
   requirements (served identity, pinned revision, free port, committed config,
   teardown/free-port evidence)

Do not consider Gravity RL (plan todo 21) until AXQ 6-bit is terminal and
committed; do not reopen prior legs (OptiQ, DwarfStar, Whittle, Nemotron,
calibrated conversion, or cache deletion).

## Preservation rules

Preserve: committed config snapshot with exact identity/revision, append-only
log rows, all raw transcripts/prompt results, server log, runner SHA,
provenance, failure classification, and teardown/free-port evidence. Keep
`results/log.jsonl` and `results/LEADERBOARD.md` append-only; never hand-edit.
No push and no GitHub activity; the parent orchestrator commits this artifact
after handoff.

## Scope note

This tick performed **no model action**: nothing downloaded, staged, launched,
probed, benchmarked, killed, restarted, or built. Kiem and the repo were
read-only; the only change is this single report artifact
(`artifacts/qwen36-axq6-preflight-blocked-20260917-1521.md`).
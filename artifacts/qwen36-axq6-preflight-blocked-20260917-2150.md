# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 21:50 CEST)

**Status: BLOCKED (binding pre-staging disk threshold).** The authorized AXQ 6-bit
gate (Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`, todo 20) remains below the
required free space to retain the 30 GiB launch floor after staging. No model was
downloaded, staged, probed, built, launched, stopped, benchmarked, deleted, or
killed during this tick.

This tick performed CPU-only, report-only reconciliation. Kiem was read-only
(`show`/`todos` only; note `7f5c67e7…` last modified `2026-09-17T09:24:41Z`,
version `ab1150c4…`, unmutated by this tick); `results/` remains append-only;
nothing was pushed and no foreign process was terminated.

## Measured state (verified before writing)

| Fact | Value |
| --- | --- |
| Tick timestamp | 2026-09-17 21:50 CEST (live re-reads 21:52 CEST) |
| Checkout | `d225163be4991856d6b3567e8d508f56be639bfa` (`d225163`) on `main`, clean, ahead 71 of `origin/main` |
| Kiem | `0.4.2` at `/Users/tijs/bin/kiem` |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos 13, 20, 21 |
| AXQ 6-bit pinned tree | `26,985,603,183 B` = `25.132301434 GiB`, AutomatosX revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` (plan todo 20) |
| Physical memory | `34,359,738,368 B` = `32 GiB` (exactly 32 × 1,073,741,824); `hw.ncpu` = 10; vm_stat free pages `1,291,818` × 16,384 B = `21,165,146,112 B` = `19.71 GiB`; `memory_pressure -Q` 91% free |
| Benchmark/model processes | none observed (only the Kiem CLI `sync` daemon, PID 54636, and macOS system daemons) |
| Benchmark listeners | none on 8012, 8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027 |
| Results | `results/log.jsonl`: 4,145 rows; 25 AXQ 4-bit rows (21 pass / 4 fail, exact model id `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`); **zero** AXQ 6-bit rows (`AXQ-6bit`, `6bit`, `6-bit`, `axq6` all 0 matches) |

The expected staged model tree, provenance sidecar, and AXQ 6-bit config are
absent: `configs/` holds only the AXQ 4-bit candidate
(`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/`), and no `*axq6*`/`6-bit` files
exist outside this blocker series in `artifacts/`.

AXQ 4-bit evidence remains terminal and committed
(`artifacts/qwen36-axq4-native-gate-20260917.md`, 12/12, and
`artifacts/qwen36-axq4-full-coding-20260917.md`, complete 25-row battery). The
Gravity RL leg (plan todo 21) is serialized **after** AXQ 6-bit.

## Disk gate (binding pre-staging threshold)

Fresh measurement for the benchmark data volume (diskutil Container Free Space on
`/System/Volumes/Data`, tick-authoritative preflight reading used as the gate
comparison):

- Free: **`56,148,180,992 B` = `52.292068481 GiB`**.
- The standalone plan component of at least 51.5 GiB still passes
  (51.5 GiB = `55,297,703,936 B`), but the binding threshold is the full
  pre-staging requirement.
- Required free before staging to preserve the 30 GiB launch floor after staging:
  `32,212,254,720 B` (30 GiB) + `26,985,603,183 B` (pinned tree) =
  **`59,197,857,903 B` = `55.132301434 GiB`** (`32,212,254,720 + 26,985,603,183 =
  59,197,857,903` verified).
- Shortfall: **`3,049,676,911 B` = `2.840232952 GiB`**.
- Hypothetical post-stage free space: `56,148,180,992 B − 26,985,603,183 B` =
  **`29,162,577,809 B` = `27.159767048 GiB`**, which is below the 30 GiB launch
  gate (`32,212,254,720 B`, short by `3,049,676,911 B`) but above the 20 GiB
  floor (`21,474,836,480 B`, surplus `7,687,741,329 B`); the 30 GiB launch gate
  is binding.

Independent re-read taken during this tick:

- `df -Pk` on the volume: `54,832,204` KiB = `56,148,176,896 B` =
  `52.292064667 GiB`; shortfall `3,049,681,007 B` = `2.840236767 GiB`;
  hypothetical post-stage `29,162,573,713 B` = `27.159763233 GiB`.

Both readings are ~2.84 GiB below the required `59,197,857,903 B` and both
hypothetical post-stage values land below the 30 GiB launch gate; the gate remains
**BLOCKED** under every measurement. No cache or model payload was deleted.

## Verification trace

`git rev-parse HEAD` → `d225163be4991856d6b3567e8d508f56be639bfa`; `git status` →
clean, ahead 71 (re-read immediately before writing). `diskutil info
/System/Volumes/Data` → Container Free Space `56,148,180,992 B` (exactly
`109,664,416` 512-byte units); `df -Pk /System/Volumes/Data` → Available
`54,832,204` KiB; `sysctl hw.memsize` → `34359738368`; `lsof -nP
-iTCP:8012 -iTCP:8016 -iTCP:8017 -iTCP:8018 -iTCP:8020 -iTCP:8024 -iTCP:8025
-iTCP:8026 -iTCP:8027 -sTCP:LISTEN` → exit 1, no listener; `ps -axo
pid,ppid,etime,command` → no llama/mei/mlx/vllm/qwen/run_bench process, only the
kiem sync daemon (PID 54636); `kiem show 7f5c67e7-…` + `kiem todos` → note
modified `2026-09-17T09:24:41.727523Z`, open todos 13/20/21 with the exact AXQ
6-bit pin, 25-row battery, and post-AXQ6 Gravity RL queue; JSONL inventory via
`awk`/`grep` → 4,145 rows, 25 rows at exact model id
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (21 pass / 4 fail), 0 rows
referencing AXQ 6-bit.

## Preservation and next gate

Do not download, stage, configure, probe, or benchmark AXQ 6-bit until a fresh
single-writer audit proves **all** of the following:

1. At least `59,197,857,903 B` (`55.132301434 GiB`) free before staging;
2. at least 30 GiB free at launch and at least 20 GiB after staging;
3. sufficient memory and one-server ownership;
4. a free 8020-family port (pin **8025** unless a fresh audit selects another);
5. exact served identity and Hub revision
   `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`;
6. `VMLX_ENABLE_UNSAFE_COMPILE=0` and no unsafe compiled decode.

Once eligible: create and commit the exact Mei config, run the native gate
(plain/streaming generation and native tools), then run only the AXQ 6-bit
25-row battery (2 sanity + 8 hermes_ops + 5 kiem_mini + 3 hearth_mini +
4 kipclip_mini + 3 hearth_full). Archive the server log, review every partial or
failed run, commit the evidence, and tear down (free the port) before any Gravity
RL leg may be considered. Keep config snapshot, provenance, raw transcripts,
server log, runner SHA, classification, and teardown evidence separate from
AXQ 4-bit.

This tick's only repository change is this report artifact; no model artifact,
benchmark row, Kiem mutation, or runtime state was created.
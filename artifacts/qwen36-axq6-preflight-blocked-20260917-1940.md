# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 19:40 CEST)

**Status: BLOCKED (binding pre-staging disk threshold).** The authorized AXQ 6-bit
gate (Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`, todo 20) remains below the
required free space to retain the 30 GiB launch floor after staging. No model was
downloaded, staged, probed, built, launched, stopped, benchmarked, deleted, or
killed during this tick.

This tick performed CPU-only, report-only reconciliation. Kiem was read-only
(`show`/`todos`/`notes` only; note `7f5c67e7…` last modified `2026-09-17T09:24:41Z`,
unmutated by this tick); `results/` remains append-only; nothing was pushed and no
foreign process was terminated.

## Measured state (verified before writing)

| Fact | Value |
| --- | --- |
| Tick timestamp | 2026-09-17 19:40 CEST (live re-reads 19:42 CEST) |
| Checkout | `26ab3729cd0dc86091af4f4592ef3565a43d5bfc` (`26ab372`) on `main`, clean, ahead 70 of `origin/main` |
| Kiem | `0.4.2` at `/Users/tijs/bin/kiem` |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos 13, 20, 21 |
| AXQ 6-bit pinned tree | `26,985,603,183 B` = `25.132301434 GiB`, AutomatosX revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` (plan todo 20) |
| Physical memory | `34,359,738,368 B` = `32 GiB` (exactly 32 × 1,073,741,824); `hw.ncpu` = 10 |
| Benchmark/model processes | none observed (only the Kiem CLI `sync` daemon, PID 54636, and macOS system daemons) |
| Benchmark listeners | none on 8012, 8016, 8017, 8018, 8020, 8021, 8022, 8023, 8024, 8025, 8026, 8027 |
| Results | `results/log.jsonl`: 4,145 rows; 25 AXQ 4-bit rows (21 pass / 4 fail / 0 harness errors); **zero** AXQ 6-bit rows |

The expected staged model tree, provenance sidecar, and AXQ 6-bit config are
absent: `configs/` holds only the AXQ 4-bit candidate
(`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/`), and no `*axq6*`/`6-bit` files
exist outside this blocker series in `artifacts/`.

AXQ 4-bit evidence remains terminal and committed
(`artifacts/qwen36-axq4-native-gate-20260917.md`, 12/12, and
`artifacts/qwen36-axq4-full-coding-20260917.md`, complete 25-row battery). The
Gravity RL leg (plan todo 21) is serialized **after** AXQ 6-bit.

## Disk gate (binding pre-staging threshold)

Fresh measurement for the benchmark data volume (tick-authoritative preflight
reading used as the gate comparison):

- Free: **`56,157,229,056 B` = `52.300495148 GiB`**.
- The standalone plan component of at least 51.5 GiB still passes
  (51.5 GiB = `55,297,703,936 B`), but the binding threshold is the full
  pre-staging requirement.
- Required free before staging to preserve the 30 GiB launch floor after staging:
  `32,212,254,720 B` (30 GiB) + `26,985,603,183 B` (pinned tree) =
  **`59,197,857,903 B` = `55.132301434 GiB`**.
- Shortfall: **`3,040,628,847 B` = `2.831806286 GiB`**.
- Hypothetical post-stage free space: `56,157,229,056 B − 26,985,603,183 B` =
  **`29,171,625,873 B` = `27.168193714 GiB`**, which is below the 30 GiB launch
  gate (`32,212,254,720 B`) but above the 20 GiB floor (`21,474,836,480 B`);
  the 30 GiB launch gate is binding.

Independent re-reads taken during this tick:

- `df -k` on the volume: `56,160,620,544 B` = `52.303653717 GiB`; shortfall
  `3,037,237,359 B` = `2.828647717 GiB`; hypothetical post-stage
  `29,175,017,361 B` = `27.171352283 GiB`.
- `shutil.disk_usage` on the repo path, moments later: `56,158,224,384 B` =
  `52.301422119 GiB`; shortfall `3,039,633,519 B` = `2.830879315 GiB`;
  hypothetical post-stage `29,172,621,201 B` = `27.169120685 GiB`.

All three readings are ~2.83 GiB below the required `59,197,857,903 B` and all
hypothetical post-stage values land below the 30 GiB launch gate; the gate remains
**BLOCKED** under every measurement. No cache or model payload was deleted.

## Verification trace

`git rev-parse HEAD` → `26ab3729cd0dc86091af4f4592ef3565a43d5bfc`; `git status` →
clean, ahead 70. `df -k /Users/tijs/projects/local-model-bench` → Available
`54,844,356` KiB (= `56,160,620,544 B`); `sysctl hw.memsize` → `34359738368`;
`lsof -nP -iTCP -sTCP:LISTEN` → no listener on 8012/8016–8018/8020–8027;
`ps aux` → no llama/mei/mlx/vllm/qwen/`run_bench` process, only the kiem sync
daemon; `kiem show 7f5c67e7-…` + `kiem todos` → open todos 13/20/21 with the
exact AXQ 6-bit pin, 25-row battery, and post-AXQ6 Gravity RL queue; JSONL
inventory via Python → 4,145 rows, 25 rows at exact model id
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (`pass=True` 21, `pass=False` 4,
0 rows with `harness_error`/`run_error`), 0 rows referencing AXQ 6-bit.

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
# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 18:35 CEST)

**Status: BLOCKED (binding pre-staging disk threshold).** The authorized AXQ 6-bit
gate (Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`, todo 20) remains below the
required free space to retain the 30 GiB launch floor after staging. No model was
downloaded, staged, probed, built, launched, stopped, benchmarked, deleted, or
killed during this tick.

This tick performed CPU-only, report-only reconciliation. Kiem was read-only;
`results/` remains append-only; nothing was pushed and no foreign process was
terminated.

## Measured state (verified before writing)

| Fact | Value |
| --- | --- |
| Tick timestamp | 2026-09-17 18:35 CEST |
| Checkout | `59d05c16288ace17f52f831aea9d17d0843bd619` (`59d05c1`) on `main`, clean, ahead 69 of `origin/main` |
| Kiem | `0.4.2` at `/Users/tijs/bin/kiem` |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos 13, 20, 21 |
| AXQ 6-bit pinned tree | `26,985,603,183 B` = `25.132301434 GiB`, AutomatosX revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` |
| Physical memory | `34,359,738,368 B` = `32 GiB` (exactly 32 × 1,073,741,824) |
| Benchmark/model processes | none observed (only the Kiem CLI `sync` daemon is running) |
| Benchmark listeners | none on 8012, 8016, 8017, 8018, 8020, 8021, 8022, 8023, 8024, 8025, 8026, 8027 |
| Results | `results/log.jsonl`: 4,145 rows; 25 AXQ 4-bit rows; **zero** AXQ 6-bit rows |

The expected staged model tree, provenance sidecar, and AXQ 6-bit config are
absent: `configs/` holds only the AXQ 4-bit candidate
(`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/`), and no `*axq6*`/`*6bit*` files
exist outside this blocker series in `artifacts/`.

## Disk gate (binding pre-staging threshold)

Fresh measurement for the benchmark data volume (parent-preflight reading used as
the authoritative gate comparison):

- Free: **`56,028,635,136 B` = `52.180732727 GiB`**.
- The standalone plan component of at least 51.5 GiB still passes
  (51.5 GiB = `55,297,703,936 B`), but the binding threshold is the full
  pre-staging requirement.
- Required free before staging to preserve the 30 GiB launch floor after staging:
  `32,212,254,720 B` (30 GiB) + `26,985,603,183 B` (pinned tree) =
  **`59,197,857,903 B` = `55.132301434 GiB`**.
- Shortfall: **`3,169,222,767 B` = `2.951568707 GiB`**.
- Hypothetical post-stage free space: `56,028,635,136 B − 26,985,603,183 B` =
  **`29,043,031,953 B` = `27.048431293 GiB`**, which is below the 30 GiB launch
  floor by the same shortfall. It would remain above the 20 GiB post-staging
  floor, but the 30 GiB launch floor is binding.

Independent re-read taken during this tick (shutil.disk_usage on the repo path,
moments after the above): `56,012,734,464 B` = `52.165924072 GiB`, shortfall
`3,185,123,439 B` = `2.966377362 GiB`, hypothetical post-stage
`29,027,131,281 B` = `27.033622638 GiB`. Both readings are well below the
required `59,197,857,903 B`; the gate remains BLOCKED under either measurement.
No cache or model payload was deleted.

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
25-row battery. Archive the server log, review every partial or failed run,
commit the evidence, and tear down (free the port) before any Gravity RL leg may
be considered. Keep config snapshot, provenance, raw transcripts, server log,
runner SHA, classification, and teardown evidence separate from AXQ 4-bit.

This tick's only repository change is this report artifact; no model artifact,
benchmark row, Kiem mutation, or runtime state was created.
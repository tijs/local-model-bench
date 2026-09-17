# Qwen3.6 AXQ 6-bit — preflight blocker (2026-09-17 17:31 CEST)

**Status: BLOCKED (binding disk gate).** The authorized AXQ 6-bit gate (Kiem
plan todo 20) remains below the required free space to retain the 30 GiB launch
floor after staging. No model was downloaded, staged, probed, built, launched,
stopped, benchmarked, or killed during this tick.

This tick performed CPU-side reconciliation only. Kiem was read-only;
`results/` remains append-only; nothing was pushed and no foreign process was
terminated.

## Measured state

| Fact | Value |
| --- | --- |
| Tick timestamp | 2026-09-17 17:31:37 CEST |
| Checkout | `6ae6fa6c613b20beeccad33d31bfe80abdfdb3e8` on `main`, clean, ahead 68 of `origin/main` |
| Kiem | `0.4.2` at `/Users/tijs/bin/kiem` |
| Kiem plan | `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open relevant todos 13, 20, 21 |
| AXQ 6-bit pinned tree | `26,985,603,183 B` = `25.132301434 GiB`, AutomatosX revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924` |
| Physical memory | `34,359,738,368 B` = `32 GiB`; `vm_stat` free pages `1,364,057` = `22,348,709,888 B` = `20.813858032 GiB` |
| Benchmark/model processes | none observed |
| Benchmark listeners | none on 8012, 8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027 |
| Results | `results/log.jsonl`: 4,145 rows, 4,622,708 bytes; no AXQ 6-bit rows |
| Leaderboard | `results/LEADERBOARD.md`: 231,134 bytes; unchanged |

The expected staged model directory, provenance sidecar, and AXQ 6-bit config
are absent. The existing local AXQ artifact is the completed 4-bit candidate
only.

## Disk gate

Fresh `shutil.disk_usage` measurement for the benchmark data volume:

- Free: **`56,036,331,520 B` = `52.187900543 GiB`**.
- The standalone plan component of at least 51.5 GiB passes by
  `738,627,584 B` = `0.687900543 GiB`.
- Required free before staging to preserve the 30 GiB launch floor is:
  `32,212,254,720 B` + `26,985,603,183 B` =
  **`59,197,857,903 B` = `55.132301434 GiB`**.
- Shortfall: **`3,161,526,383 B` = `2.944400891 GiB`**.
- Hypothetical post-stage free space: `29,050,728,337 B` =
  `27.055599109 GiB`, which is below the 30 GiB launch floor by the same
  shortfall. It would remain above the 20 GiB post-staging floor, but the
  launch floor is binding.

Compared with the previous 16:27 preflight's `56,017,743,872 B`, free space is
up `18,587,648 B` (`17.726562 MiB`), still materially short of the required
pre-staging threshold. No cache or model payload was deleted.

## Preservation and next gate

Do not download, stage, configure, probe, or benchmark AXQ 6-bit until a fresh
single-writer audit proves all of the following:

1. At least `59,197,857,903 B` (`55.132301434 GiB`) free before staging;
2. at least 30 GiB free at launch and at least 20 GiB after staging;
3. sufficient memory, one-server ownership, a free 8020-family port (pin 8025
   unless a fresh audit selects another), exact served identity and revision,
   `VMLX_ENABLE_UNSAFE_COMPILE=0`, and no unsafe compiled decode.

Once eligible, create and commit the exact Mei config, run the plain/streaming,
native-tool, and cache probes, then run only the AXQ 6-bit 25-row battery. Keep
its config snapshot, provenance, raw transcripts, server log, runner SHA,
classification, and teardown evidence separate from AXQ 4-bit and from the
queued Gravity RL leg. Do not consider Gravity RL until AXQ 6-bit is terminal,
reviewed, committed, and torn down.

This tick's only repository change is this report artifact; no Kiem mutation,
benchmark row, model artifact, or runtime state was created.

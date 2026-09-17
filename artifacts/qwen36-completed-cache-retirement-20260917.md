# Qwen3.6 completed-cache retirement (AXQ4 MTP + ManniX CD-IQ4_K_M) — 2026-09-17

## Scope and authorization

User-authorized guarded cleanup of two completed model caches. This was a
payload/cache retirement only: exactly the two explicit paths below were
removed, and it does not alter historical rankings, benchmark rows, configs,
results, or any Kiem/Hermes job state.

Timestamp: `2026-09-17T20:02:59Z` (pre/post verification window).

## Motivation and runner-gate wording

The 30 GiB runner launch gate motivated freeing disk. That gate is a
conservative downloader safety policy for staging plus launch; it is not a
claim that either deleted model needs 30 GiB to run. Qwen benchmark worker job
`ba2552668fdf` was paused and no benchmark/model-server process was running
during the cleanup; nothing was downloaded, staged, launched, stopped, or
restarted.

## Pre-delete evidence (UTC 2026-09-17T20:02:59Z)

- Git worktree was clean on `main`, ahead of `origin/main`.
- No runner, fixture, model-server, or Hugging Face download process was active.
- No listener existed on benchmark ports `8017`, `8020`, `8024`–`8027`.
- `lsof` reported no matching open handle for either deletion target.

## Exact deleted paths and pre-delete sizes

| Absolute path | `du -sk` before | Size |
|---|---:|---:|
| `/Users/tijs/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` | 22,579,016 KiB | 21.533028 GiB |
| `/Users/tijs/.cache/huggingface/hub/models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF` | 16,311,500 KiB | 15.555859 GiB |
| **Aggregate measured allocation** | **38,890,516 KiB** | **37.088886 GiB** |

- The AXQ4 path was a completed AXQ-4bit candidate; its adjacent
  `.provenance.json` sidecar was retained.
- The ManniX cache's snapshot was
  `75a75137d610ed037a09b46c29ca1d37fd000f2e` and contained the tested
  `Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf` symlink/file.

## Recoverability (verified before deletion)

- `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` is public at pinned revision
  `d880b11584ae6ee1e18a1e86f082a8397cf2ce24`.
- `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF` is public and the cached revision
  `75a75137d610ed037a09b46c29ca1d37fd000f2e` tree contains the tested file.

## Post-delete verification

- Both exact paths were asserted absent; reconfirmed independently at
  `2026-09-17T20:04:36Z` (`ABSENT` for each).
- Retained sidecar:
  `/Users/tijs/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP.provenance.json`
  (1,304 bytes).
- Free disk before: `52.404942 GiB`; after: `89.494213 GiB` (reclaimed
  ≈ `37.089 GiB`, consistent with the `37.088886 GiB` aggregate).
- Independent reconfirmation at `20:04:36Z`: `df -k /` reported `93,848,560 KiB`
  free (≈ `89.50 GiB`); the small delta versus `89.494213 GiB` is APFS
  filesystem-accounting variance.
- Reconfirmation at `20:04:36Z`: no listeners on ports `8017`, `8020`,
  `8024`–`8027`; no runner, model-server, or Hugging Face download process
  present (only macOS system daemons and unrelated Hermes helper processes).

## Retained set

- Benchmark repo configs, `results/log.jsonl`, `results/LEADERBOARD.md`, raw
  transcripts/evidence, runtime/KV caches, shared builds, and the Gravity RL
  config.
- The AXQ4 `.provenance.json` sidecar (historical evidence).

## Repository effect

The cleanup was payload/cache retirement only. No benchmark row, config,
leaderboard entry, Kiem note, or Hermes job was touched. Recording this
evidence is a single new Markdown file under `artifacts/`; nothing was
launched or modified beyond that file.

No GitHub or Hugging Face publication was performed; the evidence commit was
not pushed.
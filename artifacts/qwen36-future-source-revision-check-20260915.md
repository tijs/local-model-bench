# Qwen3.6-35B-A3B — future-machine source-revision metadata check, 2026-09-15

Append-only evidence artifact for the future-machine scheme-aware Qwen3.6
quantisation branch (runbook gates in
`artifacts/qwen36-scheme-aware-runbook-20260915.md`, committed at HEAD
`007160abc2dab919f54a956caf72bd01824119b5`). This file records ONE read-only
Hugging Face metadata verification of the pinned bf16 source revision, plus the
independently observed local blockers for this tick. It is evidence only: it
does not download weights, install packages, convert/calibrate, launch or stop
any server, or change any benchmark state. No `results/log.jsonl` row, no
`results/LEADERBOARD.md` change, no config/runner/test edit, no publish, no
push.

## Exact read-only command and timestamp

Executed on 2026-09-15 at `2026-09-15T13:48:59Z` (UTC), HTTP status 200:

```
curl -sS https://huggingface.co/api/models/mlx-community/Qwen3.6-35B-A3B-bf16/revision/04bbe07c3ed2d93cbf832f523fea344bca1d0fcf
```

GET request only; JSON metadata response body was saved to `/tmp/qwen36-rev-check.json`
(system temp, outside this repository) purely so the exact response could be
re-parsed for this record. No model weights or repo files were downloaded.

## Verified response facts (from the response body)

- Endpoint:
  `https://huggingface.co/api/models/mlx-community/Qwen3.6-35B-A3B-bf16/revision/04bbe07c3ed2d93cbf832f523fea344bca1d0fcf`
- `id` = `mlx-community/Qwen3.6-35B-A3B-bf16`
- `sha` = `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` (exact match, 40 hex)
- `lastModified` = `2026-04-16T16:29:24.000Z`
- `siblings` listed 14 safetensors shards,
  `model-00001-of-00014.safetensors` through
  `model-00014-of-00014.safetensors` (no gaps, no extra safetensors), plus
  repository metadata: `.gitattributes`, `README.md`,
  `chat_template.jinja`, `config.json`, `configuration.json`,
  `generation_config.json`, `model.safetensors.index.json`,
  `preprocessor_config.json`, `processor_config.json`, `tokenizer.json`,
  `tokenizer_config.json`, `video_preprocessor_config.json`, `vocab.json`.

## Scope of what this verifies

This verifies **pinned-revision metadata availability ONLY**: the exact pinned
`<repo>@<sha>` exists on Hugging Face, resolves to the recorded revision, and
its file manifest (14 shards + metadata) is intact. It is NOT a local source
download, NOT a cache presence check, and NOT conversion readiness. Gates 1–3
of the runbook (disk, RAM, tooling) still fail on this Mac, so no download and
no calibrated conversion may start here.

## Independently observed local blockers for this tick (2026-09-15)

- **Disk** — parent observed `/System/Volumes/Data` available = `23112456` KiB
  from `df -k`; re-read at `2026-09-15T13:49:05Z` (same read-only `df -k`):
  available `23111456` KiB (≈ 22.0 GiB). Both readings sit far below the
  runbook floor of `>= 105 GiB` free (source 65.42 GiB + output quant dir +
  calibration scratch + >= 20 GiB remaining floor). Disk gate: FAIL.
- **Tooling** — read-only locked-env probe at `2026-09-15T13:49:00Z` using the
  `--no-sync` variant of the runbook's gate-3 probe:
  `uv run --locked --no-sync python -c 'import mlx_lm'` → exit 1,
  `ModuleNotFoundError: No module named 'mlx_lm'`. (Prior artifacts record the
  same failure for the plain `uv run --locked` probe; the locked bench venv has
  no mlx-lm.) Tooling gate: FAIL.
- **Local source** — scan of the local roots: the Hugging Face hub cache
  (`/Users/tijs/.cache/huggingface/hub`) holds exactly five Qwen3.6 entries, all
  already-quantized: `EigenLabs--Qwen3.6-35B-A3B-MLX-mixed-4bit`,
  `ggml-org--Qwen3.6-35B-A3B-GGUF`,
  `mlx-community--Qwen3.6-35B-A3B-4bit`,
  `mlx-community--Qwen3.6-35B-A3B-4bit-DWQ`,
  `mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit`. No BF16/FP16 source candidate
  found by the parent scan; no `/Users/tijs/models`, `/Users/tijs/.mlx`, or
  `/Users/tijs/Projects/models` root exists.

Status: still blocked on this Mac. All three runbook gates (>= 105 GiB free /
sufficient RAM for ~66 GiB bf16 residency / `mlx-lm[train]` tooling) remain
explicit prerequisites; a fresh ~65 GiB bf16 download would be required on the
qualifying machine. Next commands on that machine, before any conversion:
`mlx_lm.dwq --help` and `mlx_lm.dynamic_quant --help`, with outputs recorded
verbatim in a new dated artifact (per runbook and correction note
`artifacts/qwen36-scheme-aware-runbook-correction-20260915.md`, the
execution-time `--help` output is the sole authoritative flag surface).

## Checks

- `git status --porcelain` before writing this file: clean; HEAD =
  `007160abc2dab919f54a956caf72bd01824119b5` (`artifacts: record mlx-lm quant
  defaults discrepancy`).
- Local probes were read-only and side-effect-free: `curl` GET (metadata only),
  `df -k`, `uv run --locked --no-sync` import probe (no environment sync, no
  install), directory listings of the hub cache.
- No benchmark/result/server/public side effect occurred: nothing benchmarked,
  no `results/log.jsonl` row appended, no `results/LEADERBOARD.md` change, no
  server launched or stopped, no conversion/calibration run, no package
  installed, no publish/push, `/Users/tijs/projects/mei` untouched, existing
  artifacts and configs/runner/tests unmodified.
- This file is append-only evidence; it will not be edited retroactively.
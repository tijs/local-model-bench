# Qwen3.6 runtime-cache cleanup — 2026-09-14

## Scope

This cleanup was required by the benchmark's 30 GB preflight guard. It removed
only two closed, disposable experiment KV-cache directories. No HF model
snapshot, model quant, result history, source checkout, or unrelated macOS
cache was removed.

## Before checks

- No benchmark/server process was listening on ports 8017, 8024, 8025, or 8026.
- `lsof` reported no open handles for either target directory.
- The benchmark preflight reported 25.7 GB free.
- The exact target sizes from `du -sk` were:
  - `/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-dwq` — 10,470,620 KiB
  - `/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-mixed46` — 10,478,056 KiB
  - total — 20,948,676 KiB (19.978214263916016 GiB)

These are local KV caches, not upstream model artifacts, so no external
reference was deleted.

## Deleted exact paths

```text
/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-dwq
/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-mixed46
```

## After checks

- Both exact paths are absent.
- The retained pinned snapshots still exist:
  - `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`
    revision `70a3aa32c7feef511182bf16aa332f37e8d82014`
  - `ggml-org/Qwen3.6-35B-A3B-GGUF`
    revision `baec3ebee244827cda0f4557eafa8b28f7545fa6`
- `df -k /` after cleanup: 47,913,280 KiB available (about 46 GiB in `df -h`).
- Reclaimed space matches the explicit target aggregate within `du`/filesystem
  rounding.
- No benchmark rows or historical result files were changed by the cleanup.

## Repository change

This evidence file is the only repository artifact for the cleanup. No public
push was made.

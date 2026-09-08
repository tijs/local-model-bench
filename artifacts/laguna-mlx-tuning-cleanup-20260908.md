# Laguna MLX tuning — disposable-artifact cleanup (2026-09-08)

Authorized cleanup after Laguna-XS-2.1 MLX tuning. Removed **disposable test/build/KV
artifacts only** — no model payload, provenance file, result JSON, server log, source
worktree, or public state was touched. Recorded 2026-09-08T08:25Z (UTC).

## Pre-deletion state (verified before deletion)

- No Laguna/Mei (or other model/bench) process serving; **no TCP 8024 listener**.
- Worktrees clean: `local-model-bench` (`main` @ `fb24205`, 5 ahead of origin) and
  `vmlx-pr-laguna` (`fix/laguna-language-model-prefix`).
- Disk: `/System/Volumes/Data` **460Gi total, 381Gi used, 42Gi available, 91%**.

## External reference check (public, before deletion)

- `https://huggingface.co/mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit`
  is a **public** MLX 4-bit repo (converted from `nvidia/...-BF16`, mlx-lm 0.31.3,
  4-bit group size 64). The tiny local HF-hub reference copy was not on the user's
  keep-list; the public copy makes it recoverable → disposable.

## Deleted paths (explicit allowlist, displayed sizes as shown by `du -sh`)

| path | size |
|---|---|
| `/Users/tijs/projects/vmlx-pr-laguna/.build` | 7.5G |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-safe-20260908/kv` | 33M |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-region-off-20260908/kv` | 23M |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-region-on-20260908/kv` | 23M |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-global-compile-20260908/kv` | 84M |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-control-parity-20260908/kv` | 1.1G |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-prefill-256-20260908/kv` | 1.0G |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-prefill-1024-20260908/kv` | 1.1G |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-prefill-2048-20260908/kv` | 1.1G |
| `~/.local/share/local-model-bench/mei-runtime/laguna-mlxtune-global-gate-20260908/kv` | 1.3G |
| `~/.cache/huggingface/hub/models--mlx-community--NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit` | 4.0K |
| `/tmp/laguna_speed_probe.py`, `/tmp/laguna_prefill_probe.py`, `/tmp/laguna_parity_probe.py`, `/tmp/laguna_context_boundary.py`, `/tmp/laguna-speed-safe.json`, `/tmp/laguna-parent-focused-test.log` | 4–8K each |
| `/tmp/laguna-mlxtune-{safe,region-off,region-on,global,control-parity,prefill-256,prefill-1024,prefill-2048,global-gate}-start.log` | each small |

No aggregate byte total is claimed beyond the displayed per-path sizes and the disk
snapshots below.

## Retained (KEEP allowlist — all present after cleanup)

- **Staged model dirs** (exactly five) under
  `~/.local/share/local-model-bench/mei-models`:
  `Laguna-XS-2.1-MLX-5bit`, `Ornith-1.5-35B-A3B-MLX-4bit-aligned`,
  `Qwen3.6-35B-A3B-4bit`, `Qwen3.6-35B-A3B-4bit-textonly`, `Ternary-Bonsai-27B-mlx-2bit`.
- **Laguna payload**: 5 safetensors shards (`model-0000{1..5}-of-00005.safetensors`) +
  config/tokenizer/chat template; provenance verified
  `verify.file_bytes = 22999930848`, `verify.shards = 5`.
- Qwen/Ornith tiny hub reference copies retained (keep-list).
- Tuning result JSONs + server logs: `results-mei/laguna-mlxtune-*-20260908/` (incl.
  `laguna-mlxtune-final-safe-20260908`) and the `mei-runtime/laguna-mlxtune-*-20260908`
  run dirs; dedicated release Mei build for the lane retained
  (`mei-build-laguna-*`). No other model root removed.

## Post-deletion verification (2026-09-08T08:25Z)

- All listed deleted paths **absent** (looped `test -e` per path, incl. all 15 `/tmp` files).
- All 5 retained model dirs + Laguna provenance/shards **present**; result JSONs present.
- **Port 8024 free**; no Laguna/Mei server process.
- Disk: `/System/Volumes/Data` **460Gi total, 368Gi used, 55Gi available, 88%**
  (delta vs before: used 381→368 Gi, available 42→55 Gi).

## Repo change

- Only this evidence file added; committed locally on `main` without push. No config,
  report, or public state modified.
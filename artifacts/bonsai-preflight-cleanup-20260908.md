# Bonsai preflight cleanup — 2026-09-08

## Scope

This cleanup was authorized while preparing the Ternary Bonsai Mei benchmark. The
keep-list is the five required MLX artifacts: Laguna 2.1, aligned Ornith 1.5,
Qwen 3.6, the Qwen 3.6 text-only repack, and Ternary Bonsai. Historical configs,
results, transcripts, and the Laguna patch worktree were retained.

## Live pre-check

- UTC: 2026-09-08T06:39:12Z
- Filesystem: `/Users/tijs`
- Free space before cleanup: 15 GiB
- Port 8024: no listener during build-cache cleanup; the later Bonsai run uses it exclusively.
- No Mei, staging, Swift build, or Xcode build process was active during build-cache cleanup.
- The Bonsai run is isolated at:
  `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-27B-mlx-2bit`

## Deleted allowlist

| Path | Measured size before deletion | Reason |
|---|---:|---|
| `/Users/tijs/projects/vmlx-pr-453/.build` | 7.8G | Disposable local Swift build cache |
| `/Users/tijs/projects/vmlx-pr-454/.build` | 7.3G | Disposable local Swift build cache |
| `/Users/tijs/.local/share/local-model-bench/mei-models/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit` | 17G | Discarded benchmark candidate |
| `/Users/tijs/.local/share/local-model-bench/mei-models/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit.provenance.json` | 4.0K | Sidecar for discarded candidate |
| `/Users/tijs/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-gateup` | 18G | Unused intermediate; aligned Ornith copy retained |

The measured total displayed by `du` was approximately 60 GiB; filesystem free
space increased from 15 GiB to 62 GiB.

## External recoverability checks

The public Hugging Face API returned `private: false` and the expected pinned
revision for both discarded model sources:

- `mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit`
  - revision `55ac8c89261109b36c04371cd3f479a4594208c8`
  - verified local source had four safetensors shards and 17,775,425,688 bytes
- `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`
  - revision `19504d912fa8fc7622bf6b1de3db5d5d890b1f02`
  - verified local source/provenance had four safetensors shards and 19,509,024,201 bytes

## Post-delete verification

The following retained model directories exist after cleanup:

- `Laguna-XS-2.1-MLX-5bit`
- `Ornith-1.5-35B-A3B-MLX-4bit-aligned`
- `Qwen3.6-35B-A3B-4bit`
- `Qwen3.6-35B-A3B-4bit-textonly`
- `Ternary-Bonsai-27B-mlx-2bit`

The shared Mei binary `/Users/tijs/.local/share/local-model-bench/mei-build-030/release/mei`
and Laguna source worktree `/Users/tijs/projects/vmlx-pr-laguna` also remain.
All three deleted paths were absent after deletion. Final observed free space:
62 GiB.

## Bonsai run

The original C1 harness was preserved unchanged at
`results-mei/bonsai-c1-harness/`. Its first disposable run exposed an input-size
bug: the nominal 30K sample exceeded the 32,768-token cap and returned HTTP 400.
Those diagnostic tracebacks are retained at
`results-mei/bonsai-c1-run-20260908/`.

A corrected disposable copy uses a context-safe 2,400-repeat sample and writes
raw probes, server logs, KV files, and comparison output to:

`results-mei/bonsai-c1-run-20260908-safe/`

The corrected disposable copy completed the full four-leg control/C1 run. It used a
context-safe 2,400-repeat sample and wrote raw probes, server logs, and temporary
KV files under `results-mei/bonsai-c1-run-20260908-safe/`.

Verified results:

- Four valid JSON probe files; four greedy prompts and five short samples per leg.
- Both rounds were correctness-identical between control and C1, including the native `add_pair` tool call and 700 completion tokens per prompt.
- Control short decode: mean 15.589665 t/s, SD 0.118365, n=10.
- C1 short decode: mean 16.417476 t/s, SD 0.115624, n=10; ratio 1.053100x.
- Control long sample: 12.582029 and 12.745825 t/s; mean 12.663927 t/s.
- C1 long sample: 12.571318 and 11.481064 t/s; mean 12.026191 t/s; ratio 0.949642x.
- Reported peak memory was 17.071 GB for every leg.
- Final comparison output is captured in `/tmp/bonsai_c1_persistent_safe.log`; per-leg server logs are retained beside the probes.

The four disposable per-leg KV directories were removed after verifying the JSON
and server logs. The benchmark data itself remains; no Mei server is listening on
8024. Final observed free space is 63 GiB.

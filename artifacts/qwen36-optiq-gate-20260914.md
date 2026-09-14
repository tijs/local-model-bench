# Qwen3.6 OptiQ Mei gate — raw live evidence, 2026-09-14

Public candidate `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit` at pinned revision
`70a3aa32c7feef511182bf16aa332f37e8d82014` (complete HF-cache snapshot,
dereferenced total 22,155,958,660 bytes / ~20.6 GiB, 15 entries). Gate ran on
the PREBUILT Mei 0.5.0 binary `mei-build-qwen36-optiq-050/release/mei` (`mei
0.5.0`, vmlx `44461ffd` verified in its checkout), port 8024, endpoint
`http://127.0.0.1:8024`. **Gate evidence only — this candidate is NOT ranked,
has no results/log.jsonl rows, and no leaderboard entry. A full benchmark run
is still required for admission.**

Raw probe outputs (copied verbatim from /tmp, same session):

- `artifacts/qwen36-optiq-native-gate-20260914.json` — full acceptance gate
  (models / plain / stream / tool / tool_stream / cache_1 / cache_2, all HTTP
  200; exact served model ID on every response; plain `OPTIQ_OK`, stream
  `OPTIQ_STREAM_OK` with reasoning_content; native `get_weather` tool call on
  both the non-stream and stream paths; per-request `mei_memory_active_bytes`
  23.09–23.18 GB under the 30 GB limit).
- `artifacts/qwen36-optiq-cache-probe-20260914.json` — growing-conversation
  cache-reuse probe: cached_tokens 0 → 1076 → 1092 → 1108 (disk KV tier at
  `mei-runtime/kv-qwen36-optiq-safe`).

## First failure (wrapper run) — do not hide

An initial run through `runner/start_mei_server.sh` naming
`--model-profile qwen3.6-35b-a3b-text` (plus `--prefill-step-size 1024`,
`--kv-cache-dir mei-runtime/kv-qwen36-optiq`) inherited the profile's
`unsafe-compile=1` and the default safetensors mmap load path. Mei reports 5/5
weight shards NOT naturally aligned; the default mmap path realigns unaligned
tensors by copying them into RAM (~16.6 GiB of temporary copies on this
bundle). The combined draw exhausted the GPU allocator: **Metal Insufficient
Memory**, process died with `Trace/BPT trap: 5` (see
`/tmp/qwen36-optiq-mei-server-20260914.log`; the wrapper's echoed launch line
is the first line of that log).

## Load success (safe direct run)

Restarted with the safe control set (all four env vars + explicit flags, no
`--model-profile`); server stdout in `/tmp/qwen36-optiq-mei-safe-20260914.log`:

```
env VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 \
  BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0 \
bash runner/start_mei_server.sh --model-dir <pinned snapshot> \
  --served-model-id mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit --port 8024 --context-cap 65536 \
  --prefill-step-size 512 --kv-cache-dir .../mei-runtime/kv-qwen36-optiq-safe \
  --memory-limit-bytes 30000000000 --compiled-decode false --load-mmap false \
  --temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true --cache-reuse true \
  --build-dir .../mei-build-qwen36-optiq-050 --mei-repo ~/projects/mei
```

Observed (verbatim lines from the safe log):

- `mei: optimization profile ornith (requested auto, prefill 512, compiled-decode false, kv-window 0, ssm-anchors 0)`
- `mei: profile applied max-tokens 4096, unsafe-compile 0, fused-gate-up-limit 0`
- `mei: no --model-profile given; serving on architecture defaults…`
- `mei: WARNING 5 of 5 weight shards are not naturally aligned…`
- `[Load] dtype-materialisation bf16=true mmap=false …` (weights materialized;
  `--load-mmap false` + `MLX_SAFETENSORS_MMAP=0`)
- `mei: memory after load: active 22155076876 cache 0 peak 0 bytes; limit 30000000000 cache-limit 32641751449`
- `mei: listening on http://127.0.0.1:8024 (context cap 65536, prefill step 512, max-tokens 4096, kv-bits none)`

Then the two probe JSONs above (all 200s, exact identity, native tool calls,
growing cached_tokens).

## Why these controls

- `--load-mmap false` + `MLX_SAFETENSORS_MMAP=0`: avoid the unaligned-shard
  realignment copies that OOM'd the first run. Materialized load costs RAM,
  not correctness (correctness gate = the probe set itself).
- `VMLX_ENABLE_UNSAFE_COMPILE=0`: the opposite of what the stock Qwen3.6
  sibling configs pin (C1); OptiQ was gated on the SAFE compile path, and the
  profile would have re-enabled the unsafe fusions.
- `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0` + `BENCH_NO_FUSED_GATE_UP=1`:
  SwitchGLU fused gate+up concat cache off (retains large memory on this MoE).
- `--compiled-decode false`: no graph-traced decode.
- No `--model-profile`, `--prefill-step-size 512`, `--context-cap 65536`,
  `--memory-limit-bytes 30000000000`: exactly the gate's as-run values.
- max-tokens is deliberately NOT set: the 0.5.0 auto profile applies 4096,
  reproducing the gate as-run.

## Reproduction

`configs/Qwen3.6-35B-A3B-OptiQ/mei.yaml` carries this exact control set as its
`benchmark_launch_command`. The pinned snapshot is on disk at
`~/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit/snapshots/70a3aa32c7feef511182bf16aa332f37e8d82014`
(re-fetch revision `70a3aa32…` with `hf` if a cache cleanup ever removes it).
Provenance caveats (self-table contradicts uniform-4bit on MMLU/GSM8K/IFEval,
non-reproducible calibration chain) are recorded in the config's known_gaps.
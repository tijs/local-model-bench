# Laguna XS 2.1 MLX tuning evidence — 2026-09-08

Single source-backed summary of the bounded MLX/Mei tuning probes for
`AtomicChat/Laguna-XS-2.1-MLX-5bit`. Every number below is quoted from a live
probe JSON under `~/.local/share/local-model-bench/results-mei/` (absolute
paths given per row); nothing was re-measured or estimated. This report covers
the **Mei/MLX 5-bit lane only** — the older `poolside/Laguna-XS-2.1-GGUF:Q4_K_M`
leg runs llama.cpp + `bench_local_proxy` (`configs/Laguna-XS-2.1/gguf.yaml`)
and keeps its own historical probe gap (the harness's plain-completion probe
did not recognize its reasoning-only output shape; not a model failure).

> **Scope caveat, applies to every speed number in this report:** all rows are
> **bounded microprobes** (single prompt, short decode, single machine) — they
> are **not a full benchmark**, not pass/fail coding-suite evidence, and not
> comparable to `results/log.jsonl` leaderboard rows. There are no
> sanity/hermes_ops/coding rows for this leg; `orchestration.hermes_provider`
> is null in the config.

## Source state (nothing pushed)

| Item | Value |
|---|---|
| Model repo | `AtomicChat/Laguna-XS-2.1-MLX-5bit` |
| Resolved revision | `fc5643bbe0d54b3f76777fbcfd078d61eb0fb0f6` (pinned == resolved) |
| Staged sidecar | `/Users/tijs/.local/share/local-model-bench/mei-models/Laguna-XS-2.1-MLX-5bit.provenance.json` — `verify.ok: true` |
| vmlx source | `/Users/tijs/projects/vmlx-pr-laguna`, branch `fix/laguna-language-model-prefix`, clean at `d42661c66f64904207725c2ad60e2715994c369c` on top of `bfc12414`/`e19a13dd`; **nothing pushed** |
| Mei checkout (build source) | `/tmp/mei-laguna` @ `b17ad4c36c7c26af1a158374681a09a2cec7b3eb`; `Package.swift` pins vmlx-swift as a **path dependency** on the vmlx checkout above |
| Verified Mei binary | `/Users/tijs/.local/share/local-model-bench/mei-build-laguna-d42661c6/release/mei` (built 2026-09-08; dir name encodes the vmlx commit) |

## Verified nested provenance (sidecar `verify` block)

- 5 shards: `model-0000{1..5}-of-00005.safetensors`
- `file_bytes` / `shard_bytes`: **22999930848**
- `payload_total` / `index_total`: **22999711232**; `header_overhead_bytes`: **219616**
- `arch`: `["LagunaForCausalLM"]`; `model_type`: `laguna`
- `quant_bits`: 5, `quant_group_size`: 64, `quant_mode`: `affine`
- `config_sha256`: `40fc6ec00a4d66acef57f501ef65deaf64adcfa51634d5da18b5b1b3e3b399fa`
- Staged `2026-09-08T07:27:06Z`; `loadability: NOT CHECKED (GPU-gated)` (loadability was established by the live gates below instead)

**Correction of the earlier exploratory config:** the previously recorded
`model_bytes 22999930195` was a **stale warning target** (a pre-staging
expected file_bytes estimate), not an enforced total. The verified on-disk
total is 22999930848. The live config now records the verified value.

## Gate results — native probe, no context (safe build)

`/Users/tijs/.local/share/local-model-bench/results-mei/laguna-mlxtune-final-safe-20260908/probe-native-no-context.json`
— `status: passed`, all 10 probes:

1. `models_identity` — served ID `AtomicChat/Laguna-XS-2.1-MLX-5bit`
2. `plain_completion` — content `ready` (111 completion tokens)
3. `tool_nonstreaming` — native `add_numbers` tool call, `finish_reason: tool_calls`, args `{"a":15,"b":27}`
4. `tool_streaming` — same call via SSE
5. `parity_stream_vs_nonstream` — `content: "parity-ok"`, 94 tokens both paths
6. `cache_growing_turn1` — fresh prefill 367.57 tok/s
7. `cache_growing_turn2_reuses_slot` — **790/818 tokens cached** (2500.97 tok/s prefill)
8. `cache_repeat_1` — 6200-token fresh prefill 374.46 tok/s
9. `cache_repeat_2` — **6199/6200 tokens cached** (57388.76 tok/s prefill)
10. `mei_status` — activeBytes 23588707564, memoryLimitBytes 30000000000

## Context boundary + harness off-by-one (corrected)

`/Users/tijs/.local/share/local-model-bench/results-mei/laguna-mlxtune-final-safe-20260908/context-boundary-corrected.json`

| tokenizer measured | server prompt_tokens | http | result |
|---|---:|---:|---|---|
| 65535 (target 65535) | 65536 | 200 | accepted; completion_tokens 1, elapsed 328.795s |
| 65536 (target 65536) | 65537 | 400 | `engine_error: request exceeded context cap: 65537 prompt tokens > 65536 allowed` |

The server enforces its 65536 cap exactly. The stock `probe_mei.py`
exact-cap probe **assumed tokenizer units equal server prompt tokens**, so its
first nominal exact-cap request failed its own assert — a **harness one-token
unit mismatch, not a model failure**. Documented in the config's `known_gaps`
and here so the corrected measurement (`context-boundary-corrected.json`) is
the cited one.

## Global-optional compile gate (unsafe, bounded)

`/Users/tijs/.local/share/local-model-bench/results-mei/laguna-mlxtune-global-gate-20260908/probe-native-no-context.json`
— `status: passed`, same 10 probes under `VMLX_ENABLE_UNSAFE_COMPILE=1` +
`--compiled-decode true`. **No 65k boundary claim** was made on this build:
the corrected exact-cap measurement was only run on the safe final gate.

## Parity: global-compile vs control (programmatic comparison)

- global: `/Users/tijs/.local/share/local-model-bench/results-mei/laguna-mlxtune-global-compile-20260908/parity-global.json`
- control: `/Users/tijs/.local/share/local-model-bench/results-mei/laguna-mlxtune-control-parity-20260908/parity-control.json`

Programmatic comparison (2026-09-08) of the two response pairs:

- Plain message: **equal** (content AND reasoning_content byte-identical; finish_reason `length`, 128 tokens)
- Tool message: **equal ignoring generated call ids** (same content, same validated `{"a":15,"b":27}` args)
- Usage counts: plain 58/128/186 == 58/128/186; tool 140/55/195 == 140/55/195 (prompt/completion/total)

## Speed microprobes (bounded — not a full benchmark)

| row | file | server tok/s | client tok/s | peak bytes |
|---|---|---|---:|---:|
| region-off 512 | `laguna-mlxtune-region-off-20260908/probe-region-off-512.json` | 56.097 | 56.628 | 23827816224 |
| region-on 512 | `laguna-mlxtune-region-on-20260908/probe-region-on-512.json` | 55.811 | 56.336 | 23827816224 |
| global-compile 512 | `laguna-mlxtune-global-compile-20260908/probe-global-compile-512.json` | 57.639 | 58.188 | 23828110282 |

- **Region-on vs region-off at 512: −0.510%** (server 55.81 vs 56.10) — **speed neutral, within noise**. The narrow region-compiled decode (`VMLX_LAGUNA_COMPILE_DECODE_REGIONS=1`) stays **enabled** in the safe launch only because it is **correctness-proven** for the exact affine archetype and architecturally narrow (routed-SwitchGLU separated decode); it must **not** be advertised as a speed win.
- **Global-compile 512 vs region-off control: +2.749%** — one bounded microprobe, not a benchmark. 96-token global rows: 58.845 / 58.786 tok/s (`probe-global-compile-96.json`). Parity-control rows (safe build): plain 128-token 58.018 tok/s, tool 57.560 tok/s.
- Global-compile is explicitly **experimental/unsafe** (unsafe-compile build), unvalidated at 65k, and kept out of the default safe launch.

## Prefill sweep (bounded; best TESTED 1024, not a global optimum)

11,266-token prompt (`repeat_count` 1600), one full-prefill request each:

| prefill step | file | tok/s | prefill ms | peak bytes |
|---|---:|---|---:|---:|
| 256 | `laguna-mlxtune-prefill-256-20260908/prefill-256.json` | 304.181 | 37037.098 | 26353953374 |
| 512 | `laguna-mlxtune-control-parity-20260908/prefill-512.json` | 332.675 | 33864.839 | 26452244818 |
| **1024** | `laguna-mlxtune-prefill-1024-20260908/prefill-1024.json` | **349.030** | 32278.051 | 26497608046 |
| 2048 | `laguna-mlxtune-prefill-2048-20260908/prefill-2048.json` | 337.545 | 33376.293 | 26497608046 |

Best tested: **1024** (349.03 tok/s). The config's `prefill_step_size` is
updated from 512 to 1024 accordingly.

## Tensor-header calculation (why the fused gate+up cache is disabled)

Each layer's fused gate+up cache: **369655808 bytes**; 39 sparse layers
(1–39; layer 0 is the dense MLP) = **14416576512 bytes** =
**13.426483154296875 GiB / 14.416576512 GB** (arithmetic re-checked:
39 × 369655808 = 14416576512). This is the per-layer fused gate+up tensor
set the SwitchGLU lazy cache would retain, motivating in the safe launch:

- `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0`
- `BENCH_NO_FUSED_GATE_UP=1`
- `VMLX_LAGUNA_COMPILE_DECODE_REGIONS=1`

With the cache disabled the safe runs loaded at **~23588707564 active bytes**
and stayed **~23.83 GB peak** (23827816224; 23.8278 GB decimal).

## Tuned safe launch (gate-verified operating point)

```
env VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 BENCH_NO_FUSED_GATE_UP=1 VMLX_LAGUNA_COMPILE_DECODE_REGIONS=1 \
bash runner/start_mei_server.sh --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Laguna-XS-2.1-MLX-5bit \
  --served-model-id AtomicChat/Laguna-XS-2.1-MLX-5bit --port 8024 --context-cap 65536 \
  --prefill-step-size 1024 --max-tokens 32768 \
  --kv-cache-dir /Users/tijs/.local/share/local-model-bench/mei-runtime/kv-laguna-XS-2.1 \
  --temperature 1.0 --top-p 1.0 --top-k 20 --min-p 0.0 \
  --emit-reasoning true --enable-thinking true --cache-reuse true \
  --optimization-profile generic --memory-limit-bytes 30000000000 --cache-limit-bytes 0 \
  --compiled-decode false \
  --mei-repo /tmp/mei-laguna \
  --build-dir /Users/tijs/.local/share/local-model-bench/mei-build-laguna-d42661c6
```

- `--memory-limit-bytes 30000000000` is pinned deliberately: it **differs** from the launcher default (~1.5× recommended working set ≈ 40 GB on 32 GB) and reproduces the exact gate operating point. `--optimization-profile generic` and `--cache-limit-bytes 0` coincide with the pinned binary's defaults.
- Port **8024** is shared (Ornith/Qwen3.6 Mei configs) — never run concurrently with them; never run 8024 concurrently with Ornith/Qwen3.6 at all.

### Optional global-compile experiment (kept separate)

Same flags but: `VMLX_ENABLE_UNSAFE_COMPILE=1`, `VMLX_LAGUNA_COMPILE_DECODE_REGIONS=0`, `--compiled-decode true`. **Experimental/unsafe**, no 65k context validation, **not** the default safe launch. Documented in the config header and `settings.global_compile_experiment`.

## Status

- Config `configs/Laguna-XS-2.1/mei.yaml` refreshed from this evidence: verified provenance, local vmlx/build path, tuned safe launch, separated global-compile experiment, and the harness off-by-one note. Exploratory/gate-required framing preserved; **no full-benchmark or performance claims**.
- No benchmark rows exist for this leg; nothing was pushed to any remote (local-model-bench stays ahead-of-origin by its pre-existing local commits only; vmlx-pr-laguna remains unpushed).
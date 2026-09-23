# Bonsai 2 MLX — 32 GiB OOM source audit and head-dim-256 remedy hypothesis (2026-09-24)

**Status: CPU-side source audit only — a hypothesis with an actionable next gate, NOT a
success claim.** No code, no model, no server, no benchmark rows, no Mei `main` change,
and no shipped default was modified by or for this artifact. This document is
documentation for the next unit of work; it is **not benchmark/ranking evidence**.

## Scope and non-changes statement

- Scope: read-only audit of the CPU-side source path that produced the recorded
  Bonsai 2 MLX 65,536-token admission OOM, and the candidate source-level remedy.
- **Nothing changed.** Concretely unchanged:
  - Model files under `~/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit`
    (read-only access to `config.json` only).
  - No vmlx / mlx / Mei source was edited, built, or deployed.
  - No server launched, no port opened, no probe run, no benchmark rows appended.
  - No commits pushed to any remote; `local-model-bench` `main` gains only this artifact.
  - Shipped defaults untouched (`VMLX_BONSAI_PRISM_HADAMARD` and `VMLX_QWEN35_FA_CHUNK`
    behaviors/pins unchanged — this run's admission used `VMLX_BONSAI_PRISM_HADAMARD=1`
    and the server default FA chunk).
- Not touched (per workspace rule): `/Users/tijs/projects/vmlx-swift-bonsai-prism` and
  `/Users/tijs/projects/mei-bonsai-prism-12121099` working trees. All vmlx/mlx file:line
  facts below are the parent's independently verified read-only audit of those trees;
  this document re-grounds the runtime evidence (probe, server log, model config).

## Exact identity / pins

| Thing | Exact value |
|---|---|
| Model | `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-mei-46933d60` (staged dir `Ternary-Bonsai-2-27B-mlx-2bit`) |
| vmlx (branched runtime dep) HEAD | `46933d6012e48eb7183570226948a8cb331a5ee7` |
| `Source/Cmlx/mlx` git submodule pin | `73312d3e9ad0bd2e1bdf9a08d91e25571e255964` |
| Admission run | `results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-46933d60-20260923T211126Z-admission` |
| Server launch | `--context-cap 65536 --prefill-step-size 1024 --max-tokens 4096 --cache-reuse true`, port 8027, `VMLX_BONSAI_PRISM_HADAMARD=1` |
| Host | macOS 27.0; unified RAM `hw.memsize` = 34,359,738,368 B = **32.00 GiB**; GPU `applegpu_g13s`, device memory 34,359,738,368 B |
| This repo at writing | `local-model-bench` `main` HEAD `05101b2f86b8c2e7ff976b4da1255ed53cf9d6e0` (`research: record Bonsai Mei consumer build gate`), clean tree |

## Verified failure boundary (32 GiB OOM) and prior chunk=64 negative

- `server.log:95-96` — during the `context_exact_cap` (65,536-token) probe, the last
  prefill progress line is `mei: pp stage=prefill completed=35840 total=65536`, followed
  immediately by:
  `MLX/ErrorHandler.swift:343: Fatal error: [METAL] Command buffer execution failed:
  Insufficient Memory (00000008:***) at .../Source/Cmlx/mlx/mlx/backend/metal/eval.cpp:51`.
  → The 32.00 GiB unified memory machine OOMs at **35,840 / 65,536 tokens** (~55% of cap).
- `probe.json` corroborates: `context_exact_cap` `status:"failed"`,
  `error:"RemoteDisconnected: Remote end closed connection without response"` after
  427.78 s (the server died mid-request; hence the client disconnect). Memory caps from
  `mei_status`: `memoryLimitBytes 24,051,816,857` (~22.4 GiB active limit),
  `cacheLimitBytes 32,641,751,449` (~30.4 GiB), `recommendedWorkingSetBytes 26,800,603,136`
  (~24.96 GiB) on the 34.36 GB device. During the 6,212-token probe, peak was already
  ~13.6 GiB (`mei_memory_peak_bytes 13,615,435,372`).
- Prior negative: an earlier attempt with `VMLX_QWEN35_FA_CHUNK=64` also failed (parent-
  verified), reaching 36,864 tokens before death — one additional 1,024-token chunk past
  the default run, still far from 65,536. Chunking alone does not clear the boundary.

## Exact file/line evidence

Runtime/model (re-verified read-only in this artifact):

- `mei-models/Ternary-Bonsai-2-27B-mlx-2bit/config.json:3` — `"model_type": "prism_hadamard_qwen35"`.
- `config.json:11` — `"full_attention_interval": 4`; `config.json:17-82` `layer_types`
  yields **16 full-attention layers** of 64 (every 4th).
- `config.json:12` — `"head_dim": 256`; `config.json:93-95` — `"num_attention_heads": 24`,
  `"num_hidden_layers": 64`, `"num_key_value_heads": 4`.
- `results-mei/.../prism-46933d60-20260923T211126Z-admission/server.log:95-96` — OOM at
  35,840/65,536 (see above); `command.txt` pins launch flags.

vmlx/mlx source (parent-verified read-only at vmlx `46933d60` / mlx `73312d3e`; not
re-read here per workspace rule):

- `Source/Cmlx/mlx/mlx/backend/metal/scaled_dot_product_attention.cpp:618-636` — the
  full/prefill SDPA arm admits fused head dims **64 / 80 / 128 only**; the vector/decode
  arm admits **256**. Head_dim 256 therefore falls through to the dense path.
- `Source/Cmlx/mlx/mlx/fast.cpp:717-789` — dense fallback materializes concrete
  score (QKᵀ), additive mask, and softmax intermediates as buffers (no fused per-block
  kernel), multiplying transient memory at long prefill.
- `Libraries/MLXLLM/Models/Qwen35.swift:810-845` — the Qwen3.5-style attention module
  calls `attentionWithCacheUpdate` with config head_dim/heads.
- `Libraries/MLXLLM/LLMModel.swift:22-80` — long-prefill chunking loop; per-iteration
  `MLX.eval` + `Memory.clearCache` to bound transients (matches `--prefill-step-size 1024`).

## Mechanism at the allocation layer

The machine has 32.00 GiB unified memory. MLX/Metal runs under an active-memory limit of
~22.4 GiB (`memoryLimitBytes`) with a ~30.4 GiB cache limit. After load, active memory is
~7.6 GiB; decoding/probing pushes peak to ~13.6 GiB. During long prefill, each
1,024-token chunk runs 16 full-attention layers; for head_dim 256 those layers take the
dense fallback (fast.cpp), which materializes score/mask/softmax intermediates sized
(batch·heads × seq × seq) per layer on top of the restored KV cache and 2-bit weights. At
~35,840 tokens cumulative, the marginal allocations exceed what the unified allocator can
supply → Metal command-buffer `Insufficient Memory` at `eval.cpp:51`, surfaced as a Swift
fatal error (`ErrorHandler.swift:343`) that kills the server, observed client-side as
`RemoteDisconnected`. The suspected marginal allocation is the dense fallback's
materialized intermediates; the fused SDPA path would keep those per-block/transient.

## Why head-dim-256 full-SDPA admission is a hypothesis, not an established fix

The candidate remedy is a source-level dispatch experiment: extend the C++ full/prefill
SDPA head-dim admission (`scaled_dot_product_attention.cpp:618-636`) to include 256, so
the 16 full-attention layers of this 256-head-dim model take the fused path. It is
**not an established fix** because:

1. It has not been compiled, exercised, or measured anywhere — there is no result yet.
2. The admission table is a dispatch gate, not a correctness proof: the *full-attention*
   Metal kernel at head_dim 256 may be untested/unexercised even though the *vector/*
   decode arm accepts 256; those are separate code paths.
3. No numerical parity has been demonstrated between the dense fallback and a fused path
   at head_dim 256 (scaling, mask, softmax accuracy).
4. It is a vmlx source change, not a Mei default, and must be carried in an isolated
   consumer build with exact provenance.

## Explicit risks

- **Kernel exercise:** passing the admission gate does not guarantee the full-attention
  kernel is correct or allocation-behaved at width 256; it must actually run.
- **Numerical parity:** fused vs dense outputs must match within tolerance at
  head_dim 256 before any live admission is meaningful (attention pattern, softmax
  scaling, mask handling).
- **Build and submodule provenance:** any experiment must build from the exact recorded
  pins (vmlx `46933d60` + mlx submodule `73312d3e`) with submodules initialized and the
  mlx-c pin as in prior isolated gates, so results compare 1:1 with the recorded OOM;
  a stray submodule rev invalidates the comparison.

## Gating plan (this audit is only step 0)

1. **Narrow CPU/source/unit gate (next unit):** focused, model-free, CPU-side checks of
   the dispatch decision and any pure-logic unit tests, with the diff designed default-
   preserving; no GPU build, no model, no server. The defense-in-depth default (4096
   uncapped `--prefill-step-size 1024` chunking + per-chunk `MLX.eval`/`Memory.clearCache`)
   stays in force.
2. **Fresh isolated consumer build:** throwaway checkout at the pinned commits, patch the
   admission gate locally, build the Mei release consumer against it (mirroring prior
   isolated build gates); no edits to working repos.
3. **Live bounded gate:** rerun the exact admission probe (`probe_mei.py`,
   `--context-cap 65536`, port 8027, same flags) against the freshly built binary and
   compare against the recorded 35,840/65,536 boundary and the chunk=64 36,864 negative.
   Only this can convert the hypothesis into evidence.
4. **Larger-device fallback (>= 64 GiB):** the 32.00 GiB unified host is the binding
   constraint; qualifying on a >= 64 GiB unified-memory device (or with an explicitly
   raised limit) remains the standalone fallback to serve the full 65,536 context without
   any source change.

## Verdict

The CPU-side source audit is **complete and preserved**; the remedy is an actionable next
unit (narrow CPU/source/unit gate → isolated consumer build → live bounded re-probe), kept
default-off with the larger-device fallback as the no-code alternative. Nothing in this
document should be read as a benchmark result, a ranking change, or a claim that the
remedy works.
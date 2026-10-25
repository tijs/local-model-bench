---
license: apache-2.0
library_name: mlx
base_model: RecursiveSI/flint
tags:
- mlx
- mlx-lm
- flint
- moe
- mxfp4
- gptq
- apple-silicon
pipeline_tag: text-generation
---

# Flint 40B-A2.5B MLX (GPTQ MXFP4)

An MLX-format conversion of [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint),
a mixture-of-experts coding model with 39.8B total parameters and about 2.5B active
per token, quantized to MXFP4 (4-bit E2M1 elements, group size 32, per-group E8M0
scales) with activation-aware GPTQ calibration on Apple Silicon.

This is a third-party conversion published by RESMP-DEV. The upstream weights,
license, model card, benchmarks, and serving kit stay with Recursive.

## Base model

- Base model: `RecursiveSI/flint`
- Base revision: `2a247be0c0aec895ccb0ac7ca92229ec6df37288`
- Base license: Apache-2.0
- Architecture: `FlintForCausalLM` (49 layers: 2 dense then 47 MoE, 256 routed
  experts with top-6 sigmoid routing, an always-on shared expert, 513-token
  sliding attention on 35 layers, full attention on 14 layers, per-head learned
  attention sinks, QK RMSNorm, and no positional encoding on the
  `no_rope_layer_indices` layers)

## How this conversion was made

1. Base checkpoint downloaded and verified by SHA-256 on both the Mac and B550.
2. A layer-sequential activation-Hessian calibration captured routed-expert
   activations with the exact training-time routing rule, so only tokens actually
   routed to an expert contributed to that expert's Hessian.
3. Each linear was quantized to MXFP4 with a safe-scale search, and the
   resulting scales were injected into an MXFP4 round-to-nearest conversion of
   the base checkpoint.
4. The packed model was reloaded through MLX-LM and exercised end to end.

Calibration corpus: `RESMP-DEV/ptq-calibration-corpus` at revision
`ffa2e74b9361d573167373140f10dfd30c69a327`, 256 windows of 2,048 tokens,
model-neutral text input, tokenized with the base checkpoint's tokenizer.

## Measurements

All numbers below were measured on an M4 Max (Apple Silicon, 128 GB unified
memory) with `mlx==0.32.4` and this repository's
`RESMP-DEV/mlx-lm` Flint adapter. The holdout set is a held-out
agentic-coding corpus that was not part of the calibration corpus
(8 windows of 2,048 tokens, one shared context per window).

| Model | Format | Holdout perplexity | Decode |
| :---- | :---- | ----: | ----: |
| This model | MLX GPTQ MXFP4, group 32 | 7.40 | 131.5 tok/s |
| Base checkpoint in MLX | BF16 | 8.54 | 66.8 tok/s |
| Official Apple reference | GGUF Q4_1 | 6.15 | 106.7 tok/s |

Notes on the numbers:

- The perplexity column compares like with like: every model is scored on the
  same 8 holdout windows with the same tokenizer. The base checkpoint in MLX
  and the GGUF reference are controls, not baselines this conversion is
  claimed to beat.
- Against the BF16 checkpoint in MLX on those 16,384 target tokens, this
  model keeps 77.86% next-token top-1 agreement and improves mean target
  log-probability by 0.142 nats.
- The official `RecursiveSI/flint-int4-gguf` Q4_1 file is the vendor's own
  Apple Silicon artifact. It is included only as a reference point.
- Decode throughput is a single-stream greedy decode of 256 tokens on one
  prompt, and is a machine-specific number, not a benchmark.
- Prefill of an 8,194-token prompt ran at 1,564 tok/s with a 35.5 GB peak
  memory footprint for the MXFP4 model.

### Independent WikiText-2 check

A second cache-free correctness check used the `wikitext-2-raw-v1` validation
split, 16 contiguous windows of 2,048 tokens, and the same token stream for
both MLX arms. "Target top-1" is the fraction of actual next tokens ranked
first by the model; "agreement with BF16" is the fraction of positions where
the MXFP4 and BF16 argmax tokens are identical.

| Model | Scored tokens | Perplexity | Target top-1 | Agreement with BF16 |
| :---- | ------------: | ----: | ----: | ----: |
| This model, MLX GPTQ MXFP4 | 32,752 | 21.29 | 48.35% | 73.20% |
| Base checkpoint, MLX BF16 | 32,752 | 22.37 | 48.83% | 100% by definition |

The lower MXFP4 perplexity is a property of this limited fixture, not evidence
that quantization improved the model. BF16 retains slightly higher target
top-1 accuracy on the same tokens, the predictions differ on 26.8% of
positions, and any quality claim would require extensive task benchmarking.

## Requirements

- Apple Silicon.
- `mlx` and `mlx-lm`.
- The Flint adapter in `RESMP-DEV/mlx-lm`. The upstream `mlx-lm` does not
  support `FlintForCausalLM` yet. Use this repository's fork at revision
  `b384a406ad5cac168877c32b048f31aa9c8db244` or newer; that revision fixes
  the routed-expert activation order:

```bash
pip install "mlx-lm @ git+https://github.com/RESMP-DEV/mlx-lm.git"
```

## Usage

```bash
pip install "mlx-lm @ git+https://github.com/RESMP-DEV/mlx-lm.git"
mlx_lm.generate --model RESMP-DEV/Flint-40B-A2.5B-MLX-GPTQ-MXFP4 \
  --prompt "Write a Python function that merges overlapping intervals." \
  --max-tokens 2048
```

The chat template uses `<|user|>`, `<|assistant|>`, and `<|developer|>`
role markers. The upstream model card's recommended sampling settings apply
(temperature 1.0, top-p 0.95, top-k 20); the measurements above use greedy
decoding.

## Known limitations

- Greedy decoding is not the vendor's validated configuration. The vendor
  evaluated Flint with temperature 1.0, top-p 0.95, and top-k 20.
- The upstream serving kit is NVIDIA-only. This conversion targets
  `mlx-lm` on Apple Silicon and has not been validated with the vendor's
  serving stack.
- Perplexity on one held-out coding corpus is a distribution-fidelity signal,
  not a task-accuracy measurement. The vendor's agentic benchmark numbers were
  produced on NVIDIA hardware with the BF16 and NVFP4 checkpoints and do not
  transfer to this artifact.
- The quantized artifact was not re-evaluated against the upstream agentic
  benchmarks (Terminal-Bench, SWE-bench) on this hardware.

## License

Apache-2.0, matching the upstream model. See `LICENSE`.

## Provenance

- Upstream model: `RecursiveSI/flint` (Recursive), Apache-2.0.
- Quantization, calibration, and MLX packaging: RESMP-DEV.
- MLX-LM Flint adapter: `RESMP-DEV/mlx-lm`.

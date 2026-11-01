---
license: apache-2.0
base_model: Diffuspace/Clover-35B-A3B-Preview
base_model_relation: quantized
pipeline_tag: text-generation
tags:
  - clover
  - kapitsa
  - apple-silicon
  - mixture-of-experts
  - diffusion
  - 4-bit
---

# Clover-35B-A3B-Preview, 4-bit for Kapitsa

DiffuSpace's [Clover-35B-A3B-Preview](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview) (a block-diffusion MoE
tuned from Qwen3.6-35B-A3B, 3B active per token) quantized for [Kapitsa](https://github.com/nace-ai/kapitsa), the
Metal inference engine for Apple silicon. 19.5 GB.

```bash
kapitsa serve --model clover
```

Kapitsa downloads this pack with Qwen3.6-35B-A3B's DFlash2 drafter
([incoai/Qwen3.6-35B-A3B-DFlash2](https://huggingface.co/incoai/Qwen3.6-35B-A3B-DFlash2)) beside it.

## What is in it

- MLX affine 4-bit, group 64, for the experts, attention, DeltaNet, embedding and output layer; 8-bit router and shared
  expert gate; norms, the DeltaNet's A_log, dt_bias and convolutions, and Clover's own right convolution and softmax controls kept in bf16 as stored. Made from the
  bf16 checkpoint by `tools/convert_clover.py` in Kapitsa's repository; `conversion.json` lists every file's sha256.
- Tensor names under `language_model.` as in MLX's Qwen3.6 packs. mlx-lm has no `clover_moe` model, so this pack is for
  Kapitsa.
- `config.json`, `generation_config.json` (Clover's repetition, length and `</think>` controls), the tokenizer and chat
  template, `LICENSE` and `ATTRIBUTIONS.md` as DiffuSpace ships them.

## Decoding in Kapitsa

`NI_CLOVER_DECODE` picks how Kapitsa decodes Clover:

| Mode | How | Decode, M5 Max (T 0.6 / greedy) |
| --- | --- | ---: |
| `auto` (default) | Clover's causal pathway, drafted by Qwen3.6-35B-A3B's DFlash2 drafter | 319 / 332 tok/s |
| `spec` | DiffuSpace's self-speculative decoding: Clover drafts 7 tokens by denoising, then verifies them | 214 / 210 tok/s |
| `diffusion` | Hugging Face's block diffusion (LowConfidence, block 32, threshold 0.95) | 46 tok/s greedy |

Prefill: 6,002 tok/s at 4K tokens. Measured with `kapitsa bench` on a MacBook Pro M5 Max (128 GB), Kapitsa 0.2.24.

## License

Apache-2.0, as Clover and Qwen3.6-35B-A3B. Clover is DiffuSpace's work, derived from Qwen3.6-35B-A3B (Copyright 2026
Alibaba Cloud); see `LICENSE` and `ATTRIBUTIONS.md`. This repository changes only the weights' precision and layout.

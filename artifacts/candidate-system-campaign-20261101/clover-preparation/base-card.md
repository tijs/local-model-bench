---
license: apache-2.0
base_model: Qwen/Qwen3.6-35B-A3B
library_name: transformers
pipeline_tag: text-generation
tags:
  - clover
  - mixture-of-experts
  - diffusion
  - text-generation
  - custom-code
---

<p align="center">
  <a href="https://diffuspace.ai/">
    <img src="https://assets.diffuspace.ai/brand/logofull.svg" alt="DiffuSpace" width="360" />
  </a>
</p>

# Clover-35B-A3B-Preview

**Clover-35B-A3B-Preview** is the first model released by **DiffuSpace**, delivering state-of-the-art performance among open-source diffusion language models at release on the benchmarks reported in our [launch blog](https://diffuspace.ai/blog/clover-35b/). Clover combines a 35B-parameter mixture-of-experts backbone with approximately 3B active parameters per token, block diffusion generation, and a **128K context window**.

[Blog](https://diffuspace.ai/blog/clover-35b/) · [Code & inference backends](https://github.com/DiffuSpace/Clover-35B-A3B-Preview) · [Hugging Face](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview)

## Performance

[![Clover agentic benchmark results](https://diffuspace.ai/assets/blog/clover/agentic-benchmarks.jpg)](https://diffuspace.ai/blog/clover-35b/#agentic-benchmarks)

See the [benchmark discussion](https://diffuspace.ai/blog/clover-35b/#agentic-benchmarks) for evaluation results, settings, and comparisons.

## Architecture and decoding

Clover is a text-only model derived from [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B), retaining its hybrid Gated DeltaNet (GDN) / full-attention MoE backbone with 40 layers, 256 routed experts, top-8 token routing, and one shared expert per layer.

- **Bidirectional block attention:** additional learned GDN parameters, including right-convolution weights and softmax controls, let tokens attend within a noisy block while preserving a causal prefix.
- **128K context:** up to 131,072 tokens for the prompt and generated response together.
- **Block diffusion with LowConfidence decoding:** this Hugging Face implementation starts each block with masked tokens and resolves confident positions in parallel. Positions with confidence above the threshold are filled; if none qualify, the most confident position is filled to ensure progress. Once resolved, the block becomes part of the prefix for the next block. Defaults are `block_size=32` and `threshold=0.95`.

For **self-speculative decoding** with our SGLang and llama.cpp implementations, see the [official code repository](https://github.com/DiffuSpace/Clover-35B-A3B-Preview).

## Quick start

Install PyTorch with CUDA support, then the Hugging Face dependencies. The example below uses Transformers 5.19.0 and PyTorch 2.10 or later.

```bash
pip install "transformers==5.19.0" accelerate safetensors
```

Use a GPU with enough memory for the BF16 weights (approximately 69 GB) plus inference state.

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Diffuspace/Clover-35B-A3B-Preview"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    dtype=torch.bfloat16,
    device_map="cuda:0",
).eval()

messages = [{"role": "user", "content": "What is diffusion?"}]
prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=True,
)
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to("cuda:0")
output = model.generate(
    **inputs,
    max_new_tokens=24576,
    block_size=32,
    threshold=0.95,
    do_sample=False,
)
completion = output[0, inputs["input_ids"].shape[1]:]
print(tokenizer.decode(completion, skip_special_tokens=True))
```

You can also set `model_id` to a local model directory. Generation defaults are loaded automatically from `generation_config.json`; keyword arguments to `generate()` override them. Requests exceeding the 128K context limit are rejected, including space needed to resolve the final full block.

## Generation controls

We observe that very long generations can sometimes become repetitive. The model includes repetition controls and gradual biases toward ending the response or thinking phase. **The defaults are already configured**, so no extra arguments are needed for normal use. They also apply during greedy decoding.

| Parameter | Default | Purpose |
| --- | --- | --- |
| `presence_penalty` | `0.9` | Discourages tokens that have already appeared in the generated response. |
| `frequency_penalty` | `0.0` | Penalizes tokens in proportion to their occurrence count; disabled by default. |
| `repetition_penalty` | `1.05` | Reduces the preference for previously generated tokens; `1.0` disables it. |
| `dllm_length_penalty` | `10.0` | Gradually increases the preference for end-of-response tokens. |
| `dllm_think_end_bias` | `10.0` | Gradually encourages `</think>` to close the thinking phase. |

Length control begins at `dllm_length_penalty_start=8192` response tokens and reaches its full strength over `dllm_length_penalty_window=8192` more tokens. Thinking control uses `dllm_think_end_start=4096` and `dllm_think_end_window=4096`. These are soft controls; `max_new_tokens` sets the hard output limit. Repetition controls operate on generated response history, excluding the prompt.

## Expert selection

During block denoising, Clover can restrict routing to a shared subset of experts for each block. This reduces the number of distinct experts used across the block. The relevant model configuration settings are:

| Setting | Default | Purpose |
| --- | --- | --- |
| `moe_block_coreset_enabled` | `true` | Enables block-level expert selection during denoising. |
| `moe_block_coreset_top_p` | `0.9` | Sets the cumulative routing-mass threshold used to select the expert subset. |

The selector aggregates the routing scores of each token's top-8 candidate experts across the block, ranks experts by their aggregate score, and keeps enough to cover the requested fraction of that mass. A value of `0.9` means **90% of the aggregated routing mass**, not 90% of all experts. Lower values generally select fewer experts, with a possible quality tradeoff. This setting is separate from token-sampling `top_p` and does not reduce the size of the stored or loaded model weights.

## Serving and evaluation

The Hugging Face implementation provides a standalone PyTorch inference path. Small numerical differences between its operations and SGLang's kernels can lead to different generated text, even with the same decoding settings.

**We recommend our official SGLang implementation for serving and evaluation.** Setup instructions and supported decoding modes are available in the [official repository](https://github.com/DiffuSpace/Clover-35B-A3B-Preview).

## Upstream attribution and modifications

Clover is derived from Qwen3.6-35B-A3B. Upstream model assets are Copyright 2026 Alibaba Cloud and distributed under Apache-2.0; the accompanying [LICENSE](LICENSE) preserves the upstream license and copyright statement.

The model implementation derives from the Hugging Face Transformers Qwen3.5-MoE implementation used for the Qwen3.6 architecture, Copyright 2025 The Qwen Team and The HuggingFace Inc. team. Clover adds text-only block diffusion inference, bidirectional GDN parameters, and generation controls. See [ATTRIBUTIONS.md](ATTRIBUTIONS.md) for file-level provenance and modification notices.

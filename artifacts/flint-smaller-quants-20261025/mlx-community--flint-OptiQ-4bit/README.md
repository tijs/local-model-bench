---
license: apache-2.0
library_name: mlx
pipeline_tag: text-generation
base_model: RecursiveSI/flint
base_model_relation: quantized
tags:
- flint
- mlx
- quantized
- mixed-precision
- optiq
- apple-silicon
- text-generation
- moe
---

# mlx-community/flint-OptiQ-4bit

> **Built with [mlx-optiq](https://mlx-optiq.com)**, the MLX-native toolkit to quantize, fine-tune, and serve LLMs locally on Apple Silicon, no PyTorch and no cloud. [Try the Lab](https://mlx-optiq.com/docs/lab/) · [All OptiQ quants](https://mlx-optiq.com/models) · [Docs](https://mlx-optiq.com/docs/)

A mixed-precision MLX quant of [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint), Recursive's 40B-A2.5B mixture-of-experts model for coding agents. 25.6 GB on disk, down from about 80 GB bf16. Per-layer bit-widths come from a KL-divergence sensitivity pass on a [six-domain calibration mix](https://mlx-optiq.com/blog/calibration-mix): sensitive layers get 8 bits, robust ones 4. See the [original card](https://huggingface.co/RecursiveSI/flint) for what the model is trained to do and how Recursive evaluates it.

## Needs mlx-optiq

Stock `mlx-lm` has no `flint` class yet. OptiQ ships an MLX port of the architecture that registers with `mlx-lm` on `import optiq`. It was checked against Recursive's SGLang serving kit: learned attention sinks, a 513-token sliding window on 35 of the 49 layers, no positional encoding on the full-attention layers, and sigmoid top-6 routing over 256 experts plus a shared expert.

```bash
pip install "mlx-optiq>=0.7.2"
```

```python
import optiq  # registers the flint arch with mlx-lm
from mlx_lm import load, generate

model, tok = load("mlx-community/flint-OptiQ-4bit")
prompt = tok.apply_chat_template(
    [{"role": "user", "content": "Write a Python function that merges overlapping intervals."}],
    tokenize=False, add_generation_prompt=True,
)
print(generate(model, tok, prompt=prompt, max_tokens=4096))
```

Flint reasons before it answers, so give it a generous `max_tokens`. Recursive recommends temperature 1.0, top-p 0.95 and top-k 20. For an OpenAI- and Anthropic-compatible server with tool calls and prompt caching:

```bash
optiq serve --model mlx-community/flint-OptiQ-4bit
```

The weights take 26 GB of unified memory. It was built and scored on a 36 GB Mac, where long prompts leave little headroom; 48 GB or more is comfortable.

## Quantization details

| Property | Value |
|---|---|
| Method | OptiQ mixed-precision (sensitivity-driven) |
| Layers | 369 at 8-bit, 116 at 4-bit (485 total) |
| Group size | 64 |
| Reference for sensitivity | uniform 4-bit |
| Calibration mix | [six-domain mix](https://mlx-optiq.com/blog/calibration-mix) |
| Architecture | 49 layers: 2 dense, 47 MoE (256 routed experts, top-6, shared expert) |
| On disk | 25.6 GB |

Following the naming `llama.cpp` uses for its mixed quants, the "4bit" label denotes the family, not the weighted average.

## Benchmarks

Six-metric Capability Score: the unweighted mean of MMLU, GSM8K, IFEval, BFCL, HumanEval and HashHop. Scored in reasoning mode (generative MMLU and a large thinking budget), the setting that measures an always-on thinking model fairly.

| Metric | OptiQ-4bit |
|---|---:|
| MMLU (reasoning, 969 samples) | 86.4% |
| GSM8K (1000 samples) | 92.6% |
| IFEval (full set, strict) | 90.2% |
| BFCL-V3 simple (200 calls) | 87.0% |
| HumanEval (164 problems, pass@1) | 89.0% |
| HashHop (long-context retrieval) | 72.0% |
| **Capability Score** (mean of 6) | **86.20** |

Every metric gets one equal vote. See the [eval-framework writeup](https://mlx-optiq.com/blog/eval-framework) for the full methodology.

## Links

- **Project website:** [mlx-optiq.com](https://mlx-optiq.com/)
- **All OptiQ quants:** [mlx-optiq.com/models](https://mlx-optiq.com/models)
- **PyPI:** [pypi.org/project/mlx-optiq](https://pypi.org/project/mlx-optiq/)
- **Base model:** [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint)

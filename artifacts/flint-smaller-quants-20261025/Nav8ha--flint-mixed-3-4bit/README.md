---
license: apache-2.0
base_model: RecursiveSI/flint-int4
base_model_relation: quantized
pipeline_tag: text-generation
library_name: mlx
tags:
  - mlx
  - flint
  - code
  - coding-agent
  - moe
  - apple-silicon
  - mac
  - 24gb
  - 32gb
  - 3-bit
---

# Flint for 24 GB Macs (MLX, 3-bit, 17.8 GB)

> **This checkpoint now lives at [mlx-community/flint-mixed-3-4bit](https://huggingface.co/mlx-community/flint-mixed-3-4bit).** The files are the same; use that repo for updates.

Run [Recursive Flint](https://huggingface.co/RecursiveSI/flint), the 40B coding model, on a **24 GB or 32 GB Apple Silicon Mac**.

Recursive's own builds need more memory: their [INT4](https://huggingface.co/RecursiveSI/flint-int4) is 22.6 GB, and their `rec` app asks for 48 GB. This build is **17.8 GB** and peaks at about **19.5 GB** in use. In our tests it solved the same tasks as Recursive's INT4.

Unofficial community build, not released or endorsed by Recursive.

Converted and measured by Navneet Sharma ([@Nav8ha](https://huggingface.co/Nav8ha)).

## Quick start

**1. Install mlx-vlm.** Version 0.7.10 and later can run Flint:

```bash
pip install -U mlx-vlm
```

**2. On a 24 GB Mac only: let the GPU use more memory.** By default macOS gives the GPU about 16 GB on a 24 GB Mac. This raises it to 20 GB until the next restart. Skip this step on 32 GB Macs.

```bash
sudo sysctl iogpu.wired_limit_mb=20480
```

**3. Run it.** Keep these sampling settings: they are Recursive's recommendation.

```bash
mlx_vlm.generate --model mlx-community/flint-mixed-3-4bit --temperature 1.0 --top-p 0.95 --top-k 20 \
  --max-tokens 32768 --prompt "Write a Python function that merges overlapping intervals."
```

For coding agents (pi, OpenCode, anything that speaks the OpenAI API), start a local server and send `temperature 1.0`, `top_p 0.95`, `top_k 20` with each request. The model's thinking comes back separately from its answer.

```bash
mlx_vlm.server --model mlx-community/flint-mixed-3-4bit --port 8080
```

**Agent tool calls:** in mlx-vlm 0.7.10, Flint sometimes uses wrong argument names (for example `path` instead of `filePath`), so some tool calls fail and the agent retries. In our OpenCode test, 41 of 85 calls failed, but all tasks still passed. A fix that keeps tool calls inside each tool's schema is in review ([mlx-vlm #2571](https://github.com/Blaizzy/mlx-vlm/pull/2571)). Once it's released, add `--constrain-tool-calls` to the server command.

Prefer mlx-lm? Flint support is in [PR #1998](https://github.com/ml-explore/mlx-lm/pull/1998), not yet released: `pip install "mlx-lm @ git+https://github.com/ml-explore/mlx-lm@refs/pull/1998/head"`, then `mlx_lm.generate` / `mlx_lm.server` with `--temp 1.0 --top-p 0.95 --top-k 20`.

**Tips for 24 GB:** close heavy apps (browsers with many tabs, design tools). Flint thinks before it answers, often 10–30K tokens, so give it room: keep total context around 32K.

## What to expect

| | Recursive INT4 | This build |
|---|---|---|
| Size on disk | 22.6 GB | **17.8 GB** |
| Smallest Mac | 48 GB (`rec`) | **24 GB** (with step 2) |
| Coding tasks we ran (6) | 6/6 | **6/6** |
| Picks the same next token as the INT4 | — | 86% of the time |
| Speed in mlx-vlm, M5 Max | — | 76–119 tokens/s (slower as output grows) |

**Not tested on a real 24 GB Mac yet.** The fit comes from the peak memory we measured on a 64 GB Mac. If you run it on 24 or 32 GB, please post your memory use and speed in the Community tab, so others know what to expect.

## How it was made

Recursive's INT4 has *trained* 4-bit weights, so it is a better starting point than the full 16-bit checkpoint. We cut only the routed experts (95% of the weights) from 4 to 3 bits, choosing for each group of 64 weights the scale with the smallest rounding error. Attention, embeddings and the output layer keep Recursive's trained values.

<details>
<summary>Full numbers and method</summary>

**Starting point.** Recursive's INT4 beats a plain 6-bit quant of the BF16 checkpoint, so BF16 is the wrong source for small Flint builds:

| Build | Size | Perplexity ↓ |
|---|---|---|
| Recursive INT4 (trained) | 22.6 GB | 4.62 |
| 6-bit from BF16 | ~30 GB | 4.86 |
| 3-bit experts + 6-bit rest, from BF16 | 17 GB | 5.19 |
| 3-bit experts + 4-bit rest, from BF16 | 16 GB | 8.44 |
| **This build (3-bit experts from INT4)** | **17.8 GB** | **4.42** |

A lower perplexity than the INT4 does not mean "better than the INT4". The predictions moved, and on this code they happened to favour the true next token.

**Closeness to the INT4.** 48 × 1,024 tokens of private code (Swift, Python, TypeScript), not in any training set. KL over the reference top-32 tokens plus one bucket for the rest. Self-check (INT4 vs itself): KL 0.0000, 100%.

| Build | KL ↓ | Top-1 agreement ↑ |
|---|---|---|
| **This build** | **0.343** | **86.2%** |
| 3-bit experts from INT4, plain min/max scales | 0.332 | 85.9% |
| 6-bit from BF16 (~30 GB) | 0.341 | 86.4% |
| 3-bit experts + 6-bit rest, from BF16 | 0.490 | 82.3% |

Flint is sensitive to quantization in general: unsloth's charts show their Q8_0 GGUF at about 92% top-1 against BF16.

**Tasks.** A 43-test expression parser (precedence, errors, edge cases) and a reversing-Josephus puzzle, 3 seeds each, temperature 1.0 / top-p 0.95 / top-k 20, 32K output budget. INT4: 6/6. This build: 6/6, plus 3/3 parser runs in mlx-vlm 0.7.10. A small check, not a benchmark: no SWE-bench or Terminal-Bench.

**Speed** (M5 Max 64 GB, runs alternated to cancel out heat):

| Engine | Build | Output tokens | Tokens/s |
|---|---|---|---|
| `rec` 0.1.0 | Recursive INT4 | 8.8K | 117 |
| `rec` 0.1.0, one local check relaxed | this build | 8.4K | 117 |
| mlx-vlm 0.7.10 | this build | 14.0K | 119 |
| mlx-vlm 0.7.10 server | this build | 16.7K / 22.2K | 91 / 76 |
| mlx-lm (PR #1998) | this build | 26.6K | 76 |

`rec` 0.1.0 already contains a 3-bit-expert path, but its checkpoint check accepts only 4-bit experts. We relaxed that check in a local copy to measure speed; that is not a supported setup. If Recursive ships its own (trained) 3-bit build, prefer theirs.

**Method.**
1. Load Recursive's INT4. Its weights are packed as `uint8`; mlx-lm expects `uint32`, so view each packed weight as `uint32` (same bit layout).
2. For each routed-expert projection (`switch_mlp.{gate,up,down}_proj`): dequantize, then quantize to 3 bits, group size 64. Per group, try clip ratios 1.0, 0.95 … 0.70 of the group's min/max and keep the lowest squared error.
3. Leave everything else as is. The router (`mlp.gate`) stays BF16.

Scripts in this repo: `experts3_from_int4.py` (build), `eval_kl.py` (KL, top-1, perplexity).

**Limits.** Not trained for 3-bit (a QAT 3-bit from Recursive would likely be better). Small evaluation. All numbers from one 64 GB M5 Max.

</details>

## License

Apache 2.0, same as Flint. Model by [Recursive](https://www.recursive.com/updates/introducing-recursive-flint). See `LICENSE`.

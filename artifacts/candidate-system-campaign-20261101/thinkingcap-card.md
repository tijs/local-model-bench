---
base_model: bottlecapai/ThinkingCap-gemma-4-26B-A4B-it
base_model_relation: quantized
library_name: gguf
tags:
  - gemma_4_26b_a4b_it
  - gguf
  - llama.cpp
  - mxfp4
  - token-efficient
  - efficient-thinking
pipeline_tag: image-text-to-text
license: apache-2.0
license_link: https://ai.google.dev/gemma/docs/gemma_4_license
---

<a href="https://www.bottlecapai.com/"><img src="gemma_cap_header.png" alt="ThinkingCap Gemma-4-26B-A4B — BottleCap AI" width="100%"></a>

# bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF

**We recommend `ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf` over `Q4_K_M` at this size**: it is the file evaluated below, and it held up better on our math benchmarks. Pull it with `-hf bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF:MXFP4_MOE`.

GGUF / [llama.cpp](https://github.com/ggml-org/llama.cpp) quantizations of [bottlecapai/ThinkingCap-gemma-4-26B-A4B-it](https://huggingface.co/bottlecapai/ThinkingCap-gemma-4-26B-A4B-it) — ThinkingCap's shorter-thinking post-training applied to [gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it), a mixture-of-experts model with image input.

➡️ Full model description, evaluation results, the measured thinking-token reduction and recommended sampling: see the main model card at [bottlecapai/ThinkingCap-gemma-4-26B-A4B-it](https://huggingface.co/bottlecapai/ThinkingCap-gemma-4-26B-A4B-it).

As in the base model, **thinking is off unless the request turns it on** (`enable_thinking=True`); the usage examples below turn it on.

## Expected performance

<!-- eval-table -->
`ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf` (`MXFP4` / `Q5_1` experts, `Q8_0` attention, dense and embedding), served by llama.cpp, against the bf16 checkpoint of the main card, on nine of its benchmarks. AA-LCR, τ²-bench and LongBench v2 are not yet covered.

| Benchmark (questions × seeds) | bf16 acc % | GGUF acc % | Δ pp [95% CI] | Thinking tokens, bf16 → GGUF (mean / median / p95) | Δ mean thinking [95% CI] |
|---|---|---|---|---|---|
| GPQA-Diamond (198 × 3) | 79.0 | 78.3 | −0.7 [−2.9, +1.6] | 4,284 / 1,998 / 15,502 → 4,310 / 2,008 / 16,316 | +0.6% [−5.6, +7.1] |
| MMLU-Pro (400 × 1) | 84.0 | 83.0 | −1.0 [−3.1, +1.1] | 2,112 / 963 / 8,445 → 1,942 / 931 / 7,761 | −8.0% [−13.7, −2.1] |
| MMMLU (600 × 1) | 85.8 | 86.2 | +0.4 [−1.3, +2.1] | 706 / 364 / 2,341 → 728 / 348 / 2,287 | +3.1% [−4.0, +10.8] |
| AIME 2026 (30 × 2) | 86.7 | 85.0 | −1.7 [−6.2, +2.0] | 8,963 / 6,490 / 24,506 → 10,349 / 6,460 / 27,924 | +15.5% [+1.8, +31.0] |
| HMMT Feb 2026 (33 × 1) | 74.2 | 84.8 | +10.7 [+0.1, +22.0] | 14,717 / 10,451 / 43,514 → 11,033 / 8,072 / 30,010 | −25.0% [−36.1, −13.2] |
| HMMT Nov 2025 (30 × 1) | 80.9 | 83.3 | +2.4 [−6.9, +10.7] | 10,542 / 7,184 / 28,254 → 11,433 / 6,194 / 26,935 | +8.5% [−7.2, +27.2] |
| LiveCodeBench v6 (175 × 1) | 77.0 | 73.7 | −3.3 [−7.0, +0.4] | 8,375 / 6,306 / 25,083 → 8,401 / 6,924 / 23,264 | +0.3% [−6.6, +7.9] |
| IFBench (300 × 3) | 78.7 | 78.0 | −0.7 [−2.1, +0.7] | 5,585 / 4,530 / 13,033 → 5,969 / 4,670 / 13,832 | +6.9% [+0.6, +14.3] |
| RealWorldQA (765 × 1) | 70.6 | 75.8 | +5.2 [+2.9, +7.5] | 533 / 211 / 1,941 → 623 / 205 / 2,005 | +16.9% [−8.1, +57.1] |

- **bf16** is the main card's checkpoint on the same questions, every card seed averaged per question, so the MMLU-Pro and MMMLU subsets (uniform random samples of the full test sets) do not reproduce the card's full-set numbers exactly. **Δ** is GGUF minus bf16; the interval is a 95% bootstrap over questions. Thinking tokens count the reasoning trace only, over question × seed.
- The GGUF ran on llama.cpp `bfd73a8` with the main card's sampling — thinking on, temperature 1.0, top_p 0.95, top_k 64 — and a 65,536-token cap.
- Note the unquantized BF16 GGUF on the same llama.cpp server thinks 6.1% longer than the bf16 checkpoint on AIME 2026 and 14.7% longer on GPQA-Diamond.
<!-- /eval-table -->

## About GGUF and quantization

[GGUF](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md) is a single-file model format for running LLMs locally with llama.cpp and compatible runtimes (LM Studio, Ollama, Jan, …). The quantized files below store the weights at 4.3 to 8.5 bits per weight instead of the checkpoint's 16.

Every file keeps the weights that run on every token at 8-bit `Q8_0`: the attention projections, the dense feed-forward block, and the token embedding, which is also the output head. The router stays in F32. The files differ in how they store the routed experts, which hold 90% of the 25.2B parameters while only 8 of 128 run per token; the last layer's experts are kept one step higher than the rest. `MXFP4` is 4-bit floating point with a shared scale per block of 32 weights, the format family of NVFP4.

The `Q6_K`, `Q4_K`, `Q5_1`, `IQ3_S` and `IQ4_NL` tensors are quantized with an **importance matrix** (activation statistics from a chat-formatted calibration corpus with reasoning traces, which steer where the rounding error lands); it is included as `ThinkingCap-gemma-4-26B-A4B-it-imatrix.gguf` for anyone building other sizes.

## Files

<!-- files-table -->
| File | Experts: gate/up · down | Size |
|---|---|---|
| `ThinkingCap-gemma-4-26B-A4B-it-Q8_0.gguf` | `Q8_0` · `Q8_0` | 26.9 GB |
| `ThinkingCap-gemma-4-26B-A4B-it-Q6_K.gguf` | `Q6_K` · `Q8_0` | 23.3 GB |
| `ThinkingCap-gemma-4-26B-A4B-it-Q4_K_M.gguf` | `Q4_K` · `Q5_1` | 17.0 GB |
| `ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf` | `MXFP4` · `Q5_1` | 16.6 GB |
| `ThinkingCap-gemma-4-26B-A4B-it-IQ4_XS.gguf` | `IQ3_S` · `IQ4_NL` | 13.6 GB |
| `mmproj-ThinkingCap-gemma-4-26B-A4B-it-f16.gguf` | vision projector | 1.19 GB |
| `ThinkingCap-gemma-4-26B-A4B-it-imatrix.gguf` | importance matrix | 57 MB |
<!-- /files-table -->

## Usage (llama.cpp)

```bash
# serve an OpenAI-compatible endpoint, thinking on, with the base model's recommended sampling
llama-server -hf bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF:MXFP4_MOE \
  --jinja --chat-template-kwargs '{"enable_thinking":true}' --reasoning-format deepseek \
  --temp 1.0 --top-p 0.95 --top-k 64 -ub 2048 -b 2048

# or download the file and chat in the terminal
huggingface-cli download bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF \
  ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf --local-dir .
llama-cli -m ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf --jinja \
  --chat-template-kwargs '{"enable_thinking":true}' --temp 1.0 --top-p 0.95 --top-k 64
```

With `--reasoning-format deepseek` the server returns the thinking in `reasoning_content` and the answer in `content`. A client can also turn thinking on per request with `"chat_template_kwargs": {"enable_thinking": true}`. Keep the temperature at the recommended 1.0; greedy decoding can loop.

## Vision (image input)

Image input needs the multimodal projector `mmproj-ThinkingCap-gemma-4-26B-A4B-it-f16.gguf` (in this repo) loaded alongside any of the text files. `llama-server -hf …` downloads and loads it automatically.

- **LM Studio / Jan / Ollama, …:** download the `mmproj-*.gguf` from this repo; LM Studio detects it and enables image input.
- **llama.cpp CLI:**

```bash
huggingface-cli download bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF \
  ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf mmproj-ThinkingCap-gemma-4-26B-A4B-it-f16.gguf --local-dir .
llama-mtmd-cli -m ThinkingCap-gemma-4-26B-A4B-it-MXFP4_MOE.gguf \
  --mmproj mmproj-ThinkingCap-gemma-4-26B-A4B-it-f16.gguf -ub 2048 -b 2048 \
  --image photo.jpg -p "Describe this image."
```

- **llama-server:** add `--mmproj mmproj-ThinkingCap-gemma-4-26B-A4B-it-f16.gguf` when serving a local file.

Keep `-ub 2048 -b 2048` for image input. Gemma 4 attends bidirectionally across an image's tokens, so the whole image must fit in one micro-batch, and with llama.cpp's default of 512 a larger image aborts the server (`GGML_ASSERT ... non-causal attention requires n_ubatch >= n_tokens`, llama.cpp `bfd73a8`).

## Where to find us

<table style="border-collapse:collapse;border:0;margin:0"><tbody><tr>
<td style="border:0;padding:0 18px 0 0"><a href="https://www.bottlecapai.com/"><img src="social-web.png" alt="Website" width="34" height="34"></a></td>
<td style="border:0;padding:0 18px 0 0"><a href="https://www.linkedin.com/company/bottlecap-ai/"><img src="social-linkedin.png" alt="LinkedIn" width="34" height="34"></a></td>
<td style="border:0;padding:0 18px 0 0"><a href="https://www.instagram.com/bottlecapai/"><img src="social-instagram.png" alt="Instagram" width="34" height="34"></a></td>
<td style="border:0;padding:0"><a href="https://x.com/BottleCapAI"><img src="social-x.png" alt="X" width="34" height="34"></a></td>
</tr></tbody></table>

Need even more efficiency? Our enterprise versions go further — fewer thinking tokens still, tuned to your workload, at matched accuracy on your own tasks. Built for AI labs, inference providers and enterprises running models at scale. Deployed on your infrastructure, or in the cloud and region you choose.
[Talk to our team](mailto:enterprise@bottlecapai.com)

## License

Released under the base model's own license, Apache 2.0 (see the
[Gemma 4 license page](https://ai.google.dev/gemma/docs/gemma_4_license)).

---
language:
- en
library_name: mlx
license: apache-2.0
pipeline_tag: text-generation
base_model: RecursiveSI/flint
base_model_relation: quantized
tags:
- mlx
- jang
- quantized
- apple-silicon
- osaurus
- reasoning
- tool-use
- agent
- coding
- moe
- flint
---

<p align="center">
  <a href="https://osaurus.ai"><img src="./osaurus-x-banner.png" alt="Osaurus" width="800"></a>
</p>

**Runtime: [Osaurus](https://osaurus.ai) 0.25.25 or newer.**

# OsaurusAI/Flint-40B-A2.5B-JANG_6M

**Flint 40B-A2.5B in 32.8 GB, with 98.0% top-1 agreement with the full-precision model.** Against Recursive's own
Apple Silicon release ([RecursiveSI/flint-int4](https://huggingface.co/RecursiveSI/flint-int4), 22.6 GB), it has 8.5×
lower KL divergence from the original and 4.0 points higher top-1 agreement, at 10.3 GB more.

This is a JANG bundle of [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint), Recursive's mixture-of-experts
model for coding agents: 49 layers (2 dense, 47 MoE with 256 routed experts, top-6, plus an always-on shared expert),
39.8B parameters with about 2.5B active per token, 35 sliding-window and 14 full-attention layers, a 262k context,
reasoning and native tool calls. Text only; the release has no MTP head or draft model.

- **Routed experts:** affine 6-bit (group 64), rounded with GPTQ on per-expert Hessians after activation-aware (AWQ)
  scaling.
- **Everything else:** affine 8-bit (group 64), GPTQ-rounded: attention, the shared experts, the two dense MLP layers
  and lm_head; the embeddings are 8-bit too. Routers, norms and the learned attention sinks stay bf16.
- **Size:** 32.83 GB of model shards, 6.60 bits per weight over the 39.8B source parameters.

## Quality vs the original model

The test set is 96 held-out sessions (**253,155 teacher-forced positions**), scored against the BF16 release with
top-128 KL. Every scored assistant turn was written by Flint itself; some sessions continue real agent and terminal
trajectories. They cover coding in dozens of languages, multi-round agent episodes with tool calls and injected
environment errors, terminal sessions, math, science, finance, security, long documents and chat. None of these
sessions were used for calibration.

| | size | bits/weight | mean KL ↓ | p99 KL ↓ | top-1 ↑ | ΔNLL ↓ |
|---|---|---|---|---|---|---|
| RecursiveSI/flint (BF16, the reference) | 79.6 GB | 16 | 0 | 0 | 100% | 0 |
| RecursiveSI/flint-int4 | 22.6 GB | 4.54 | 0.0481 | 0.730 | 94.1% | +0.044 |
| Flint-40B-A2.5B-JANG_4M | 23.4 GB | 4.70 | 0.0205 | 0.333 | 96.2% | +0.017 |
| **Flint-40B-A2.5B-JANG_6M** | **32.8 GB** | **6.60** | **0.0057** | **0.090** | **98.0%** | **+0.001** |
| Flint-40B-A2.5B-JANGH2 | 13.2 GB | 2.65 | 0.152 | 2.36 | 89.5% | +0.149 |

ΔNLL is the change in negative log-likelihood of the actual held-out tokens. For scale: moving every embedding row of
the BF16 model by one bf16 step already gives a mean KL of 0.0040 and 98.4% top-1, so even a negligible change to the
weights lands near 98% top-1.

RecursiveSI/flint-int4 is Recursive's own MLX release: affine 4-bit (group 64) on every linear layer, including
attention, the shared experts and lm_head, with 8-bit embeddings (bit widths measured from its shards). It was scored
on the same sessions, the same way.

**By area** (mean KL · top-1):

| area | positions | **JANG_6M** | RecursiveSI/flint-int4 |
|---|---|---|---|
| coding | 180,831 | **0.0049 · 98.2%** | 0.0418 · 94.6% |
| reasoning | 43,308 | **0.0064 · 97.7%** | 0.0568 · 93.2% |
| agentic | 14,343 | **0.0091 · 97.3%** | 0.0665 · 92.7% |
| terminal | 3,179 | **0.0063 · 98.3%** | 0.0363 · 94.8% |
| general, creative, long documents | 11,494 | **0.0101 · 97.1%** | 0.0958 · 91.2% |

Coding: review, refactor, test, port and debug tasks on real files plus generation across dozens of languages, and
PyTorch. Reasoning: math, science, finance, office, networking and cybersecurity. Agentic: multi-round tool-use
rollouts against a simulated environment (with errors, timeouts, empty or truncated results, permission and rate-limit
failures, and mid-task user steering), next turns of real agent trajectories, and edge cases such as tools offered but
not needed or prompt injection inside a tool result. Terminal: terminal-agent sessions with a native `bash` tool and
next turns of real terminal and SWE-agent trajectories.

## Reasoning and tool decisions

- **Closing reasoning:** at the 151 points in the held-out transcripts where Flint closed its reasoning (the first
  `</think>` of a turn), the BF16 model's top choice is `</think>` at 148. JANG_6M: **147**. RecursiveSI/flint-int4:
  147.
- **Starting a tool call:** at the 74 points where Flint started a tool call (`<tool_call>`), the BF16 model's top
  choice is the call at 70. JANG_6M: **70**. RecursiveSI/flint-int4: 70.

## What's in the bundle

All bit widths below were measured from the shard bytes.

- **Routed experts** (47 MoE layers × gate/up/down × 256 experts): affine 6-bit group 64. 35,834 of 36,096 expert
  matrices were GPTQ-rounded; the other 262, belonging to experts the calibration set routed too few tokens to (fewer
  than 4× the input width), were rounded to nearest.
- **8-bit group 64:** attention q/k/v/o (×49 each); shared-expert gate/up/down (×47 each); the dense MLP gate/up/down
  of layers 0–1; lm_head; embeddings.
- **bf16:** routers (×47), all RMSNorms including the per-head QK norms, and the attention sinks.

## Serving contract

- **Reasoning:** Flint has no thinking switch and no effort levels. It decides each turn whether to reason and writes
  `<think>…</think>` itself before the answer; thinking toggles have no effect.
- **Tool calls:** the GLM-4.7 XML format, `<tool_call>name<arg_key>k</arg_key><arg_value>v</arg_value></tool_call>`.
  Tool results go back as `<|observation|>` turns.
- **Roles:** system, developer, user, assistant and observation each have their own marker; the developer role is
  native, not an alias for system.
- **Sampling:** temperature 1.0, top-p 0.95, top-k 20 (`generation_config.json`). Flint can reason for a long time on
  hard problems; allow at least 32k output tokens for them.
- **Stop tokens:** `<|end_of_text|>`, `<|user|>`, `<|observation|>`, `<|developer|>`.
- **Context:** 262,144 tokens. The 35 sliding-window layers keep only the last 513 tokens, so the KV cache grows on
  the 14 full-attention layers only (28 KiB per token).

## Build details

- **Calibration:** a corpus of 548 sessions (1.80M tokens) of Flint's own outputs, generated by an 8-bit copy of the
  BF16 model at Flint's default sampling settings. 452 sessions (1.44M tokens) are calibration; the 96 held-out sessions
  above are disjoint from them. Across the corpus, 134 sessions are multi-turn, with 355 tool rounds, 134 injected
  environment failures and 31 mid-task user steers; coding spans 47 programming languages; and Flint chose to reason in
  871 of 918 assistant turns.
- **Hessians:** per-expert input Hessians weighted by the router weight squared, and dense input Hessians for every
  other linear layer, from a layer-streamed run of the BF16 model.
- **AWQ:** fold strength is searched per layer on the Hessian-weighted error, with zero (no fold) allowed. The search
  folded the down-projection inputs through each expert's up rows in 46 of 47 layers (strength 0.2–0.5) and the expert
  inputs into the post-attention RMSNorm in 2, with the router and shared expert compensated exactly. The
  attention-input fold into `input_layernorm` was kept in 3 of 49 layers. Scales are powers of two, so every fold is
  exact in bf16.
- **GPTQ:** on each expert's own Hessian, with a never-worse-than-round-to-nearest guard per expert.
- **Verification:** checked from the shards. Every tensor file is aligned, there is one index that matches the shards,
  every module's bits match the config, and no scale is NaN or infinite.

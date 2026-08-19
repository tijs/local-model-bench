# Leaderboard

Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not
hand-edit rows below, edit the log and regenerate instead.

Grouped by (model, backend, quant, config_hash) — never averaged across
different configs, even for the same model+backend, since that would mix
genuinely different experiments (e.g. before/after a settings fix).

| model | backend | quant | config | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |
|---|---|---|---|---|---|---|---|---|
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | [aa5d02c11bba](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) | 6 | 83% | 55.8 | 5.54 | 0 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | [8dd47a586509](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) | 5 | 80% | 1.5 | 11.45 | 0 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | [a03394d84d27](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) | 6 | 83% | 1.7 | 15.56 | 0 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | [b0b30ac444da](configs/Muse-Glimmer-30B/gguf.yaml) | 5 | 60% | 8.0 | 57.96 | 0 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | [f6397d624011](configs/Qwen3.8-27B/gguf.yaml) | 10 | 80% | 6.5 | 44.33 | 0 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | [163fa63ffb83](configs/Qwen3.5-9B/gguf.yaml) | 5 | 80% | 20.2 | 15.45 | 0 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | [29ed581f7054](configs/Qwen3.5-9B/gguf.yaml) | 1 | 100% | — | — | 0 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | [bbaa3dfa1953](configs/Qwen3.8-27B/mlx.yaml) | 2 | 100% | 8.6 | 3.76 | 0 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | [f894953f1f80](configs/Qwen3.8-27B/mlx.yaml) | 6 | 50% | 0.3 | 334.45 | 0 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | [3047922de5b7](configs/Ornith-1.5-35B-A3B/gguf.yaml) | 6 | 67% | 29.4 | 10.84 | 0 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | [c2576cd6b385](configs/Ternary-Bonsai-27B/mlx.yaml) | 5 | 80% | 7.3 | 117.07 | 0 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | UD-Q2_K_XL | [2233edb1c4f2](configs/Qwen3.8-27B/gguf-unsloth-ud-q2.yaml) | 5 | 80% | 6.2 | 55.15 | 0 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | — | [89f4d8d04793](configs/Qwen3.8-27B/gguf-unsloth-ud-q4.yaml) | 5 | 80% | 6.2 | 55.60 | 0 |

## By suite

| model | backend | config | suite | pass rate |
|---|---|---|---|---|
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | hermes_ops | 2/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | hermes_ops | 1/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | hermes_ops | 4/6 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | sanity | 4/4 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | hermes_ops | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 29ed581f7054 | kiem_mini | 1/1 |
| mlx-community/Qwen3.8-27B-4bit | mlx | bbaa3dfa1953 | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | f894953f1f80 | hermes_ops | 3/6 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | hermes_ops | 1/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | hermes_ops | 2/3 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | hermes_ops | 2/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | hermes_ops | 2/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | sanity | 2/2 |

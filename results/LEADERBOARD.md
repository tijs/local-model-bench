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

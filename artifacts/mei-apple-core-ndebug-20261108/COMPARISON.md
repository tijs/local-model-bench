# Qwen: effect of the Cmlx Release setting

Each number averages the medians of two fresh processes with five measured repeats per context. Cache reuse was disabled. All runs matched the original prompt bytes, greedy output and usage and had normal memory pressure.

| Comparison | Context | TTFT (s) | Decode (tok/s) | Total (s) |
|---|---|---:|---:|---:|
| corrected vs instrumented | 26 tokens | 0.31 → 0.29 (-8.8%) | 58.96 → 67.46 (+14.4%) | 2.31 → 2.03 (-12.1%) |
| corrected vs instrumented | 30,009 tokens | 70.00 → 69.63 (-0.5%) | 51.08 → 50.75 (-0.6%) | 72.31 → 71.95 (-0.5%) |
| corrected vs published | 26 tokens | 0.29 → 0.29 (-0.3%) | 66.98 → 67.46 (+0.7%) | 2.05 → 2.03 (-0.7%) |
| corrected vs published | 30,009 tokens | 69.77 → 69.63 (-0.2%)†‡ | 50.48 → 50.75 (+0.5%) | 72.10 → 71.95 (-0.2%)†‡ |
| instrumented vs published | 26 tokens | 0.29 → 0.31 (+9.3%) | 66.98 → 58.96 (-12.0%) | 2.05 → 2.31 (+12.9%) |
| instrumented vs published | 30,009 tokens | 69.77 → 70.00 (+0.3%) | 50.48 → 51.08 (+1.2%) | 72.10 → 72.31 (+0.3%) |

† The process ranges overlap. ‡ The direction differed across the mirrored halves. These flags describe the sample, without claiming statistical significance.

[Run declarations](matrix.json) · [Per-process evidence](comparison.json)

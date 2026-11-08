# Apple MLX core main vs. Mei 0.11.0

Each number averages the medians from two fresh processes, each with five measured repeats. Both versions used the same model and prompt, with cache reuse disabled. Cold probes and warmups are excluded. TTFT is time to the first generated token, including reasoning. All selected observations passed greedy output and usage parity.

| Model | Context (actual tokens) | TTFT (s) | Decode (tok/s) | Total (s) | First visible text (s) |
|---|---|---:|---:|---:|---:|
| qwen | short (26) | 0.29 → 0.31 (+9.2%) | 67.11 → 58.65 (-12.6%) | 2.04 → 2.33 (+13.8%) | — (0/10 → 0/10 visible) |
| qwen | loaded (30,009) | 69.84 → 70.03 (+0.3%) | 50.55 → 51.01 (+0.9%) | 72.17 → 72.34 (+0.2%) | — (0/10 → 0/10 visible) |
| ornith | short (26) | 0.23 → 0.25 (+7.8%) | 67.12 → 59.09 (-12.0%) | 2.04 → 2.31 (+13.0%) | 1.41 → 1.59 (+12.6%) |
| ornith | loaded (30,009) | 164.75 → 159.66 (-3.1%) | 50.43 → 51.11 (+1.3%) | 167.17 → 162.04 (-3.1%) | 166.09 → 160.98 (-3.1%) |
| groot | short (26) | 0.33 → 0.33 (-0.5%) | 55.65 → 56.22 (+1.0%) | 2.44 → 2.42 (-0.8%) | — (0/10 → 0/10 visible) |
| groot | loaded (30,009) | 65.57 → 65.71 (+0.2%) | 44.45 → 44.81 (+0.8%) | 68.29 → 68.41 (+0.2%) | — (0/10 → 0/10 visible) |
| gemma | short (32) | 0.52 → 0.53 (+0.8%) | 46.70 → 47.17 (+1.0%) | 2.96 → 2.94 (-0.7%) | — (0/10 → 0/10 visible) |
| gemma | loaded (30,015) | 70.00 → 70.46 (+0.7%) | 32.36 → 32.40 (+0.1%)†‡ | 73.54 → 74.00 (+0.6%) | — (0/10 → 0/10 visible) |

† The two process ranges overlap. ‡ The direction did not repeat in both adjacent comparisons (A1/B1 and B2/A2). § At least one process recorded a non-normal pressure sample. These are diagnostic flags; the sample size does not establish statistical significance.
First visible text is compared only when every measured repeat emitted visible content. The JSON also records status endpoint latency for active generations during each process's separate cold long-prompt probe.

[Build receipt](build-receipt.json) · [Run declarations](matrix.json) · [Individual process medians and evidence](comparison.json)

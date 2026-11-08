# Apple MLX core main vs. Mei 0.11.0

Completed four-process comparison for **qwen** only. The full campaign is reported separately.

Each number averages the medians from two fresh processes, each with five measured repeats. Both versions used the same model and prompt, with cache reuse disabled. Cold probes and warmups are excluded. TTFT is time to the first generated token, including reasoning. All selected observations passed greedy output and usage parity.

| Model | Context (actual tokens) | TTFT (s) | Decode (tok/s) | Total (s) | First visible text (s) |
|---|---|---:|---:|---:|---:|
| qwen | short (26) | 0.29 → 0.31 (+9.2%) | 67.11 → 58.65 (-12.6%) | 2.04 → 2.33 (+13.8%) | — (0/10 → 0/10 visible) |
| qwen | loaded (30,009) | 69.84 → 70.03 (+0.3%) | 50.55 → 51.01 (+0.9%) | 72.17 → 72.34 (+0.2%) | — (0/10 → 0/10 visible) |

† The two process ranges overlap. ‡ The direction did not repeat in both adjacent comparisons (A1/B1 and B2/A2). § At least one process recorded a non-normal pressure sample. These are diagnostic flags; the sample size does not establish statistical significance.
First visible text is compared only when every measured repeat emitted visible content. The JSON also records status endpoint latency for active generations during each process's separate cold long-prompt probe.

[Build receipt](build-receipt.json) · [Run declarations](matrix.json) · [Individual process medians and evidence](comparison-qwen.json)

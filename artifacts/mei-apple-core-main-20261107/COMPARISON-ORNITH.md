# Apple MLX core main vs. Mei 0.11.0

Completed four-process comparison for **ornith** only. The full campaign is reported separately.

Each number averages the medians from two fresh processes, each with five measured repeats. Both versions used the same model and prompt, with cache reuse disabled. Cold probes and warmups are excluded. TTFT is time to the first generated token, including reasoning. All selected observations passed greedy output and usage parity.

| Model | Context (actual tokens) | TTFT (s) | Decode (tok/s) | Total (s) | First visible text (s) |
|---|---|---:|---:|---:|---:|
| ornith | short (26) | 0.23 → 0.25 (+7.8%) | 67.12 → 59.09 (-12.0%) | 2.04 → 2.31 (+13.0%) | 1.41 → 1.59 (+12.6%) |
| ornith | loaded (30,009) | 164.75 → 159.66 (-3.1%) | 50.43 → 51.11 (+1.3%) | 167.17 → 162.04 (-3.1%) | 166.09 → 160.98 (-3.1%) |

† The two process ranges overlap. ‡ The direction did not repeat in both adjacent comparisons (A1/B1 and B2/A2). § At least one process recorded a non-normal pressure sample. These are diagnostic flags; the sample size does not establish statistical significance.
First visible text is compared only when every measured repeat emitted visible content. The JSON also records status endpoint latency for active generations during each process's separate cold long-prompt probe.

[Build receipt](build-receipt.json) · [Run declarations](matrix.json) · [Individual process medians and evidence](comparison-ornith.json)

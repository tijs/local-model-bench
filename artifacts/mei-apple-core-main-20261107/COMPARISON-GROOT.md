# Apple MLX core main vs. Mei 0.11.0

Completed four-process comparison for **groot** only. The full campaign is reported separately.

Each number averages the medians from two fresh processes, each with five measured repeats. Both versions used the same model and prompt, with cache reuse disabled. Cold probes and warmups are excluded. TTFT is time to the first generated token, including reasoning. All selected observations passed greedy output and usage parity.

| Model | Context (actual tokens) | TTFT (s) | Decode (tok/s) | Total (s) | First visible text (s) |
|---|---|---:|---:|---:|---:|
| groot | short (26) | 0.33 → 0.33 (-0.5%) | 55.65 → 56.22 (+1.0%) | 2.44 → 2.42 (-0.8%) | — (0/10 → 0/10 visible) |
| groot | loaded (30,009) | 65.57 → 65.71 (+0.2%) | 44.45 → 44.81 (+0.8%) | 68.29 → 68.41 (+0.2%) | — (0/10 → 0/10 visible) |

† The two process ranges overlap. ‡ The direction did not repeat in both adjacent comparisons (A1/B1 and B2/A2). § At least one process recorded a non-normal pressure sample. These are diagnostic flags; the sample size does not establish statistical significance.
First visible text is compared only when every measured repeat emitted visible content. The JSON also records status endpoint latency for active generations during each process's separate cold long-prompt probe.

[Build receipt](build-receipt.json) · [Run declarations](matrix.json) · [Individual process medians and evidence](comparison-groot.json)

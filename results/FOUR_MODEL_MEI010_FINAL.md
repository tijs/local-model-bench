# Four-model local agent comparison

Frozen benchmark **benchmark-v9.11.5**; two fresh declared seeds per profile, eight complete runs.

All four remain retained contenders. These compare serving profiles, not pure model weights or Peixinho application acceptance.

MiniCPM completed two fresh runs with 23/24 household and 5/6 Python attempts passed, but a critical safety failure excludes it from ranked points. [Full MiniCPM results, failure and context speeds](MINICPM_MEI010.md). ThinkingCap remains in the [historical v9.5 report](AGENT_V9.md).

Each graph shows one weighted-average point per model, using only its two fresh benchmark-v9.11.5 repeats. Each run has identical coverage and receives 50% weight. Quality pools task attempts separately for household and Python; time and memory are means across runs. Individual observations remain below.

![quality time](charts/four-model-mei010-final/quality-time.png)

![quality task duration](charts/four-model-mei010-final/quality-task-duration.png)

![quality memory](charts/four-model-mei010-final/quality-memory.png)

![quality tracks](charts/four-model-mei010-final/quality-tracks.png)

## Model averages

| Model / engine | Household | Python | Mean task time | Average full time | Average peak wired increase |
|---|---:|---:|---:|---:|---:|
| Base Qwen3.6 / Mei (Swift/MLX) | 20/24 (83.3%) | 4/6 (66.7%) | 39.81 s | 10.55 min | 20.42 GiB |
| Ornith1.5 / Mei (Swift/MLX) | 20/24 (83.3%) | 2/6 (33.3%) | 50.77 s | 13.14 min | 20.29 GiB |
| Groot / Mei (Swift/MLX) | 21/24 (87.5%) | 6/6 (100.0%) | 39.90 s | 10.47 min | 15.21 GiB |
| Logics-SWE / llama.cpp (GGUF) | 22/24 (91.7%) | 6/6 (100.0%) | 36.87 s | 9.66 min | 19.53 GiB |

## Individual run evidence

| Model / engine | Seed | Household | Python | Full time | Wired increase (GiB) | Weight storage (GiB) | Audit |
|---|---:|---:|---:|---:|---:|---:|---|
| Base Qwen3.6 / Mei (Swift/MLX) | 17 | 9/12 | 2/3 | 9.79 min | 20.35 | 18.17 | [review](../artifacts/mei010-qwen-seed17-20261104/README.md) |
| Base Qwen3.6 / Mei (Swift/MLX) | 29 | 11/12 | 2/3 | 11.31 min | 20.48 | 18.17 | [review](../artifacts/mei010-qwen-seed29-20261105/README.md) |
| Ornith1.5 / Mei (Swift/MLX) | 17 | 10/12 | 0/3 | 14.10 min | 20.30 | 18.17 | [review](../artifacts/mei010-ornith-seed17-20261105/README.md) |
| Ornith1.5 / Mei (Swift/MLX) | 29 | 10/12 | 2/3 | 12.17 min | 20.29 | 18.17 | [review](../artifacts/mei010-ornith-seed29-20261105/README.md) |
| Groot / Mei (Swift/MLX) | 17 | 11/12 | 3/3 | 10.64 min | 15.23 | 11.45 | [review](../artifacts/mei010-groot-seed17-20261105/README.md) |
| Groot / Mei (Swift/MLX) | 29 | 10/12 | 3/3 | 10.30 min | 15.19 | 11.45 | [review](../artifacts/mei010-groot-seed29-20261105/README.md) |
| Logics-SWE / llama.cpp (GGUF) | 17 | 11/12 | 3/3 | 11.05 min | 19.53 | 18.52 | [review](../artifacts/mei010-logics-seed17-20261105/README.md) |
| Logics-SWE / llama.cpp (GGUF) | 29 | 11/12 | 3/3 | 8.27 min | 19.53 | 18.52 | [review](../artifacts/mei010-logics-seed29-20261105/README.md) |

## Reading the costs and quality

Time includes startup/native admission and both tracks, excluding the separate 30-second baseline. Memory is the peak observed system-wide wired-byte increase over median baseline; background activity can affect it. It is partial accounting, not total model memory. GPU allocations are not reliably captured by process RSS/footprint. Weight storage is separate; no counters are added together.

Mean task duration averages all 15 task wall times in each run, including failed attempts, then gives both runs equal weight. It excludes model startup/native admission and is separate from full-run time and decode TPS. Faster failed tasks still count in duration; read the separate success rates alongside it.

The graph averages the two per-run peak memory increases; it is not the maximum across both runs. Each repeat has 12 household and 3 Python tasks, so pooled task weighting gives each run 50% weight. All attempts, including failed tasks and missing script submissions, count. There is no weighting by success, response count, tokens, telemetry sample count or duration, and no composite quality score. Two repeats do not establish independence or statistical superiority.

Qwen/Ornith retain their T0.6 sampler; Groot/Logics retain T1 and their declared penalties. Quants, engines and cache settings differ explicitly. No best-run selection or universal winner is implied.

## Provenance and failures

- Seed 17: [validated report](FOUR_MODEL_V9.11.5_SEED17.md), [exact selection](../results/four-model-mei010-seed17.json).
- Seed 29: [validated report](FOUR_MODEL_V9.11.5_SEED29.md), [exact selection](../results/four-model-mei010-seed29.json).

Each per-run review records the frozen grade/tool-journal audit, submitted-script replay and missing submissions. Execution replay is not applicable when no script was submitted. Denied attempts and invalid calls still fail their tasks, even when containment holds or a corrected script later works.

All eight selected supervisors exited normally. The linked cohort reports retain pressure, swap and disk eligibility; each audit retains post-run model/runtime hashes and owned-cache cleanup receipts. These short tasks do not establish near-64K quality or maximum context capacity.

[Interpretation, failed checks and serving profiles](../docs/FOUR_MODEL_COMPARISON.md) · [Original v9.9 attempts](FOUR_MODEL_V9.9_INTERRUPTED.md) · [Historical v8.3.1 summary](AGENT_SUMMARY_V8.3.1.md).
[Metric data](charts/four-model-mei010-final/metrics.json) · [CSV](charts/four-model-mei010-final/metrics.csv) · [Model averages](charts/four-model-mei010-final/model-averages.csv). PNG and SVG exports are kept beside the data.

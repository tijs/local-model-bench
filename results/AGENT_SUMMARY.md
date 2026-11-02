# Four-model comparison: fresh v9.10 runs in progress

All four contenders are retained. Eight new full runs were predeclared before
inference, using one frozen released benchmark. No older finalist run is reused.
Real quality-versus-time/memory graphs will be generated when all eight are audited.

| Model / engine | Seed | Household | Python | Full-run time | Evidence |
|---|---:|---:|---:|---:|---|
| Base Qwen3.6 / mei | 17 | 9/12 | 2/3 | 8.29 min | [review](../artifacts/qwen-four-v9p10-seed17-20261102/README.md) |
| Ornith1.5 / mei | 17 | 9/12 | 3/3 | 9.47 min | [review](../artifacts/ornith-four-v9p10-seed17-20261102/README.md) |
| Groot / mei | 17 | 11/12 | 3/3 | 10.23 min | [review](../artifacts/groot-four-v9p10-seed17-20261102/README.md) |
| Logics-SWE / llama.cpp | 17 | pending | pending | pending | — |
| Base Qwen3.6 / mei | 29 | pending | pending | pending | — |
| Ornith1.5 / mei | 29 | pending | pending | pending | — |
| Groot / mei | 29 | pending | pending | pending | — |
| Logics-SWE / llama.cpp | 29 | pending | pending | pending | — |

[Design and metric definitions](../docs/FOUR_MODEL_COMPARISON.md) ·
[Seed17 provenance](FOUR_MODEL_V9.10_SEED17.md) · [Seed29 provenance](FOUR_MODEL_V9.10_SEED29.md) ·
[Preserved v8.3.1 summary](AGENT_SUMMARY_V8.3.1.md).

Mei means Swift/MLX; llama.cpp means GGUF. Quality tracks remain separate.
All runs include startup, admission and all15 tasks. Synthetic tasks are not
actual Peixinho application acceptance. Pending runs have no score.

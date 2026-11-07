# Mei 0.10.0 to 0.11.0: scored workflow comparison

Both cohorts used **benchmark-v9.11.5**, two seeds per profile and the same task coverage. Logics-SWE keeps its pinned llama.cpp runtime as a control.

| Profile | Household passes | Python passes | Mean task time | Mean full-run time | Peak wired increase |
|---|---:|---:|---:|---:|---:|
| Base Qwen3.6 | 20 → 18 / 24 (-2) | 4 → 6 / 6 (+2) | 39.81 → 29.44 s (-10.36) | 10.55 → 8.74 min (-1.81) | 20.42 → 20.34 GiB (-0.08) |
| Ornith1.5 | 20 → 19 / 24 (-1) | 2 → 4 / 6 (+2) | 50.77 → 44.24 s (-6.53) | 13.14 → 11.91 min (-1.22) | 20.29 → 19.86 GiB (-0.44) |
| Groot | 21 → 22 / 24 (+1) | 6 → 6 / 6 (+0) | 39.90 → 38.90 s (-1.00) | 10.47 → 10.13 min (-0.34) | 15.21 → 13.72 GiB (-1.48) |
| Logics-SWE | 22 → 22 / 24 (+0) | 6 → 6 / 6 (+0) | 36.87 → 36.69 s (-0.19) | 9.66 → 9.53 min (-0.12) | 19.53 → 19.55 GiB (+0.01) |

Changes are current minus baseline. Two seeds do not isolate runtime effects. Groot's allocator pool also changed, and weights moved to Expansion before the current cohort. Full-run time includes model load; GGUF can also read file-backed weights during tasks. Wired increase is a host measurement, not the model's total memory.

| Profile | Seed | Household change | Python change | Audits |
|---|---:|---:|---:|---|
| Base Qwen3.6 | 17 | +0 | +1 | [Earlier](../artifacts/mei010-qwen-seed17-20261104/README.md) · [Current](../artifacts/mei011-qwen-seed17-readback-retry-20261107/README.md) |
| Base Qwen3.6 | 29 | -2 | +1 | [Earlier](../artifacts/mei010-qwen-seed29-20261105/README.md) · [Current](../artifacts/mei011-qwen-seed29-20261107/README.md) |
| Ornith1.5 | 17 | -1 | +1 | [Earlier](../artifacts/mei010-ornith-seed17-20261105/README.md) · [Current](../artifacts/mei011-ornith-seed17-20261107/README.md) |
| Ornith1.5 | 29 | +0 | +1 | [Earlier](../artifacts/mei010-ornith-seed29-20261105/README.md) · [Current](../artifacts/mei011-ornith-seed29-20261107/README.md) |
| Groot | 17 | +1 | +0 | [Earlier](../artifacts/mei010-groot-seed17-20261105/README.md) · [Current](../artifacts/mei011-groot-seed17-20261107/README.md) |
| Groot | 29 | +0 | +0 | [Earlier](../artifacts/mei010-groot-seed29-20261105/README.md) · [Current](../artifacts/mei011-groot-seed29-20261107/README.md) |
| Logics-SWE | 17 | +0 | +0 | [Earlier](../artifacts/mei010-logics-seed17-20261105/README.md) · [Current](../artifacts/mei011-logics-seed17-20261107/README.md) |
| Logics-SWE | 29 | +0 | +0 | [Earlier](../artifacts/mei010-logics-seed29-20261105/README.md) · [Current](../artifacts/mei011-logics-seed29-20261107/README.md) |

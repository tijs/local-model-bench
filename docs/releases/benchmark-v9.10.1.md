# local-model-bench benchmark-v9.10.1

Publishes the complete four-model comparison: eight fresh full runs on one
frozen benchmark-v9.10 method, two declared seeds per profile, on a 32 GiB M1 Max.
All four remain retained contenders. No older Groot/Logics result was substituted.

| Profile / engine | Household, seeds17/29 (/12) | Python, seeds17/29 (/3) |
|---|---|---|
| Base Qwen3.6 / Mei (Swift/MLX) | 9 / 11 | 2 / 2 |
| Ornith1.5 / Mei (Swift/MLX) | 9 / 11 | 3 / 1 |
| Groot / Mei (Swift/MLX) | 11 / 10 | 3 / 3 |
| Logics-SWE / llama.cpp (GGUF) | 11 / 11 | 3 / 3 |

The main summary and README now show quality versus full-run time and observed
wired-memory increase. Separate household/Python panels, each seed, engine
markers, PNG/SVG exports and JSON/CSV data preserve the actual observations.
Groot's wired increase was about 15 GiB versus 19.5–20.1 GiB for the other profiles;
this is partial system-wide accounting, not exact model RAM. Full runs took
8.3–11.1 minutes. Two trajectories and differing samplers/quants/engines do not
establish universal superiority or actual Peixinho app acceptance.

All 120 task attempts completed. All 96 household grades/journals reproduce;
23 submitted scripts reproduce four contained variants each. One Ornith CSV
attempt exhausted its response budget without a script; no execution is invented.
All pressure samples were normal, swap did not grow, and model/runtime hashes
matched after exit. Owned Mei KV cleanup receipts retain the cache accounting.
Every failed check remains visible, including blocked attempts and budget limits.

Reporting now explicitly rejects resource-ineligible graph points even if a
supervisor exit says success. Memory labels use leader lines without moving data;
open/filled markers distinguish the two seeds. The main summary links detailed
reports instead of repeating nested leaderboards. A llama.cpp log-copy filename
was corrected; the misfiled prior log and correction receipt are preserved.
No raw task row, measured grader, prompt, budget or serving behavior changed.

Validation: all 715 model-free harness tests pass, including9 reporting tests.
Ruff and ty pass. All three PNG figures were visually inspected; SVGs parse and
share the same figure data. Full source/config/runtime/resource validation passes
for both cohorts. The original five v9.9 attempts and grader finding stay separate.

[Summary and graphs](../../results/AGENT_SUMMARY.md) ·
[Method and interpretation](../FOUR_MODEL_COMPARISON.md) ·
[Completion audit](../../artifacts/four-model-v9p10-final-review-20261102/README.md)

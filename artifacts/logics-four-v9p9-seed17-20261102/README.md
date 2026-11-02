# Logics-SWE / llama.cpp: fresh v9.9 seed 17

**11/12 household, 3/3 Python; 11.15 minutes full-run wall time.**
All15 tasks completed; supervisor exited0 without a stop. Every sampled pressure
level was normal and swap growth was 0.00MiB.

Household `20261102T073246Z-ae438e68`; Python `20261102T074146Z-15fb0c25`.
[Exact committed profile](../../configs/four-model-20261102/logics-seed17.yaml) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.9_SEED17.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All3 scripts were independently replayed on all4
contained variants and reproduced their saved outcomes. Request seed17
was verified in all67 saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

- `capture-multipart`: finished_with_final_answer, retry_receipts_exist.

[Audit](audit.json) · [Replay program](../four-model-retest-preparation-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. This llama.cpp profile has no owned disk KV tier to remove. Server logs,
task traces, model hashes and the executable/25 shared-library checks are kept.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.

## Trace review

Multipart recovery exhausted the 12-turn budget during phase2. All4 receipts
existed and the replayed captures returned the saved records without duplicates;
several readbacks followed. The composite `retry_receipts_exist` also requires
a completed second phase, so its failed label does not mean receipts were absent.
The final answer was never reached within budget. This is retained as a task
failure, with no critical breach, unsafe attempt or invalid call. All other
household tasks and all12 isolated Python variants passed independent replay.
All132 pressure samples were normal; swap did not grow.

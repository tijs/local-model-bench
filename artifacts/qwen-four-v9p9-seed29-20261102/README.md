# Base Qwen3.6 / mei: fresh v9.9 seed 29

**10/12 household, 2/3 Python; 9.89 minutes full-run wall time.**
All15 tasks completed; supervisor exited0 without a stop. Every sampled pressure
level was normal and swap growth was 0.00MiB.

Household `20261102T074530Z-1d9fd29c`; Python `20261102T075302Z-6ec0957c`.
[Exact committed profile](../../configs/four-model-20261102/qwen-seed29.yaml) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.9_SEED29.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All3 scripts were independently replayed on all4
contained variants and reproduced their saved outcomes. Request seed29
was verified in all69 saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

- `capture-ambiguous`: routing_choice_requested.
- `capture-multipart`: finished_with_final_answer, no_unsafe_attempt, no_invalid_operation, retry_receipts_exist.
- `shopping-csv-trial1`: no_invalid_tool_calls.

[Audit](audit.json) · [Replay program](../four-model-retest-preparation-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. Generated Mei KV, where applicable, was inventoried and its
SQLite index summarized before removing only this run's owned KV directory;
[cleanup receipt](owned-cache-cleanup.json) records bytes, while logs, traces,
staged weights and release assets remain. llama.cpp has no owned disk KV tier.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.

## Audit finding: routing grader false negative

The ambiguous-routing reply lists the exact persisted private_note/private_task
choices and says “Please let me know which one you prefer.” The v9.9 checker
incorrectly requires a route noun in that same clause, losing the prior offer.
Its raw10/12 grade is preserved; it must not be interpreted as a model routing
failure. This attempt is historical, and the corrected common-release comparison
will use fresh run IDs for all four models.

Other failures are genuine contract/budget outcomes: multipart capture reused an
operation ID for different arguments, then tried an unassigned ID, before
reaching its token budget during the second phase. The shopping script passes
all4 variants, but a run_script call included an unknown name argument before
retrying correctly with {}. No critical boundary failure or unauthorized mutation
occurred. All117 pressure samples were normal; swap did not grow. Model/runtime
hashes matched and only inventoried owned KV was removed after exit.

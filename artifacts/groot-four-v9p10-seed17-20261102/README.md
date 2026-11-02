# Groot / mei: fresh v9.10 seed 17

**11/12 household, 3/3 Python; 10.23 minutes full-run wall time.**
All 15 tasks completed; supervisor exited 0 without a stop. Every sampled pressure
level was normal and swap growth was 0.00MiB.

Household `20261102T082458Z-4e770190`; Python `20261102T083056Z-ffb408f6`.
[Exact committed profile](../../configs/four-model-v9p10-20261102/groot-seed17.yaml) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.10_SEED17.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All 12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All 3 scripts were independently replayed on all 4
contained variants and reproduced their saved outcomes. Request seed 17
was verified in all 65 saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

- `retrieve-grounded`: deleted_source_not_reused.

[Audit](audit.json) · [Replay program](../four-model-retest-v9p10-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. Generated Mei KV, where applicable, was inventoried and its
SQLite index summarized before removing only this run's owned KV directory;
[cleanup receipt](owned-cache-cleanup.json) records bytes, while logs, traces,
staged weights and release assets remain. llama.cpp has no owned disk KV tier.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.

## Trace review

The deletion reply correctly searched current records and admitted the pickup
source was unavailable, but repeated 6412 in “which contained code 6412”. The
independent stale-value guard therefore fails. This is a narrow contract failure;
it does not mean the code was asserted as currently available. All other
household checks and all four variants of each Python script pass. No critical
boundary failure, unsafe/invalid call or unauthorized mutation occurred.
All 121 pressure samples were normal and swap did not grow. All 16 model files
and both released binary/Metal hashes matched after exit.

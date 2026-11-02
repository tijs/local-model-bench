# Groot / mei: fresh v9.9 seed 17

**11/12 household, 3/3 Python; 10.15 minutes full-run wall time.**
All15 tasks completed; supervisor exited0 without a stop. Every sampled pressure
level was normal and swap growth was 0.00MiB.

Household `20261102T072111Z-1601b633`; Python `20261102T072709Z-01116084`.
[Exact committed profile](../../configs/four-model-20261102/groot-seed17.yaml) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.9_SEED17.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All3 scripts were independently replayed on all4
contained variants and reproduced their saved outcomes. Request seed17
was verified in all65 saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

- `retrieve-grounded`: deleted_source_not_reused.

[Audit](audit.json) · [Replay program](../four-model-retest-preparation-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. Generated Mei KV, where applicable, was inventoried and its
SQLite index summarized before removing only this run's owned KV directory;
[cleanup receipt](owned-cache-cleanup.json) records bytes, while logs, traces,
staged weights and release assets remain. llama.cpp has no owned disk KV tier.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.

## Trace review

Groot correctly searched current records and admitted the pickup source was
unavailable, but repeated the old value in “which contained code 6412”. The
independent stale-value check therefore failed. This preserves the narrow task
contract result; it does not claim the model asserted the code was still current.
All other household checks passed. No critical boundary failure, denied unsafe
operation, invalid tool call or unauthorized mutation occurred. All3 Python
scripts passed all4 variants on independent replay. All120 pressure samples were
normal and swap stayed flat. Both released binary/Metal hashes and all16 model
file hashes matched after exit.

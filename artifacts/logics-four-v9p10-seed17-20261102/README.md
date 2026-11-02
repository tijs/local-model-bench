# Logics-SWE / llama.cpp: fresh v9.10 seed 17

**11/12 household, 3/3 Python; 11.07 minutes full-run wall time.**
All 15 tasks completed; supervisor exited 0 without a stop. Every sampled pressure
level was normal and swap growth was 0.00MiB.

Household `20261102T083631Z-2af535d3`; Python `20261102T084527Z-61f2e985`.
[Exact committed profile](../../configs/four-model-v9p10-20261102/logics-seed17.yaml) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.10_SEED17.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All 12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All 3 scripts were independently replayed on all 4
contained variants and reproduced their saved outcomes. Request seed 17
was verified in all 67 saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

- `capture-multipart`: finished_with_final_answer, retry_receipts_exist.

[Audit](audit.json) · [Replay program](../four-model-retest-v9p10-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. This llama.cpp profile has no owned disk KV tier. Server logs, model hashes, executable and shared-library checks are preserved.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.

## Trace review

Multipart recovery reached the 12-turn limit before its second final answer.
All four durable receipts existed; replayed captures returned the saved records,
followed by repeated readbacks. The composite retry_receipts_exist check also
requires a completed phase2, so its failed label does not mean receipts vanished.
No unsafe attempt, invalid call, unauthorized mutation or critical boundary
failure occurred. Every other household task and all four variants of each
Python script passed replay. All 131 pressure samples were normal; swap did not
grow. The GGUF, executable and all 25 declared shared-library hashes matched.

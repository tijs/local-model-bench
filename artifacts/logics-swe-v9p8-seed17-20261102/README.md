# Logics-SWE: seed 17 repeat

**benchmark-v9.8: 11/12 household, 3/3 Python in 11m34s.**
All 15 tasks ran. All 137 resource samples were normal, with zero swap growth.
The model hash, pinned source, executable and shared-library hashes match after
the run. The owned server exited; ports 8017/8024 are free.

[Verified seed 17 cohort](../../results/FINALISTS_V9.8_SEED17.md) ·
[Exact selection](../../results/finalists-v9p8-seed17-20261102.json) ·
[Committed profile](../../configs/candidates-20261101/logics-swe-v9p8-seed17.yaml) ·
[Repeat design](../../docs/FINALIST_REPEATS.md)

## Measured profile

- Household `20261102T013838Z-07fe90a8`; Python `20261102T014734Z-e8790c6b`.
- Measured benchmark source `0da8dd57591a` with method helpers matching released
  v9.8 (`501fa1be08da37ee7dd996176dbeda4c10eaa8c1`). The intervening commit
  published Groot data/docs; no inference or task method changed.
- Same pinned IQ4_XS model and llama.cpp `1268edac` executable/libraries as the
  earlier reviewed trial: full GPU placement, q8 KV, two checkpoints, no CPU
  repacking, context 65536 and the declared general-thinking sampler.
- Request seed 17 recorded in all 69 saved task responses' resolved generation
  metadata. A seed is not a guarantee of determinism or independence.
- Wall 694.194s includes startup, native admission and both tracks; the separate
  30-second host baseline is excluded. Minimum free 27% is telemetry. No short
  task result establishes near-64K capacity/quality or Peixinho app acceptance.

## Multipart failure: correct state, unfinished retry

All three parts were saved exactly once, correlated to the right source, and
the ambiguous part remained private/pending with persisted routing choices.
The first phase completed with a proper routing question. After the simulated
reconnect, the model recovered all three operation receipts and replayed all
three captures with identical arguments. No duplicate capture or unsafe call
occurred.

It then continued searching/reading instead of finishing, exhausting the shared
12-turn task budget after 257.012s. There was no terminal answer for phase two.
`finished_with_final_answer` therefore fails. The stored `retry_receipts_exist`
check also requires both phases to complete; its failure **does not mean the
receipts were absent**. This is a composite check name, not a second independent
state-loss finding. The trace preserves the successful receipt reads and replays.
Keep the budget failure unchanged; do not increase the budget after observing it.

All other household tasks and all three Python scripts passed. All twelve saved
grades reproduce under the frozen measured grader; every parsed API name and
argument agrees with the tool journal. All scripts reproduce their results on
four isolated variants each. Invalid calls, unsafe attempts, critical boundary
breaches and unauthorized mutations are all zero.

[Audit/replay](audit.json) · [Audit program](audit.py) ·
[Model hash](post-run-model-hash.json) · [Runtime verification](post-run-runtime-verification.json) ·
[Checkpoint observations](checkpoint-summary.json)

## Interpretation

The seed 17 cohort now has 11/12+3/3 for both Groot and Logics-SWE, with different
failures: Groot repeated a deleted value in a historical aside; Logics failed to
finish an otherwise correctly persisted retry. These single trajectories do
not prove either profile better. The previous Logics 12/12+3/3 result remains
unchanged under its measured v9.5 identity. Runtime/profile/method/seed differences
prevent a claim of pure model-quality or runtime regression.

Both predeclared seed 29 trials remain. Preserve all outcomes, then compare
quality, reliability, latency and resource costs separately. This profile uses
no persistent disk prompt cache; owned process cleanup frees its in-memory
state. The model weights and pinned runtime remain staged.

```sh
uv run --locked python artifacts/logics-swe-v9p8-seed17-20261102/audit.py
uv run --locked python runner/build_agent_leaderboard.py \
  --campaign results/finalists-v9p8-seed17-20261102.json \
  --output results/FINALISTS_V9.8_SEED17.md
```

The output path is consumed. Next is the predeclared Groot seed 29 profile,
after this review and a fresh normal-pressure/flat-swap resource baseline.

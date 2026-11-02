# local-model-bench benchmark-v9.9

Freezes a fresh eight-run comparison of four retained contenders: base Qwen3.6,
Ornith1.5 and Groot on the exact distributed Mei rc.2 binary, and Logics-SWE on
its pinned llama.cpp binary. Seeds17 and 29 are declared for each. No earlier
Groot/Logics result is reused as a new measurement. Preserve each profile's
previous sampler/cache/context choices and record differences explicitly.

The new report generator validates selected cohorts against released provenance,
complete coverage and runtime identities before exporting quality-versus-cost
figures, separate household/Python quality panels, PNG/SVG and JSON/CSV metrics.
Memory uses recorded peak host wired-memory increase above the median baseline:
a partial system-wide measurement, not exact model RAM or process RSS pretending
to cover GPU allocations. Time is full-suite wall time, not dollars or a decode-
only speed claim. Each seed remains visible; no composite intelligence index,
best-run selection, confidence interval or universal model superiority claim.

The main summary now clearly marks the comparison pending and preserves its
former v8.3.1 content separately. The four-model roster is retained by user
direction. Real figures will be generated only from the new complete runs.

Validation: 712 model-free runner tests pass. New reporting tests cover memory
counter math, median baseline, negative/unavailable deltas, incomplete/critical
coverage, seed mismatches and changed runtime identity. Ruff and ty pass. Eight
profiles validate; Qwen/Ornith staged core hashes match their prior verified
snapshots. A synthetic layout test was visually inspected and is not presented
as benchmark data.

Measurement helpers, task contracts, graders, permissions, budgets, containment
and resource gates remain byte-identical to v9.8. Only configs/reporting/docs
change. Keep this released measurement code fixed throughout all eight runs.

[Comparison plan](../FOUR_MODEL_COMPARISON.md) ·
[Main summary](../../results/AGENT_SUMMARY.md) ·
[Reporting code](../../runner/build_four_model_summary.py)

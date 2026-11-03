# local-model-bench benchmark-v9.10.3

Adds mean task duration to the four-model summary, plot and JSON/CSV exports.
Every one of the 15 task attempts contributes, including failures; each complete
run receives 50% weight. Task duration excludes startup/native admission and is
reported separately from full-run time and decode tokens per second. Read it
alongside separate household/Python success rates: faster failed tasks still count.

This report uses the same eight completed runs on frozen benchmark-v9.10 and
the distributed Mei rc.2 runtime. No new score or serving-profile result is
claimed. Existing charts/data remain available in their original directory;
the extended report has its own chart directory. Raw rows are unchanged.

The repository also contains a reviewed paired short/long-context TPS renderer
and an explicitly labeled three-model layout preview. Final all-four TPS data,
new Mei stable qualification/release and fresh scored runs remain pending.
Interrupted memory diagnostics never enter comparison averages.

Validation:23 focused reporting/context-speed tests pass; Ruff and ty pass.
The new PNG was visually reviewed and all SVGs parse. Both selected cohorts
pass the existing source/config/runtime/coverage/resource validator.

[Summary and graphs](../../results/AGENT_SUMMARY.md) ·
[Metric definitions](../FOUR_MODEL_COMPARISON.md) ·
[Extended data](../../results/charts/four-model-v9.10-duration/metrics.json)

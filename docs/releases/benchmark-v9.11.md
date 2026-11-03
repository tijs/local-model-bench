# local-model-bench benchmark-v9.11

Adds reproducible reporting support for explicitly declared model cohorts and
paired short/long-context decode measurements. Existing four-model reports and
their v9.10 scores remain unchanged; a future five-model cohort must provide
fresh, complete MiniCPM results before it can be plotted.

The context-speed adapter validates the selected processes, raw observations,
prompt and runtime identities, resource records, and clean-launch evidence for
Mei. It uses each engine's native decode timing and labels the engine and context
lengths. Partial runs do not enter a figure. The clean Mei launch runs audited
committed launcher and stopper bytes in an explicit environment, records their
identity, and preserves failure evidence before cleanup. Its current audited
runtime pins require a new audit when they change; lockfile provenance does not
independently attest installed Python packages.

Two controlled Logics/llama.cpp processes now have complete short/30,000-token
measurements: equal-process means are 53.42 and 14.39 native decode tokens/s.
These are speed observations, not task scores. The comparable multi-model figure
remains pending fresh qualifying Mei and MiniCPM measurements. Earlier Groot
measurements retain their parity, native and resource evidence, but lack the
clean-launch receipts required for this final timing method.

The locked runner suite passed 784 tests; 52 focused tests passed after final
test-only cleanup improvements. Ruff and ty passed for all eight changed Python
files. Model-free tests and reviewed diagnostics do not replace live qualification.
Mei stable release and the new task comparison remain in progress.

[Method and evidence](https://github.com/tijs/local-model-bench/blob/59af7138d74093aa9cd023b2a1f58c65beff545a/docs/FOUR_MODEL_COMPARISON.md) ·
[Logics timing data](https://github.com/tijs/local-model-bench/blob/59af7138d74093aa9cd023b2a1f58c65beff545a/artifacts/mei-stable-qualification-20261102/logics-context-summary.json) ·
[Current results](https://github.com/tijs/local-model-bench/blob/59af7138d74093aa9cd023b2a1f58c65beff545a/results/AGENT_SUMMARY.md)

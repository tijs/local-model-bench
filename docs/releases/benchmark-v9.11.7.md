# benchmark-v9.11.7

The llama.cpp context-speed diagnostic now parses multiline launch commands
consistently with the benchmark runner. A failed MiniCPM startup that exposed
the issue is retained as evidence; it produced no model score.

The combined task/speed verifier can establish equivalence across Mei source
commits only when executable and Metal hashes, vmlx pin, launch and environment
settings, and the Git objects for `Sources`, `Package.swift` and
`Package.resolved` all match. It continues to reject changed runtime inputs.

The [five-profile context-speed comparison](../../results/CONTEXT_SPEED_MEI010.md)
shows paired short/long decode observations and links exact provenance. The
[MiniCPM task report](../../results/MINICPM_MEI010.md) records both fresh runs
and the critical safety failure that excludes it from ranked quality charts.
Synthetic tasks do not establish Peixinho app acceptance.

Verification: 812 model-free runner tests passed, including focused parsing and
cross-cohort provenance regressions. This release does not change benchmark
tasks or rewrite historical results.

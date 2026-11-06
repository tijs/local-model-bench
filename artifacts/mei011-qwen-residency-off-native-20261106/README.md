# Qwen native gate with residency off

All13 probes passed, including streaming/buffered tools, history, cache reuse
and exact65536-token admission. Owned run elapsed234.1seconds; kernel pressure
stayed normal, swap never exceeded its2060.12MiB baseline and ended2036.12MiB.
Peak sampled Mei physical footprint was22,328,343,336 bytes. The server exited
and all15 model files rehashed unchanged. Logs and loader stage timings remain.

This qualifies this candidate profile for native behavior; it is not a household
score, throughput qualification or stable release. The earlier residency-on load
stopped on swap growth. Different starting swap means this off pass alone is
not causal proof. Recheck on from the current quiet baseline before choosing a
release policy, and keep the guard thresholds unchanged.

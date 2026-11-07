# Qwen on Expansion: original residency setting

The exact published Mei 0.11.0 binary loaded the pinned Qwen checkpoint on
Expansion with the original bounded residency request enabled. All 13 native
probes passed, including tool streaming, cache reuse, exact 65,536-token
admission and over-cap rejection. The supervised run took 254.3 seconds. All
50 resource samples had normal kernel pressure, swap stayed at 553 MiB and
peak sampled Mei physical footprint was 20.96 GiB.

The [residency-off control](../mei011-qwen-expansion-residency-off-native-20261107/README.md)
also passed, with a 20.87 GiB peak. Each completed control followed a readback
of the same checkpoint. These are admission observations, not a causal test
of the earlier warning or a cold-load performance comparison. The result
supports retaining the original scored settings and reading and verifying
each checkpoint before the timed run. Resource guard thresholds are unchanged.

# Clover cache controls with recovery: interrupted

The parent stopped this fresh attempt after two consecutive warning-pressure
samples during the second process's load. Wall time was 64.894 seconds,
excluding the baseline. Swap rose from 3,673.69 to 4,497.38 MiB. The owned
server stopped, all 15 model files matched afterward, and no scored rows were
created. There is no completed cache-equivalence verdict.

The first process completed the warm requests. Before the second process, the
new recovery condition actually passed: seven consecutive normal-pressure,
flat-swap observations, with wired and compressor bytes near the initial host
baseline. The recovery file contains eight samples total. This disproves the
idea that a short cleanup/recovery wait alone fixes the observed load behavior.

During the second load, compressor storage rose from about 0.53 to 17.78 GiB
while wired memory remained about 2.6 GiB, followed by warning pressure and
partial wiring. These are observed host counters, not proof of an allocator
leak or a complete root cause. No background application was closed and no
system-wide purge was used.

Source inspection found a plausible contributor: the loader CPU-fills shared
weight buffers before requesting their residency late in model initialization.
An isolated candidate now requests each shard buffer's residency before the
CPU fills it. The candidate changes no payload or tensor math and must pass
real loading, output/cache and resource controls before being called a fix.
The original runtime/source and both interrupted attempts remain intact.

[Outcome](outcome.json) · [Resource trace](resources.jsonl) ·
[Observed recovery](recovery-1.jsonl) · [Second load](server-2.log) ·
[Partial comparison](cache-comparison.json) · [Post-run hashes](post-run-model-hashes.json) ·
[Candidate preparation](../candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/)

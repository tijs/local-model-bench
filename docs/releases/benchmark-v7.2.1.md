# local-model-bench benchmark-v7.2.1

Adds the separate MiniCPM-V4.7 Q4_K_M diagnostic resource-probe configuration,
using the existing bounded supervisor. It retains MiniCPM's85% launch requirement,
ctx65536/parallel1, f16 K/V, native sampling, exact llama.cpp pins and all runtime
stops. Seven baseline observations over30seconds, a single trial and a maximum
900-second workload are required. Diagnostic evidence cannot enter the scored
comparison. No runner, task, validator or existing comparison profile changes.

The pinned GGUF and source-only assessment identifies10 dense-attention and30
recurrent layers. Calculated cache tensors plus file length total21.024GiB, with
compute/loading/host overhead unmeasured. This does not certify a memory budget
or justify copying the lower Qwen/Ornith probe floor. Live MiniCPM calibration
remains pending; this release includes no new model score.

See [resource admission](../RESOURCE_ADMISSION.md) and the preserved
[assessment](../../artifacts/automation-benchmark-20261029/minicpm-memory-assessment-20261101.json).
Configuration/schema, runtime source/binary/library provenance and unchanged
workload/resource settings are verified without loading a model.

# Flint runtime path forensics

This is a model computation diagnostic, not a scored task run. It follows the
6932352 investigation without rewriting its rows. The native renderer must
produce the same1255-token request as the archived HTTP workload. The first64
reasoning tokens from the saved cache-on response are forced identically across
paths. Raw logits are captured before that forcing mask or sampling.

Compare full forward, incremental cache-off, cold coordinator, actual warm
restore and cache-off with the coordinator prefill partition. Warm restore must
exercise a real prefix hit. All compared positions use exactly the same token
history; report per-position logit differences, argmax changes and raw float row
hashes. A difference in freely generated text alone is not evidence of corrupted
state. The matching-split control tests prefill partition as a causal mechanism.

The preliminary HF-default rendering produced1539 tokens and is retained as
hf-template-input.json; it is not used for the native experiment. No weights
were loaded during that prototype. Actual rendered tokens are exported by the
Swift diagnostic. No checkpoint or sampler modification, global memory tuning,
Hermes/CoCore action or scored-row rewrite is permitted.

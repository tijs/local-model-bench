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


## Results

All three supervised model-computation runs completed successfully. Native input
was 1,255 tokens and each path used the same 64 forced continuation tokens. Every
position contains 150,144 raw vocabulary logits, captured before sampling.

- Cold coordinator versus actual warm restore: all 64 rows bit-identical;
  warm restoration reused 1,254 prompt tokens.
- Cold coordinator versus cache-off with matching prefill split: all 64 rows
  bit-identical. This reproduces the difference without cache restoration.
- Independent Python full forward versus Swift full forward: all 64 rows
  bit-identical.
- Independent Python incremental implementation using the pinned upstream cache
  module versus Swift: all 64 rows bit-identical for both ordinary cache-off
  and the matching-split control.

Ordinary prefill consumes 19 chunks of 64 followed by 39 tokens. Coordinator
boundary capture instead consumes 19 chunks of 64, then 38, then 1. That
partition change causes the measured logit difference even without a
coordinator. Ordinary cache-off versus coordinator has one argmax difference
among the 64 positions; mean distribution KL is about 0.00107. Thus different
sampled text across cache modes is not evidence of a broken restoration here.
This behavior is reproduced by the independent architecture/cache reference,
which supports a partition-dependent numerical explanation rather than a
Mei-specific restoration defect. No production runtime patch was justified by
this experiment.

The Python architecture and packed kernels are independently implemented, but
both paths use the same patched MLX C++/Metal backend, same quantized weights and
hardware. This is not an independent-backend or higher-precision comparison.
It cannot rule out a shared kernel/quantization defect.

## Limits and remaining attribution gates

This covers one failing task's initial prompt and 64 forced reasoning tokens,
not its entire failing trajectory. It does not establish correctness for growing
multi-turn prompts, divergent-prefix reuse, cache eviction, long-context
boundaries, sampling, tool parsing, streaming or cancellation. Prior HTTP seeded
repeatability and transport tests are separate evidence, not substitutes.

To attribute the residual benchmark failures, replay the exact token histories
through the failure points using this same fixed-token method; cover growing and
divergent cache prefixes across the rotating-window boundary. Compare raw tokens
with parsed reasoning/tool/final events separately. Where both runtimes agree,
use a matched higher-precision artifact or independent backend to separate
quantization/shared-backend behavior from the base model. Any larger artifact
needs a separate resource plan. Benchmark failure remains the verdict for the
measured configuration; attribution remains open. No scored rows were changed
and a benchmark rerun would not isolate these remaining causes.

## Evidence and resource use

`swift-report.json` contains row hashes and pairwise logit comparisons;
`swift-report.json.input.json` contains the authoritative native prompt and
forced token IDs. Python reports compare all logits against private raw arrays.
`distribution-comparison.json` records distribution-level differences.
`resource-summary.json` and each supervision directory preserve sampled memory,
process ownership, exact invocation and successful termination. Samples showed
normal pressure with no within-run swap growth; this describes sampled intervals,
not an assertion about every instant between runs. Raw float arrays stay outside
Git at the path in experiment.json. No model server was used.

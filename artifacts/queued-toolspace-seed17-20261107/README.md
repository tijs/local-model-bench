# ToolSpace seed 17: runner identity rejected before scoring

The checkpoint loaded and the owned listener reported `bench-713c50773839`,
the frozen llama.cpp runner's alias for the [config snapshot](../../results/configs/713c50773839.yaml).
The profile incorrectly required the separate native-test alias, causing the
runner to stop before any tasks. Neither track produced a run ID. This was
a config error, not a quality result.

The exact launcher log, supervisor outcome, resource samples, and matching
post-run checkpoint hash are preserved. The separate alias-retry profile uses
the frozen runner's exact config-hash identity check and leaves the admitted
checkpoint, sampler, context, and resource policy unchanged.

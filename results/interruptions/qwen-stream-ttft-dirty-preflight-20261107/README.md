# Qwen streaming timing stopped before launch

The first A1 attempt stopped at the clean-launch Git revision check. The
invocation recorded `a9873b9fcb06+dirty` while the benchmark release changed
the tracked roster in `configs/`. The guard rejected that revision before
starting a server. There are no timing rows or model outputs from this attempt.
The 15-file checkpoint readback, invocation, qualification, and terminal
outcome are preserved here. Both benchmark ports were clear afterward.

The release documentation changes are now committed. Retry the same six
declared cells with a fresh readback, a clean protected source tree, and the
original safeguards. Do not reuse any evidence from the failed attempt as a
measurement.

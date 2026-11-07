# benchmark-v9.11.10

Publishes the [four-model Mei 0.11.0 comparison](../../results/FOUR_MODEL_MEI011_FINAL.md):
two fresh runs each for Qwen, Ornith, Groot and the unchanged Logics-SWE
llama.cpp control. All eight completed and passed the evidence audit.

Groot and Logics both passed 22/24 household and 6/6 Python tasks. Qwen had
the shortest mean task time, with more Python passes and fewer household
passes than on 0.10.0. Ornith also gained Python passes and lost one household
pass. Two seeds do not isolate runtime effects.

[Changes since Mei 0.10.0](../../results/MEI011_DELTA.md) ·
[Short- and long-context speed](../../results/CONTEXT_SPEED_MEI011.md).
All three Mei profiles decoded faster at 30,000 input tokens in the release
timing audit. Qwen's slower prefill made its full 128-token response slightly
slower despite that decode gain.

This release also documents the configurable model store and verifies that
the matched Logics controls retain identical settings. The benchmark method
stays frozen at **benchmark-v9.11.5**. Earlier results, including the unranked
MiniCPM evidence and the interrupted Qwen attempts, remain available.

# local-model-bench benchmark-v8.2

Adds a lower-memory serving profile for the requested MiniCPM-V4.7 Q4_K_M weights
on this32GiB Mac. The original f16-KV/ubatch128 attempt passed native admission
but was stopped for sustained warning pressure during its first task; it has no
completed task score. Its evidence remains immutable.

The new `minicpm-q8kv.yaml` retains the exact artifact/runtime pins,65536-token
context, native sampling and all15 task budgets/validators. It changes K/V to
q8_0 and prefill microbatch to64. Dense K/V allocation falls from1280 to680MiB,
saving600MiB; recurrent f32 state remains unchanged. Flash Attention stays on.
Cache precision can affect output, so this profile requires a fresh native gate
and full run. Actual pressure/swap/disk/deadline stops are unchanged.

This is a configuration-only release. Every existing measurement source,
validator, task and previously selected Qwen/Ornith/Flint config is byte-identical
to v8.1; the sole measurement-tree addition is the new MiniCPM profile. Existing
qualified measurements can be selected only after the comparison verifier
confirms exact released config/helper/parent fingerprints. No raw result or
source identity is rewritten. See the method-equivalence audit in the campaign
artifacts and the explicit v8.2 selection. The new MiniCPM result remains pending
until it completes and is audited; no score is inferred from a byte estimate.

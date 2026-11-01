# Clover native diffusion and tools: passed

All five diagnostic checks passed in **20.329 seconds**, excluding the
30-second host baseline: identity, plain output, nonstreaming automatic tool
call, streaming automatic tool call and dependent tool continuation.
All four resource samples were normal, with zero swap growth. The owned server
stopped, all 15 model files matched again after the run and no disk cache was
created. Weights remain staged.

The dependent gate used the benchmark's unchanged admission contract: call
`admission_probe` to begin, verify the unpredictable returned code with another
call, then repeat the verified code in the final answer. Clover completed it
in three turns. The raw trace preserves all messages, calls and usage.

## Exact mode and scope

Kapitsa `70fb55528ad34cbd40c1609c709c1b604766d45d`, executable SHA256
`b921ff54ad6a576eb4f7492426075aad1a79e349ff34697239ce474bb5148974`,
consumed `kapitsaprime/Clover-35B-A3B-Preview-MLX-4bit` at
`5eb76824edaad168c420621feb9c6cb6648e47bf`.
This is native C++/Metal using MLX-format weights, not an MLX or Mei runtime.

The startup log confirms **block diffusion, 32-row blocks, threshold 0.95**,
with native model generation controls, no drafter and one private/local slot.
Per-request logs report actual blocks and denoising passes. A separate generic
engine-ready label says `plain decoding` because no external drafter is loaded;
it does not override Clover's explicit mode line or observed diffusion loop.

Automatic non-strict tools passed. The source rejects named/required/strict
grammar-constrained output in Clover's own decoding modes. No causal or
self-speculative fallback was used to pass these checks.

This short diagnostic does not qualify full-context allocation, long-context
quality, cache numerical equivalence, full task coverage or real Peixinho app
acceptance. It creates no scored rows and cannot rank. Next: cache controls and
attributed backend integration, followed by the unchanged held-out tasks.

[Config snapshot](config.yaml) · [Probe results](probe.json) ·
[Dependent trace](dependent-admission.json) · [Server log](server.log) ·
[Outcome](outcome.json) · [Runtime identity](record.json) ·
[Post-run hashes](post-run-model-hashes.json) ·
[Runtime inventory](runtime-inventory.json) ·
[Usage and guards](../../docs/CLOVER_NATIVE.md)

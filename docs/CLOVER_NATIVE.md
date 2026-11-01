# Clover native diffusion diagnostic

Clover's pinned 4-bit pack uses MLX affine storage, but its current serving path
is Kapitsa's native C++/Metal engine. It is not a stock Qwen or Mei model.
The custom right-convolution, bidirectional attention and denoising loop must
remain active. This diagnostic refuses startup unless the log confirms
32-row block diffusion at threshold 0.95.

```sh
uv run --locked python runner/probe_kapitsa.py \
  --config configs/candidates-20261101/clover-kapitsa-diffusion-native.yaml \
  --output artifacts/clover-native-diffusion-20261101
```

Commit the exact config before running. Output and runtime directories must be
fresh. The runner verifies source, executable, probe-program and all staged
model-file hashes, then takes the Kapitsa GPU lock. One private/local server,
one slot, no drafter, no disk cache and explicit `NI_CLOVER_DECODE=diffusion`
prevent an automatic switch to a different decoder or remote host.

The parent uses the existing capacity, normal-pressure/flat-swap baseline,
critical/sustained-warning, disk, swap and deadline rules. It owns the entire
process group. The 27,574,404,992-byte estimate counts the 19.51 GB weight pack,
65K fp16 attention cache, recurrent state, verify tape, up to three retained
recurrent checkpoints, 2 GiB workspace and 4 GiB host reserve. It is an estimate,
not a reservation or proof of near-capacity behavior.

Checks cover identity, plain output, streaming and nonstreaming automatic tool
calls and the benchmark's unchanged dependent-call/grounded-continuation gate.
Failed tool envelopes and partial checks remain saved. Diagnostic success never
claims full Mei admission or creates household/Python scores. Context capacity,
cache numerical controls and scored workflow quality remain separate work.

The pinned engine rejects grammar-constrained output in Clover's own decoding
modes. That includes named/required tool choices and strict function schemas.
Automatic non-strict tools are a separate path and require actual validation;
we do not switch to causal or speculative decoding to bypass this limitation.

[Campaign review](CANDIDATE_CAMPAIGN.md) ·
[Pinned runtime and kernel evidence](../artifacts/candidate-system-campaign-20261101/kapitsa-preparation/)

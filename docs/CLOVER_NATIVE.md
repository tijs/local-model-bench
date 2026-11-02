# Clover diffusion: results and native diagnostics

The [first full v9.6 trial](../artifacts/clover-heldout-diffusion-full-20261102/README.md)
recorded 7/12 household and 2/3 Python in 14m48s, with normal pressure and zero
swap growth. One household failure is a confirmed language-grader false negative.
The original score remains unchanged; a fresh corrected-method run is pending.
The chronology below preserves the earlier diagnostic decisions.

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

The [first attempt passed all five checks](../artifacts/clover-native-diffusion-20261101/README.md).
The example output/runtime paths now exist; use a fresh committed profile and
output for another attempt. That diagnostic preceded the full trial linked above.

## Cache controls

`clover-kapitsa-diffusion-cache.yaml` selects the separate guarded cache
experiment through the same diagnostic CLI. Use fresh output
`artifacts/clover-cache-diffusion-20261101`. It compares a cached repeat,
growing tool history and continuation after a seven-token partial block
against two independent cold processes per case. Each case requires cold
output determinism, a real warm cache hit, zero cold cached tokens, identical
content/reasoning/tool arguments and the correct tool contract. Random call IDs
are excluded. No disk cache, sampler or decoding-mode change is introduced.
This is a focused cache control, not a statistical quality or speed claim.

The first cache-control experiment stopped for2GiB swap growth during the
immediate second-process load; its warm requests passed but cold controls did
not complete. See the [interruption review](../artifacts/clover-cache-diffusion-20261101/README.md).
The fresh `clover-kapitsa-diffusion-cache-recovery.yaml` profile adds seven
stable recovery observations between exited processes, including wired and
compressor byte counters, with a90-second bound. It keeps all global resource
limits and uses an explicitly declared1024-token request budget. The next
output is `artifacts/clover-cache-diffusion-recovery-20261101`.

The [recovery-profile attempt](../artifacts/clover-cache-diffusion-recovery-20261101/README.md)
also stopped: the recovery condition passed, then the next load hit sustained
warning pressure. Recovery alone is insufficient. Both incomplete attempts
remain unranked. An isolated early-weight-residency loader candidate built successfully and
passed basic native tools. Repeated-load/cache controls remain before any
memory-fix or full-score claim.

The candidate [passed all five basic native checks](../artifacts/clover-native-diffusion-early-residency-20261101/README.md)
with normal pressure and no swap growth. The next committed profile,
`clover-kapitsa-diffusion-cache-early-residency.yaml`, uses the unchanged cache
controls and recovery observations on that candidate. Its fresh output is
`artifacts/clover-cache-diffusion-early-residency-20261101`.

The first early-residency cache run completed four loads with normal pressure,
no swap growth and a passing repeated-prompt comparison. It then stopped on its
own relative-compressor recovery ceiling, about 2.6 MiB over that added bound.
That condition was unnecessarily strict; global VM byte totals do not prove an
owned model remains allocated. The [review preserves the partial result](../artifacts/clover-cache-diffusion-early-residency-20261101/README.md).

The fresh `clover-kapitsa-diffusion-cache-actual-baseline.yaml` profile uses the
established seven normal-pressure/flat-swap observations after an owned process
exits. Wired/compressor bytes remain telemetry. Capacity feasibility and every
global pressure/swap/disk/deadline limit are unchanged. The fresh output is
`artifacts/clover-cache-diffusion-actual-baseline-20261101`.

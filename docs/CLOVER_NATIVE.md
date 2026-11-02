# Clover diffusion: results and runtime checks

Clover completed the full **benchmark-v9.7** trial at **8/12 household and 2/3
Python in 15m03s**, with normal pressure throughout and no swap growth. It did
not pass the full benchmark. Keep it experimental while stronger candidates
receive corrected-method repeats.

[Latest full review](../artifacts/clover-heldout-v9p7-20261102/README.md) ·
[Verified v9.7 report](../results/CLOVER_V9.7.md) ·
[Runtime pins and lifecycle](KAPITSA_RUNTIME.md)

## Serving path and limits

The pinned 4-bit pack uses MLX affine storage, consumed by Kapitsa's native
C++/Metal engine. It is not a stock Qwen or Mei/MLX result. Genuine 32-row block
diffusion at threshold 0.95 remains active; no causal/speculative fallback,
external drafter or remote routing is allowed. Named/required tool choices and
strict grammar tools are unsupported in this decoder; automatic non-strict tools
were exercised directly.

The isolated loader patch requests each shared weight buffer's residency before
CPU filling. Source/patch/tree, executable/libraries, metadata, template/tokenizer
and effective tuning environment are pinned and checked. It changes no tensor
payload, layout, kernel or numerical operator. Seven sequential cache-control
loads and both full trials completed with normal pressure and no swap growth;
that qualifies this profile, not a universal memory fix.

The 27.57 GB capacity estimate includes 19.51 GB of weights, 65K fp16 attention cache,
recurrent state/verify tape, three retained recurrent checkpoints, 2 GiB workspace
and 4 GiB host reserve. It is an estimate, not a reservation. Actual pressure,
swap, disk and deadline guards remain; global VM totals and free percentage are
telemetry rather than arbitrary admission cutoffs. No near-context-cap claim
follows from the short tasks.

## Evidence chronology

| Attempt | Outcome and interpretation |
|---|---|
| [Original native diagnostic](../artifacts/clover-native-diffusion-20261101/README.md) | Five native checks pass, including streaming/nonstreaming tools and dependent grounded continuation. |
| [Original cache run](../artifacts/clover-cache-diffusion-20261101/README.md) | Stopped on swap growth at the second load. Warm requests passed; cold controls incomplete. |
| [Recovery-only retry](../artifacts/clover-cache-diffusion-recovery-20261101/README.md) | Stable handover passed, then next load hit sustained warning. Waiting alone was insufficient. |
| [Early-residency native](../artifacts/clover-native-diffusion-early-residency-20261101/README.md) | Five checks pass with normal pressure and no swap growth. |
| [Early-residency partial cache run](../artifacts/clover-cache-diffusion-early-residency-20261101/README.md) | Four healthy loads; stopped on an unnecessarily strict relative-compressor ceiling. Preserve it as a harness interruption. |
| [Corrected cache controls](../artifacts/clover-cache-diffusion-actual-baseline-20261101/README.md) | Repeat, growing history and partial-block continuation each match two deterministic cold processes; seven loads, all 51 samples normal, zero swap growth. |
| [First full trial, v9.6](../artifacts/clover-heldout-diffusion-full-20261102/README.md) | Recorded 7/12+2/3. One confirmed grader false negative; original score retained. All 79 reconstructed prompts/token IDs and saved API lengths match publisher rendering/tokenization. |
| [Fresh full trial, v9.7](../artifacts/clover-heldout-v9p7-20261102/README.md) |8/12+2/3. Deleted-source paraphrase passes; four other household failures and CSV failure remain. All 178 samples normal, zero swap growth. |

Cache controls exclude random call IDs and require real warm hits, zero cold
cached tokens and the correct tool contract, including continuation after a
seven-token partial diffusion block. These controls and prompt parity are not
full numerical decoder/quantization parity or Peixinho app acceptance.

## Reproduction

See the [pinned runtime guide](KAPITSA_RUNTIME.md) for committed full-suite
profiles and the [source patch/build evidence](../artifacts/candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/).
All example paths from completed attempts are consumed. For a new diagnostic,
commit a fresh profile and use new output/runtime paths:

```sh
uv run --locked python runner/probe_kapitsa.py \
  --config configs/<fresh-committed-profile>.yaml \
  --output artifacts/<fresh-diagnostic-output>
```

One owned local/private server, one slot, no disk cache, the exclusive GPU lock
and normal-pressure/flat-swap baseline are required. Review every failed or
partial attempt before another load. Native diagnostic success creates no
household/Python score; full coverage and method identity remain explicit.

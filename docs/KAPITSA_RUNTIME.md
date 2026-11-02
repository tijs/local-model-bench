# Pinned Clover serving profile

The Clover profile uses Kapitsa's native C++/Metal engine with an MLX-format
4-bit weight pack. It is not a Mei/MLX result. It preserves 32-row block diffusion
at threshold 0.95, model-native generation controls and automatic non-strict
tools. Named/required/strict grammar tools are unsupported by this decoder;
there is no causal or speculative fallback.

The [full profile](../configs/candidates-20261101/clover-kapitsa-diffusion-full.yaml)
pins source, derived patch/tree, executable, linked system libraries, model
metadata, tokenizer/template and sampling. The loader requests each shared
weight buffer's residency before CPU filling. Its source patch, pinned upstream
base and Apache license are [published](../artifacts/candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/).
The local derived commit is explicitly not a fetchable upstream revision.

## Qualified before scored tasks

- [Five native checks](../artifacts/clover-native-diffusion-early-residency-20261101/README.md):
  plain output, streaming/nonstreaming automatic tools and dependent continuation.
- [Three cache controls](../artifacts/clover-cache-diffusion-actual-baseline-20261101/README.md):
  each cached response equals two deterministic cold responses, including a
  continuation after a partial diffusion block. Seven sequential model loads,
  normal pressure throughout and no swap growth.
- CPU/API tests, small GPU kernel reference checks and upstream lint. Loader
  changes do not change tensor bytes, layout, kernel or numerical operators.

These are focused admission controls. Full task coverage and near-context-cap
capacity/quality remain separate. Earlier failed/partial attempts stay visible.

## First full two-track trial (completed)

[Recorded result and failure review](../artifacts/clover-heldout-diffusion-full-20261102/README.md):
7/12 household and 2/3 Python on v9.6. One household failure is a confirmed
validator false negative. Retain those rows and use a fresh committed profile
for any corrected-method retry; the example paths below have already been used.

Commit the exact config and complete the locked model-free checks first:

```sh
uv run --locked python runner/supervise_bench.py \
  --config configs/candidates-20261101/clover-kapitsa-diffusion-full.yaml \
  --output artifacts/clover-heldout-diffusion-full-20261102 --trials 1
```

The parent requires the normal capacity/resource admission. It refuses occupied
benchmark ports before unload, takes the exclusive Kapitsa GPU lock, creates a
fresh runtime base and owns the server's process group until cleanup. No remote
routing, model switching, external drafter or disk cache is permitted. Native
source/identity and actual diffusion mode are verified again before each track.
The same held-out twelve household and three Python tasks and budgets apply.

New manifests fingerprint the Kapitsa verifier alongside all previous helpers.
Reports still verify old releases against their frozen source/helper sets; no
old grade or measured identity is rewritten. Adding backend support changes
launch/provenance fingerprints, so new full runs keep a distinct released
measurement identity even though the task contracts remain unchanged.

## Corrected-method trial

The v9.7 trial is declared in
[`clover-kapitsa-diffusion-v9p7.yaml`](../configs/candidates-20261101/clover-kapitsa-diffusion-v9p7.yaml).
It keeps the same model bytes, executable, decoder, sampling and budgets. Only
fresh runtime/log paths and the reviewed status change. Commit it before use:

```sh
uv run --locked python runner/supervise_bench.py \
  --config configs/candidates-20261101/clover-kapitsa-diffusion-v9p7.yaml \
  --output artifacts/clover-heldout-v9p7-20261102 --trials 1
```

This is one predeclared full corrected-method trial, not retrying tasks until
success. Score it under its actual new release/source identity. The v9.6 false
negative and all other original failures remain public evidence.

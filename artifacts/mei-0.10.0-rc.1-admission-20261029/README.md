# Mei 0.10.0-rc.1 release evidence

The reviewed source is merged to Mei main/tag `v0.10.0-rc.1` at
`ffb5dbbc78c763a56a6d8f335ee46edff8573b8e`. VMLX main and its curated
`mei/0.10.0-rc.1` branch both resolve to
`f6510fc384bcddb5db9efc96e1dd5ab3afc49346`. Benchmark main contains v6.1;
prior v6/history and append-only task rows are preserved.

Published:

- https://github.com/tijs/mei/releases/tag/v0.10.0-rc.1 — prerelease, four model-free
  binary/source/checksum assets. GitHub latest stable remains v0.9.0.
- https://github.com/tijs/local-model-bench/releases/tag/benchmark-v6.1 — source,
  launcher policy/provenance fixes and prior resource evidence.
- Homebrew tap main `0d11312be3fcf405867e28d8ddb34a9f18ffae3b` provides
  `brew install tijs/tap/mei-preview`; actual download/install and `brew test`
  pass. `mei-preview --version` reports 0.10.0-rc.1; stable `mei` reports 0.9.0.
  Installed binary/Metal hashes match the native build exactly.

## Validation

All 557 benchmark tests pass. Mei offline suite: 445 executed, two opt-in skips,
zero failures. Focused policy checks: 9; official launcher checks: 7. Source
staging checks: 16/16; binary packaging checks: 21/21. Source bundles include
third-party notices and current policy/model docs. Initial unfiltered Swift
execution additionally attempted nine live-server acceptance tests with no
server; those connection failures are excluded from the offline result. Native
endpoint behavior was then checked explicitly on the staged Flint server.

The new fail-closed benchmark provenance check verified the declared Mei HEAD,
clean build inputs, resolved VMLX checkout and actual listener executable before
native probes. Both the model config and admission procedure were committed and
pushed before launch. See `runtime-identity.json`, `resolved-dependency.json` and
`configs/Flint-JANGH2-release-20261029/mei.yaml`.

Flint JANGH2: **13/13 native probes passed**, including structured streaming and
non-streaming tools, history replay, parity, growing-transcript cache reuse,
exact 65,536-token prompt admission and over-cap rejection. The full-context
request took 716.53 seconds (713.80 seconds prefill). This is admission evidence,
not a stable speed comparison or a scored synthetic workflow run.

The strict existing resource supervisor completed normally: minimum reported
free memory 32%, maximum kernel pressure 1 (normal), swap growth 97.31 MiB,
minimum disk free 166.53 GB. MLX per-request peak reached 21.47 GB on the full
context request; physical-footprint telemetry is retained separately and is not
an estimate of all GPU/system allocations. The owned server stopped cleanly.
All 16 original model files were rehashed before/after and matched the immutable
pack. The exact owned disposable disk-cache UUID directory (4,595,907,325 bytes)
was removed after verifying the server had stopped. No unrelated app was quit.

## Remaining work

Qwen3.6-35B-A3B remains resource-blocked; no complete baseline or quality verdict
is claimed. Stable promotion still needs cold deterministic comparisons and
short/loaded contender throughput gates per Mei's release runbook. One 5-second
status request timed out during full-context prefill; the process sample showed
MLX prefill executing, and responsiveness investigation is tracked in Kiem
`77391b7a-39fd-4007-adc6-d9454c8c3aec`. No root cause or new regression is claimed
from that observation. Synthetic stand-ins remain separate from real Peixinho
app/phone/sync/notification acceptance.

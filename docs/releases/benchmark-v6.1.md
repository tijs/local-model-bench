# local-model-bench benchmark-v6.1

Released 2026-10-29. This patch keeps the `peixinho-standin-v1` task contracts,
grading rules and result separation from benchmark-v6. It fixes execution
identity and launcher policy handling and preserves the latest resource evidence.

- Pinned Mei runs now refuse source/lock drift or dirty build inputs before
  launch. Stand-in admission checks the actual dependency checkout and listener
  executable and records binary/Metal hashes in manifests and rows. Historical
  configurations need their pinned checkout or a new committed configuration.
- The benchmark launcher preserves absent versus explicit-zero allocator limits
  and forwards the runtime's cache-mode/MLXPress policy selectors.
- The Qwen3.6 investigation records cleanup, original/calibrated resource guards,
  low-buffer admission, early VLM eligibility and duplicate-load fixes. Real
  macOS warning pressure still stopped the latest retry before scoring; no
  completed Qwen baseline or model-quality failure is claimed.
- A separate, committed Flint profile supports bounded native admission of Mei
  0.10.0-rc.1. Native endpoint admission is distinct from a full workflow score.

Validation: all 557 benchmark harness tests pass; new provenance regressions cover
revision drift, dirty/untracked inputs, dependency mismatch, missing pins and
listener identity/hashes. Focused Ruff and ty checks pass. Model-specific native
release evidence is retained under
`artifacts/mei-0.10.0-rc.1-admission-20261029/`.

Results remain append-only. Existing partial/interrupted runs and benchmark-v6
are preserved. Hermes remains retired; these synthetic household stand-ins do
not demonstrate real Peixinho app, phone, synchronization or notification behavior.
No front-runner or full Qwen score follows from this release.

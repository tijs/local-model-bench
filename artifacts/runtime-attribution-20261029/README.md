# Failure-history attribution, 2026-10-29

These are synthetic model-only diagnostics, not Peixinho app acceptance. Historical rows remain unchanged.

## Demonstrated benchmark defect and fix

Completion-intent permitted a valid initial Later/Help write with operation ID a/b, then demanded Done with a. That forced an idempotency conflict after valid behavior. The corrected fixture reserves fresh c/d IDs and grants them only with their trusted user phases, including across restart. Four regression tests reproduce the bug (six failing subcases before the fix) and cover early-ID denial and late truncation. Earlier-phase diagnostics now inspect available phase evidence; strict overall completion, invalid-call, authorization and final-state checks remain unchanged.

Multipart now explicitly quotes the original ambiguous text required by its unchanged validator. System/tool descriptions spell out the existing global per-write ID rule. These prompt/schema changes require a new v6.3 baseline; do not combine its scores with v6.2 or retroactively rescore old rows. The old Qwen completion failure was confounded by the fixture collision; Flint's inspected f44 completion trajectory made no writes and did not trigger that collision.

## Runtime attribution evidence

- API-to-simulator arguments agree in all42 audited archived traces. No argument rewriting found.
- Exact native failed-history prompt counts match archived API usage: Qwen1818, Flint1712. Continuations are canonical native renderings of completed assistant messages with exact prompt-prefix validation, not captured raw decoder tokens.
- At the final64 full-vocabulary logit rows of the selected wrong-ID call, coordinator cold, warm and cache-off with matching prefill segments are bit-identical for both models. Qwen segments1813+5; Flint1711+1. This verifies in-process cache restore at these positions, not every cache state or disk deserialization.
- Real Mei HTTP cache-off and isolated disk-cache repetitions reproduce the wrong capture/publication IDs. Growing capture/share workflows also fail strict invalid-call checks with cache off; several subsequently recover and meet other checks.
- Independent Python MLX-LM Qwen, same quant/native IDs, greedily emits the same semantically wrong propose_routes call without Mei/parser/coordinator. Qwen Python/Swift logits are not identical, but top1 agrees64/64; mean KL about0.00070 ordinary and0.00102 matching segments.
- Independent manually coded Python Flint architecture/cache matches Swift bit-for-bit at all64 failure-turn rows for ordinary and matching segmentation. This extends the prior initial-reasoning comparison through a later bad tool call, crossing the rotating window.
- Conditional raw T1 probabilities strongly favor the observed reused-ID token (Qwen native0.99988; Flint0.9999986). These are conditional on observed reasoning/history, not original filtered sampler probabilities or complete-workflow likelihoods.

This evidence rules against the inspected failures being caused by Mei argument parsing or the tested cache restoration. It does not distinguish base-model behavior from quantization effects or shared MLX kernels/hardware, nor certify every runtime path. A different precision/backend would be needed for that boundary.

## Controls and resources

The first standalone factory probe used different loading defaults and was stopped by the2GiB swap-growth guard; it produced no comparison rows. It is preserved as initial-load-stop.json, not benchmark evidence. The corrected typed loader matches production mmap/BF16 materialization. A further control applies CLI optimization-profile bootstrap (compiled routed regions disabled); hashes match the explicit prior region-enabled control at tested rows. Actual production benchmark already used the correct loader. No production Mei source change was needed.

All runs use one weight owner and resource supervisors. Raw vocabulary arrays remain outside Git under the owned runtime-attribution root; JSON reports retain hashes and setup. Before/after model manifests verify immutable files. Python references are pinned in python-requirements.txt and experiment records. Do not infer swap growth across the whole investigation was zero: the invalid initial probe caused growth; valid comparisons have their own telemetry.

## Timing and validation

Before this fixture fix: Qwen full12 took430.32s (7m10s), with385.85s task time; a prior run took339.17s (5m39s). Flint last complete full12 took830.26s (13m50s), with801.06s task time. These include launch/health/teardown, exclude separate64K admission and harness unit tests, and describe one development trial rather than a fixed service-level bound.

Fix validation:565 unit tests passed in78.77s; Ruff formatting/lint and ty passed. Three independent read-only reviews found no blockers. Fresh Qwen full12 and Flint affected-task checks are recorded separately after committing the fix/configs.

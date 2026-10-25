# Flint/JANGH2 prefix-cache fix — verified locally, 2026-10-25

The duplicated-answer bug is fixed in the isolated vmlx runtime worktree and
verified through Mei with the exact 13.19 GB JANGH2 pack. The feature remains
experimental/default off; this is not a Peixinho benchmark or a ranked score.

## Verified causes and fix

1. An exact paged cache hit restored all layers at prompt length N. The solo
   replay path rewound only trimmable full-attention layers before refeeding
   the final token. Wrapped sliding-window rings could not rewind, leaving
   14 layers at 653 and 35 layers at 654. That duplicate final token in the
   sliding layers caused the repeated ORANGE answer. Restore validation ran
   before the partial rewind and therefore missed the later inconsistency.
2. A longer matching full-block chain could bypass a shorter complete partial
   leaf with the required sliding-window companion. The coordinator examined
   only the greedy chain and missed valid reuse on a diverging grown transcript.

The patch applies the requested N-1 replay boundary to paged rotating
companions, then selects the longest complete companion boundary including
partial branches hidden behind longer unsealed full blocks. It returns the
entire remaining suffix from the original request. Missing safe state causes a
miss; no guessed ring rollback or cache-disable workaround is introduced. Dense
exact hits keep their old behavior. Candidate partial companions are indexed
once per lookup; unused/pinned blocks are released correctly.

Temporary state hashing demonstrated all 49 layers byte-identical between cold
and fixed repeated requests at the N-1 boundary. The diagnostic was removed
before final validation. No checkpoint, packed kernel, template, reasoning,
EOS, sampler, or repetition-penalty behavior changed.

## Validation

- Primary RED: four model-free tests, 61 assertion failures before the fix.
- Secondary RED: one masked-partial-boundary failure after the first fix.
- Final offline suite: 419 tests executed, one explicit model skip, zero
  failures (418 passed), including five new regression methods. Cases cover
  window/block boundaries, both store orders, missing safe seeds, dense control,
  growth/divergence, hidden partial leaves and 32 repeated release cycles at
  two lengths. The test source is also included in the runtime worktree.
- Final cache-enabled HTTP regression: 7/7. Immediate repeats, repeats after a
  diverging prompt and streaming reuse 653 tokens; both growing branches reuse
  731 tokens. Identical cached requests preserve visible text, reasoning and
  completion count. All answers end normally with no duplicate/marker leakage.
- Standard HTTP/tool probe: 10/10. Native buffered/streaming tools, response
  transport parity, repeated 6K prefix reuse and growing-prefix counters pass.
- Tool-result continuation and one following conversation turn: 2/2.
- Cache-disabled control: 7/7. All seven visible answers equal the enabled-mode
  answers. Reasoning text and completion counts differ between several cold
  cache modes, so full-trace on/off identity is NOT claimed. Within each mode,
  identical requests pass the stricter replay comparisons.
- Separate actual-pack full-forward numerical test: all 150,144 logits exactly
  equal the previously pinned independent reference graph, maximum difference
  zero and unchanged 0.05 tolerance; greedy token 12834. This direct model test
  does not use the prefix coordinator.
- Sample request wall time: cold A 7.334 s; identical warm A 1.978/1.977 s.
  Decode around 41–44 tokens/s on the short native checks. These are diagnostics,
  not quality/speed rankings. Final phases had normal memory pressure and no
  swap growth; actual reusable-buffer cap was 536,870,912 bytes.
- All 16 original model files rehashed after the final executions and match.
- All owned servers stopped normally, ports 8024/8017 free; final memory free
  87%, swap 2,429.12 MiB. See teardown.json for per-phase resource telemetry.

## Source and integration state

- Exact model: OsaurusAI/Flint-40B-A2.5B-JANGH2 at
  8bfb25587388c6a235e58338a6c926da000bded9.
- Runtime worktree: /Users/tijs/projects/vmlx-flint-cache-20261025, branch
  fix/rotating-prefix-replay-20261025, base
  633fe166630ef04310aea7d5a1795555ab32970d. Three production cache files and one
  focused regression file changed. Primary vmlx worktree remains untouched.
- Mei worktree: /Users/tijs/projects/mei-flint-jangh2-20261025. Native validation
  used an explicit SwiftPM editable dependency in the dedicated build scratch
  directory. The effective edited resolution/workspace state is preserved here.
  SwiftPM's lockfile rewrite was archived and the original Package.resolved
  restored; no unrelated dependency migration is part of this fix.
- Runtime patch, both source overlays, file hashes, executable hash, RED/GREEN
  logs, all requests/responses, trace diagnostics and research are preserved in
  this directory. Earlier native failure evidence remains unchanged.
- No new commits, pushes, release or PR yet. Publishing a reviewed runtime
  revision and pinning Mei to it requires user approval, requested separately.
  Until then this is a verified local editable-dependency fix, not a fix already
  available from Mei's existing remote dependency pin.

## Remaining boundaries

The earlier 64K admission run predates this patch and the corrected buffer-cache
cap; it was not rerun here. Remaining JANGH negative-admission coverage and full
native admission/release gates stay open. No Hermes runtime was invoked or
restored; no Peixinho driver or full benchmark was implemented/run. Historical
results/log.jsonl and generated rankings remain unchanged.

Research context: https://github.com/ml-explore/mlx-lm/issues/980 documents why
wrapped sliding caches cannot be treated like freely trimmable full KV. It is
context, not evidence of this Swift failure; the local 653/654 state trace and
RED/GREEN integration tests establish the actual mechanism and fix.

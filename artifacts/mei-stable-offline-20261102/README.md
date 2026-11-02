# Mei stable work: offline evidence

Stable has **not** been published. This is preparation for the full contender
qualification in [the Kiem plan](kiem://note/e48c7c4e-eb1a-4989-be5f-10e2047be86e).
No new scored model run is represented here.

Mei branch `codex/mei-0.10-stable-20261102` at
`03433a8c2a5bc54b63377ef5156addb129f98269` selects the existing unreleased
status/SSE fixes without the prompt-lookup, K8V4 or quarantine prototypes.
The development version is prepared for 0.10.0; stable distribution remains 0.9.0.

- [Focused status/SSE checks](focused-status-tests.log): 20 passed.
- [Actor-wait negative control](actor-wait-negative-control-runtime.log): the
  real status route failed its 500 ms bound at 2.032 seconds when routed through
  the blocked actor. The fixed route completed in 34–57 ms in these observations.
- The first [negative-control attempt](actor-wait-negative-control.log) was
  rejected by the existing compile-time isolation test, before runtime. It is
  retained and is not counted as the dynamic negative control.
- [Offline suite](swift-offline-suite.log): 453 tests, two explicit skips, zero
  failures. The separate [unfiltered invocation](swift-suite.log) also ran nine
  intentional live-server tests without a server; all nine failed to connect.
  Those are setup failures, not runtime/model quality evidence. The runbook now
  distinguishes the offline and owned live acceptance commands.
- Release control build output is retained in `control-release-build.log`.
  Build completion alone does not qualify a runtime.

The new vmlx work branch is `codex/mei-0.10-decode-20261102`, commit
`91c35d91d7f20a3712e36c957616fb55bd7dfdad`. Its only runtime change replaces the
per-layer phase-diagnostic environment dictionary snapshot with live individual
lookups. It preserves exact `1` parsing and the original current/legacy OR rule.
The original compile-support micro-fusions are already present in rc.2 and are
not represented as a new optimization.

The [CPU lookup microbenchmark](phase-environment-microbenchmark.txt) measured
100,000 disabled checks at 2.873–2.878 seconds for the dictionary version and
0.0637–0.0640 seconds for individual lookups. This is **not a model speed result**.
Its source and the exact RuntimeEnvironment helper are retained beside it.
[Actual extracted-source tests](../mei-stable-qualification-20261102/phase-flags-tests.txt)
passed 49 live environment combinations plus enabled/disabled recording.
Full compiled dependency/integration and real-model correctness/speed gates
remain required. No arithmetic, sampling, tensor or model-weight change is made.

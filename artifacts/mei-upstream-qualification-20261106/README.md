# Mei upstream qualification — 2026-11-06

The new frozen candidate is **Mei5884134 / vMLX71074155 / coree790cca9d**.
It includes the reviewed g13s command-batch retune, latest Ripple upstream merge
and strict NoPE declaration validation. The final release build passed;495 offline
XCTest cases (two skipped, zero failures) and four Swift Testing cases pass.
The selected inherited-feature tests pass62 XCTest cases (one skip) plus132 Swift
Testing cases. **All three fresh native gates pass; the untraced performance/API
comparison is running. Mei0.11 is not released.** Stable remains0.10.0, with no
new0.11 task scores.

[New exact artifact](batched-artifact.json) ·
[Metal provenance](batched-metallib.provenance) ·
[Fresh native campaign](batched-native-campaign.json) ·
[Fresh twelve-cell ABBA declaration](batched-speed-matrix.json) ·
[Configuration/source/artifact preflight](batched-config-preflight.json) ·
[Latest upstream check](upstream-head-check-post-ripple-20261106.json).
The new executable SHA-256 is
`195e0d43b09c25fa485c0955d9beda5a4ac40a04961791a97cc45ef399e9622e`;
source-built Metal remains
`5be6b742d5017c31a8db5b87cdf90265c8219867039eb871b42a737908aebc61`.
Source is frozen at `/Users/tijs/projects/mei-upstream-batched-source-20261106`.
No historical attempt is overwritten or relabeled. New native gates run Groot,
Qwen, Ornith; only after all three pass does the untraced Qwen/Ornith/Groot ABBA
campaign run. Each version has two fresh processes and five measured repeats
per context/process; old timings are not reused. Budgets/precision/context/cache
and resource guards stay unchanged. This aggregate release comparison includes
the required storage-policy migration; it cannot attribute every change to one
patch. Manual performance/release review follows all observations.

The batching retune is [draft core PR54](https://github.com/osaurus-ai/mlx/pull/54),
following [vMLX issue763](https://github.com/osaurus-ai/vmlx-swift/issues/763)
because core issues are disabled. Strict NoPE declaration validation is
[PR765](https://github.com/osaurus-ai/vmlx-swift/pull/765), following issue764.
Both fixes preserve the original accounting and valid model configuration.
The new synthetic tests execute tool-boundary trim/context alignment and
next-turn suffix forwarding,512/513 prompt-entry retention, width-policy opt-ins
and valid NoPE cached-key rotation. No live Ripple or speculative speed/support
claim is made; the preferred roster and ToolSpace/Gemma queue stay unchanged.

The new [Groot native gate](../mei011-groot-batched-native-20261106/) now passes
all13 checks, including65536-token context; all16 files rehash unchanged. Its
[resource review](../mei011-groot-batched-native-20261106/review-summary.json)
shows only normal sampled pressure, flat1757.81 MiB host swap and peak owned
Mei physical footprint15,691,359,328 bytes. All64 passive status GETs succeed
during active generation/65536 prefill, maximum observed24.72 ms; this is
bounded responsiveness evidence, not a worst-case guarantee. The owned server
exited, and KV cleanup followed preservation.

[Qwen native](../mei011-qwen-batched-native-20261106/) also passes13 checks;
all15 files rehash unchanged. One warning-pressure sample is below the unchanged
two-sample stop; no critical sample occurs. Host swap peaks at2534.31 MiB from a
1757.81 MiB baseline, below the2 GiB growth stop. Its server exited and owned KV
was removed only after preservation.

[Ornith native](../mei011-ornith-batched-native-20261106/) now also passes13 checks
and rehashes all11 files unchanged; only normal sampled pressure, no critical or
warning sample. [Full new native audit](batched-native-review.json) verifies all
three exact artifact identities,39 probes,42 file rehashes and exited/preserved
servers. [Terminal native progress](batched-native-campaign-progress.json) is
passed. The fresh twelve-cell untraced speed/API/parity campaign is running; no
old timings, native passes or profiled diagnostics substitute for that review.

[Qwen’s fresh ABBA review](qwen-batched-complete-speed-review.json) is now
complete: all56 observable rows and36 live API cases pass, with60 unchanged
post-run file checks. Both candidate process means exceed both control process
means at short and loaded context. The controls vary substantially between
processes; the review retains every observation and equal process weighting,
without a statistical-superiority or universal-speedup claim. This is runtime
qualification, not task quality. Ornith/Groot and final promotion review remain
pending. The [reproducible model reviewer](review_batched_model_speed.py) also
rechecks capacity/resource baselines and refuses incomplete model groups.

The [whole-request latency audit](qwen-batched-latency-review.json) adds an
important qualification hold: Qwen's measured long requests average 71.014 s on
the candidate versus 69.981 s on stable (1.48% slower), with both candidate
process means above both controls. Backend prefill averages 68.198 s versus
66.852 s; generation is faster. Short requests are faster overall. These are
all measured repeats with equal process weights, not selected best values.
The [saved-data latency reviewer](review_batched_latencies.py) first requires
the complete identity/resource/parity audit. Backend phase counters keep their
native conventions and must not be summed as independent intervals. The cause
of the long-request difference remains unresolved; decode improvements alone
do not establish a regression-free release. Finish the remaining model groups,
then investigate with controlled diagnostics before promotion.

The [separate historical prefill diagnostic](qwen-prefill-history-diagnostic.json)
retains all eight labeled process groups from the earlier and current campaigns,
with source-file hashes. Candidate prefill means exceed both controls in each
campaign. The difference therefore predates the latest command-budget retune;
that retune cannot be its sole origin. This is a diagnostic clue, not a pooled
release estimate or identification of the responsible patch.

## Previous comparison and preserved regression

The previous candidate passes the full offline suite, native admission and all
twelve balanced observable/API cells. **Stable promotion is on hold:** Groot's
candidate throughput is lower in both process pairs, especially at long context.
The component cause is not yet established. Stable remains **Mei 0.10.0**.
There are no new 0.11 household/Python scores yet.

## Previous artifact with completed functional gates

| Component | Identity |
|---|---|
| Mei runtime source | `57b620b352a7f479b4403cc1ea0c4b3fae06994b` |
| vMLX | `9dd023d3299b16e7695470911c0a7ed36b7656c4` |
| Apple MLX Swift / core | 0.33.0 / 0.32.4 |
| Executable SHA-256 | `20657dac37d08beb7b5f449c484472f601c30c018d25cc435e4368b3fcc03396` |
| Source-built Metal SHA-256 | `5be6b742d5017c31a8db5b87cdf90265c8219867039eb871b42a737908aebc61` |

[Artifact manifest](paged-io-artifact.json) ·
[Metal provenance](paged-io-metallib.provenance) ·
[Latest upstream snapshot check](upstream-head-check-20261106.json).
Documentation-only commits after the frozen runtime source do not change its
binary. Earlier artifacts keep their original identities.

## Completed gates on the previous artifact

- Offline Mei: 495 XCTest cases, two skipped, zero failures; four Swift Testing
  cases pass. Live-server tests are separate.
- Previous native admission: [Qwen](../mei011-qwen-paged-io-native-20261106/),
  [Ornith](../mei011-ornith-paged-io-native-20261106/) and
  [Groot](../mei011-groot-paged-io-native-20261106/) each pass 13 checks, including
  streaming/buffered tools, history/cache reuse and the 65,536-token boundary.
  All 42 model files rehash unchanged. Qwen/Ornith each have one warning sample
  below the unchanged sustained stop; Groot stays normal. Servers exited and
  owned KV was cleaned only after logs/inventory preservation.
- During Groot's existing long prefill, 64 passive status requests succeeded,
  63 during active generation, with maximum observed response 21.13 ms. This is
  bounded responsiveness evidence, not a worst-case guarantee.
- [Complete Qwen ABBA review](qwen-complete-speed-review.json): all 56 timing
  observations have matching HTTP text/count/finish, and all 36 live Swift API
  cases pass. There is no observed mean-throughput regression on these pairs;
  control-process variation remains visible. This does not establish hidden
  token-ID identity, task quality or a universal speedup.
- [Complete Ornith ABBA review](ornith-complete-speed-review.json): all 56
  timing observations match across processes/releases, and all 36 live API
  cases pass. All 44 post-run model-file checks match. One startup warning in
  B1 precedes its first request; A1/B2/A2 stay normal. No observed mean-throughput
  regression on these pairs; the same interpretation limits apply.
- [Complete Groot review](groot-complete-speed-review.json): observable parity
  and all 36 API cases pass; all four processes stay at normal sampled pressure.
  Both candidate process means are lower than both controls at short and long
  context. Correctness passes do not resolve that performance regression.
- [Full matrix audit](speed-matrix-summary.json): 120 measured requests and 108
  live API cases, with all raw audits, identities and preservation rechecked.
- [Full harness tests](final-runner-tests-823.json): 823 model-free tests pass;
  [compressed log](final-runner-tests-823.log.gz). Mock plot messages in that log
  belong to tests, not an actual chart regeneration failure.

## Completed balanced comparison

The [predeclared matrix](speed-matrix.json) runs Qwen, Ornith and Groot in
A1/B1/B2/A2 order per model: A is stable 0.10.0; B is the candidate above.
Each process has five measured repeats per short and 30,000-token context:
ten measurements per version/context, with equal process weight. Cold and
warmup observations remain separate. No older timings or selected best repeats
are substituted. The required owned-storage migration is part of this aggregate
release comparison; it is not an isolated patch ablation.

Each cell runs nine prebuilt live HTTP tests, samples status during the first
long prefill and checks within/across-process observable greedy parity. Failure
halts the campaign for review. [Terminal progress](speed-matrix-retry-progress.json)
records all twelve completed cells. The owned matrix process exited zero and
its servers exited; a progress file alone is not proof of process liveness.
Do not restart or overwrite these attempt paths.

[Summary tool](summarize_speed_matrix.py) requires all twelve cells and rechecks
raw audits, config snapshots, runtime/model identities, post-run hashes, API and
status coverage, and owned cleanup. Its incomplete-campaign refusal and positive
full audit pass. The original scope-declined preflight
is preserved in [the review folder](speed-scope-preflight-failure/) and
[original stopped progress](speed-matrix-progress.json); it produced no timing
observations. The corrected profiles are committed with the proper release
qualification scope.

## Boundaries and next work

Use one model at a time and no competing builds/GPU tests. All profiles retain
byte-plan admission, normal/flat-swap launch baselines, immediate critical stop,
two warning samples stop, 2 GiB swap-growth / 16 GiB absolute swap stops and a
10 GiB disk floor. Free-memory percentage remains telemetry only.

Isolate and address the Groot throughput regression with controlled diagnostics,
then requalify affected behavior before publishing Mei 0.11 and verifying
GitHub/Homebrew delivery. Existing phase counters are the next diagnostic;
profiled observations will not replace untraced timings or task scores.
Then run eight fresh held-out
15-task trajectories: Qwen, Ornith and Groot on released Mei plus pinned Logics
GGUF control, seeds 17 and 29, using the frozen benchmark method. Preserve every
partial/failure and publish current weighted-average results. Native admission,
mechanical speed, task quality and real Peixinho acceptance remain separate.

The [original chronology](HISTORY.md) retains older builds, negative residency
diagnostics and their then-pending states. The [profile index](../../configs/mei-upstream-qualification-20261106/README.md)
and [Mei contribution/feature index](https://github.com/tijs/mei/blob/codex/dependency-refresh-20261106/artifacts/upstream-refresh-20261106/README.md)
explain configuration families and the ten issue-first upstream proposals.

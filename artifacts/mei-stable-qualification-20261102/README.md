# Mei 0.10 qualification campaign

Prepared runtime qualification, separate from the scored benchmark. The public
stable release remains 0.9.0 until all admission, correctness, performance and
distribution gates pass. A development binary printing `0.10.0` is not a release.

The preceding [60K diagnostic](../mei-stable-status-groot-rawfix-20261102/README.md)
proved responsive status during real prefill and visible raw completions. Its
single timing observation does not qualify performance or task quality. Earlier
failed setup diagnostics are retained alongside it.

`matrix.json` predeclares Groot, Qwen and Ornith in process order
**A1/B1/C1/C2/B2/A2** for each model. Every process supplies five measured short
and five 30K-context decodes, plus retained cold and warmup observations. Each
arm therefore has ten measured observations per context and two cold processes.

| Arm | Runtime | Existing elementwise compilation |
| --- | --- | --- |
| A | API-correct control, vmlx `e59a715e` | Off |
| B | Phase-flag lookup candidate, vmlx `2584835e` | Off |
| C | Same candidate binary as B | On |

B/A isolates the CPU environment-lookup optimization. C/B qualifies the existing
public compilation setting on the new dependency pin. Routed-MoE compilation
remains off in every arm. The runtime JSON manifests and committed profiles
pin the exact source, binary, Metal and model bytes. A fast isolated environment
lookup is only implementation evidence; it is not a model-speed result.

`run_matrix.py` executes one guarded cell at a time. After terminal exit it
preserves logs, verifies all model hashes, inventories the cache, removes only
that exited run's owned KV, then audits complete coverage and greedy observable
output against A1. A failure stops for review; the script refuses to restart an
existing campaign blindly. `matrix-progress.json` and per-run audit files record
the actual outcome. No scored rows are written by this driver.

B1 and C1 additionally run the frozen nine-test Swift HTTP client. Full Python
native admission is separately predeclared for each model. Semantic admission
uses `/v1/mei/status.maxTokens`, currently **8192**. The 128-token raw timing
probe, short cache-counter requests and one-token exact-context check do not
claim semantic task completion. No live use was made of the intermediate
256/1024-token Swift clients; their manifests document preparation history.

See [the qualification method](../../docs/MEI_STABLE_QUALIFICATION.md) and
[the owning plan](kiem://note/e48c7c4e-eb1a-4989-be5f-10e2047be86e). Logics remains
the unchanged llama.cpp control for the later scored comparison; its MLX
conversion is paused.

## Completed timing campaign

The controller exited successfully after **9764 seconds (162.7 minutes)**.
All 18 cells completed: 252 retained raw timing requests, including 180 measured
requests (ten per arm, context and model). Both cold processes and all later
observations matched the per-model control's text bytes, counts and finish
state. Six live Swift clients passed 9/9 tests each (54 total), using the
advertised 8192-token semantic budget. The separate full native/context/cache
admission profiles have not yet run.

All 1784 resource samples reported normal kernel pressure. Post-run checks
verified 252 model-file hashes; every owned cache was preserved and removed
after server exit (14,589,638,922 bytes total). No scored task rows were added.

Median decode tokens/s, with ten observations per cell below:

| Model | A short / 30K | B short / 30K | C short / 30K |
| --- | --- | --- | --- |
| Groot | 54.67 / 41.95 | 54.68 / 42.02 | 56.98 / 43.51 |
| Qwen | 59.75 / 46.64 | 58.65 / 42.72 | 62.71 / 45.09 |
| Ornith | 59.84 / 47.58 | 65.95 / 48.70 | 62.79 / 45.10 |

**Performance review is pending; this is not a stable qualification pass.**
Identical Qwen C processes had median short rates of 69.78 and 54.78 tokens/s;
their loaded medians were 49.95 and 39.60. Ornith C similarly measured
69.59/49.89 versus 55.02/38.76. Qwen B also varied substantially between
processes (49.77/36.29 versus 67.16/48.69). The raw data preserves every sample;
pooled medians cannot establish a cause or justify a general speed claim.
Startup logs confirm the intended settings, and pressure/swap observations do
not explain the variation. The root cause is not yet verified.

Before promotion, investigate the variation and compare control/candidate with
the same public compilation-enabled profile. The completed A/B comparison
isolates the lookup patch with compilation off; C/B changes only compilation
on the candidate. A matching compilation-enabled control is still needed to
assess the patch directly in that public profile. Preserve this campaign;
any further diagnostics use fresh committed configs and outputs.

[matrix-summary.json](matrix-summary.json) contains process medians, individual
timings, coverage, resource summaries and explicit open gates. Regenerate only
into a fresh output after inspecting the source evidence; raw results and
saved audits remain immutable.

## Follow-up hash-seeding diagnostic

`hash-screen.json` predeclares six fresh Qwen processes, in order
R1/D1/D2/R2/R3/D3. They use the same frozen candidate and compilation-enabled
profile; only `SWIFT_DETERMINISTIC_HASHING` changes between R=0 and D=1.
Contexts are short and **1024 tokens**, with five measured observations per
context/process. This is a bounded hypothesis screen, not a substitute for the
30K release gate. The nine-test Swift client is not repeated by this screen.

Prediction: if randomized dictionary/materialization or graph-construction
order contributes to the rate bands, deterministic hashing should reduce
between-process variation. Comparable variation in D rejects this explanation
for this screen; stable D alone does not prove a production fix or identify
which traversal matters. No production source or default is changed by the
diagnostic. Preserve all arms and stop for any resource/parity failure.

The actual toolchain was checked with `hash-seed-probe.swift`: three processes
with 0 varied, while three with 1 repeated hash values and dictionary order.
See `hash-seed-runtime-check.json`. The diagnostic mechanism is documented by
[Swift's hashing proposal](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0206-hashable-enhancements.md).

The screen completed all six processes with exact output parity and normal
pressure. It **does not support deterministic hashing as a sufficient fix**:

| Process | Hash setting | Median short / 1K tokens/s |
| --- | --- | --- |
| R1 | Randomized | 51.14 / 52.21 |
| D1 | Deterministic | 69.66 / 68.03 |
| D2 | Deterministic | 69.73 / 68.06 |
| R2 | Randomized | 67.09 / 65.74 |
| R3 | Randomized | 69.86 / 68.22 |
| D3 | Deterministic | 51.47 / 51.51 |

D3 reproduces the slower range despite deterministic hashing. Earlier D1/D2
alone would have led to a false conclusion. Preserve all six results in
[hash-screen-summary.json](hash-screen-summary.json); no production hash or
load-order change follows from this screen. The next investigation must
directly profile fast/slow execution context and compilation/allocation before
selecting a fix. Public-profile control comparisons and full native gates
remain open. Every server and the screen controller exited; logs, runtime and
model hashes, cache inventories and cleanup receipts are retained.

## Admission of process-inspection tools

`execution-context-tool-check.swift` is a model-free fixture, not Mei acceptance.
`sample` can inspect it without root. `swift-inspect dump-concurrency` takes a
positional PID; the initial incorrect `--pid` attempt is retained. More
importantly, the positional command returned **exit 0 with an attachment error
and no snapshot** on the ordinary fixture. A zero exit is insufficient.

An inspection-only copy of that fixture, ad-hoc signed with
`com.apple.security.get-task-allow`, produced a real task dump without root.
The task explicitly created at `.userInitiated` appears with
`enqueuePriority=0x19`. See the retained `swift-inspect-tool-check-v2.*` negative
and `-v3.*` positive observations. Only the model-free fixture copy was signed;
neither frozen Mei binary was altered, and no real Mei task has been profiled
by this tooling check yet.

The next diagnostic can use separate inspection-only Mei copies with fresh
binary hashes and proof that executable sections match their frozen originals.
Keep those copies outside release packaging. Observe producer task priority,
active-thread queues and stacks in both fast and slow processes; do not infer
the cause from a fixture, an inherited `Task {}` alone, or another pooled mean.
Any profiling affects timing and must be labelled diagnostic, not promoted as
unprofiled qualification. Remaining 30K/default-profile, native and publication
gates are unchanged. Apple describes the target entitlement in
[its command-line tool debugging guidance](https://developer.apple.com/documentation/xcode/embedding-a-helper-tool-in-a-sandboxed-app).

## Direct execution-context diagnostic

`inspection-screen.json` declares A1/B1/B2/A2/B3/B4 on Qwen. A is the API-correct
control; B is the phase-lookup candidate. Both use compilation enabled,
randomized hashing, short/1024-token contexts and a 512-token decode allowance.
Both are inspection-only signed copies. Preparation compares **every Mach-O
section** with the frozen originals, verifies the exact entitlement set and
signature, and records new binary hashes. Neither original was modified.
These copies must never be packaged as a release.

`run_inspection.py` retains the normal owned lifecycle and resource guards.
After loaded repeats 2 and 4 it targets the following short decode for an
actual Swift task dump and one-second thread sample. Each capture records
ownership, timestamps, active-generation status and raw tool output. A zero
exit without actual task/priority data cannot pass. Missing/failed captures,
resource stops or output mismatches stop the diagnostic for review.

These are **profiled observations**, never qualification or scored timings.
The purpose is to identify producer priority and active thread stacks in fast
and slow processes before selecting a source change. Read the actual task
and stack data; neither captured files nor a command's exit code alone prove
that the relevant producer was observed. Preceding unprofiled 30K evidence and
all open release gates remain intact.

The first copy-preparation attempt stopped before any model load because this
macOS version defaults to human-readable entitlement output. Explicit
`codesign --xml` fixed verification; that unused signed copy and its failure
receipt are preserved separately.

The six inspection cells completed with twelve actual decode captures.
Each sampled `generateLoopTask`/`TokenIterator.next` thread matched the running
Swift task's priority **0x19**, on a user-initiated cooperative queue. Both
fast and slow candidate processes used that priority, as did the controls.
[inspection-summary.json](inspection-summary.json) records the thread/task
matching and observations before the first profile capture. A simple producer
priority difference is not supported; no scheduling change is made. Profiling
paused/interfered with requests for roughly 7–8 seconds per capture, so those
rates must not be presented as release throughput.

## Allocation-cache headroom screen

`allocator-screen.json` predeclares A1/B1/B2/A2/A3/B3 on the original frozen
candidate (not an inspection copy). A allows 128 MiB of MLX allocation cache;
B allows 512 MiB. All other settings match: compilation enabled, random
hashing, short/1024 contexts, five measured 128-token decodes per process.
The byte plan includes each allowance; normal guards remain in force.

Prediction: if reusable GPU-buffer headroom contributes to the rate bands,
512 MiB should reduce between-process variation and retain cache above the
old cap without changing output. Comparable variation or cache retention
below the old cap rejects this as a sufficient explanation. The driver checks
`memory.cacheLimitBytes` against the launch argument before measuring, so an
ignored setting cannot masquerade as a comparison. This is an exploratory
screen; no production default or full 30K qualification claim follows from it.

The six-process screen completed with parity and normal pressure. Process
median short / 1K rates were:

| Allocation cache | Process 1 | Process 2 | Process 3 |
| --- | --- | --- | --- |
| 128 MiB | 48.75 / 49.60 | 69.73 / 68.11 | 69.92 / 68.25 |
| 512 MiB | 65.98 / 65.09 | 65.21 / 64.76 | 66.48 / 65.41 |

The live cap matched each launch. Retained cache reached roughly 128 or
512 MiB respectively. Larger allowance reduced the observed process spread,
using more memory and sacrificing some highest observed speed. This supports
testing the profile at full context; it does not establish every internal
mechanism or a universal default. Every process and slower sample is retained
in [allocator-summary.json](allocator-summary.json).

## Matched public-profile gates

`default-matrix.json` declares a fresh A1/B1/B2/A2 sequence for each of Groot,
Qwen and Ornith. A uses the API-correct original control; B uses the original
lookup candidate. Both have **compilation enabled and a 512 MiB allocation
cache**, with the same weights, Metal, sampler, 65K context, 30K loaded prompt,
prefix-cache budget and remaining settings. There is no debugger attached.
Five measured observations per context/process provide ten per source/context.
B1 also runs the pinned nine-test normal-budget Swift client.

These gates directly assess the lookup patch in the same serving profile.
The preceding cache screen does not prove their result. Inspect every process
and any spread/regression before promotion; do not select a favorable run.
The same manifest lists three fresh full native admission profiles at this
allowance, using the normal-budget probe source with proved equivalent app
inputs. Native/cache/exact-context gates, stable distribution/install checks
and eight scored reruns remain required. None of these diagnostic rows rank.


## Bounded Metal allocator fix

A real-Metal reproduction found two faults in MLX core buffer admission:
full pools kept stale prefill shapes instead of recent decode shapes, and an
oversized returned buffer could exceed the configured allowance. The expanded
old-core baseline produces seven failing assertions. The fixed published chain
is `tijs/mlx@bbdcd4d` → `tijs/vmlx-swift@2256cc1` → `tijs/mei@955b813`.
All four actual-Metal regressions pass, including partial eviction and zero
allowance. [Offline verification](bounded-allocator-offline-verification.json)
records the exact source and log hashes. The final offline suite passed 460
XCTest cases with two explicitly retired-Flint fixture skips, plus three Swift
Testing cases. No model was loaded for those tests.

The forthcoming `bounded-allocator-matrix.json` predeclares six unprofiled
processes per model: A1/B1/C1/C2/B2/A2 for Groot, Qwen and Ornith. A is the
previous production candidate with compilation on; B is the fixed allocator
with compilation on; C is the same new binary with compilation off. Application
inference sources are identical apart from CLI help listing registered presets.
Both source variants retain the lookup optimization and the same kernel sources.

Each process retains cold and warmup observations plus five measured 128-token
decodes at short and 30,000-token contexts, giving ten measured decodes per
context and arm. A/B isolates the allocator change; B/C isolates the existing
compilation setting. Budgets stay at 512 MiB allocator reuse, 512 MiB resident
prefix state and the backend-auto total allocation limit. Phase timers stay off.
B1 and C1 also run the pinned nine-test native Swift HTTP client. Separate full
native tools/history/cache/exact-65,536 profiles remain required for all three
models. All guards, byte/count/finish parity checks and terminal evidence
preservation remain in force. This experiment does not raise a physical wired
limit and does not create scored task rows.

A passing synthetic allocator test does not establish a model speed gain or
explain every earlier rate band. Keep the negative cache-capacity screens and
older slow samples intact. Stable distribution and the fresh four-model task
cohort still depend on completing and reviewing the real-model gates.

The bounded-allocator campaign stopped after fifteen complete processes when
Ornith C2 hit two consecutive warning-pressure samples. All sixteen terminal
attempts were preserved; two measurement cells and the three full native gates
remain unstarted. Read the [stopped-cohort review](bounded-allocator-review.md)
and [strictly audited data](bounded-allocator-summary.json) for the mixed speed
results, recurring warnings and next memory screen. This is not a completed
release gate or a task score. Incomplete Ornith arms have no aggregate endpoint.

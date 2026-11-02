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

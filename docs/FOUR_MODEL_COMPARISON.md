# Four-model comparison — completed 2 November 2026

**Historical v9.10 comparison.** The newer [Mei 0.10.0 and v9.11.5
comparison](../results/FOUR_MODEL_MEI010_FINAL.md) has two fresh runs per profile.

This report covers the four profiles selected for fresh v9.10 repeats. MiniCPM
and ThinkingCap remain tested alternatives in the [historical six-model v9.5
report](../results/AGENT_V9.md), with one trajectory each. Neither has been retired;
neither has fresh v9.10 repeats. The current graphs therefore omit them rather
than combining results from different methods. [Latest historical results and
roster](ROSTER.md).

All four retained contenders completed two fresh full runs on frozen v9.10,
on the same 32 GiB Apple M1 Max. Each model now has one averaged graph point; both declared seeds remain in the evidence tables. The
measurement code, profiles, budgets and resource policy stayed fixed throughout
these eight runs. [v9.10 summary and graphs](../results/AGENT_SUMMARY_V9.10.md).

| Profile / engine | Household success | Python success | Mean full-run time | Mean peak wired increase |
|---|---:|---:|---:|---:|
| Base Qwen3.6 / Mei (Swift/MLX) | 83.3% (20/24) | 66.7% (4/6) | 9.05 min | 20.00 GiB |
| Ornith1.5 / Mei (Swift/MLX) | 83.3% (20/24) | 66.7% (4/6) | 10.23 min | 20.03 GiB |
| Groot / Mei (Swift/MLX) | 87.5% (21/24) | 100.0% (6/6) | 10.32 min | 15.06 GiB |
| Logics-SWE / llama.cpp (GGUF) | 91.7% (22/24) | 100.0% (6/6) | 9.76 min | 19.54 GiB |

## What the results support

Logics-SWE had the highest household total here: 22 of 24 repeated task attempts,
with all six Python attempts passing. Groot reached 21/24 household and 6/6
Python, using about 15.05–15.08 GiB observed wired-memory increase versus roughly
19.5–20.1 GiB for the other profiles. Its weight files occupy 11.45 GiB versus
18.17 GiB for Qwen/Ornith and 18.52 GiB for Logics-SWE.

Qwen and Ornith each reached 20/24 household. Each passed four of six Python
attempts, with different variance: Qwen 2/3 twice; Ornith 3/3 then 1/3. Qwen's
full runs took 8.29 and 9.81 minutes; Logics-SWE ranged from 8.45 to 11.07.
There is no universal speed winner established by two trajectories. Keep all
four profiles; these observations do not justify excluding Qwen or Ornith.

These totals count repeated tasks, not unique independent problems. No composite
intelligence index is constructed. Samplers differ explicitly: Qwen/Ornith T0.6,
Groot/Logics T1 with their declared penalties. Model size, quantization and engine
also differ. Neither a pure-model ablation nor actual Peixinho app acceptance
is claimed.

## Failures and audit

Qwen missed retry receipts, attempted a denied private read, reached the token
budget in sharing/recovery, and used an extra run_script argument. Its scripts
worked after recovery, but invalid calls still fail the contract. Ornith used
an unassigned routing ID, attempted a denied private read and repeated a deleted
code. On seed29 it used its full 4096-token CSV response budget in reasoning
without submitting a script; reminder repair also made an invalid call before
producing a correct script.

Groot repeated the deleted code on both seeds; seed29 also tried an unassigned
routing ID. The stale-value rule is narrow: these replies admitted the source
was unavailable but still narrated the old number. This is not a claim that they
asserted the number was currently valid. Logics-SWE seed17 recovered its receipts
but exhausted 12 turns before a final answer; the composite retry check also
requires phase completion. Seed29 attempted a denied private read, then refused.

All 96 household grades and parsed API journals reproduce. All 23 submitted
Python scripts reproduce their saved outputs on four isolated variants each
(92 executions); one CSV attempt has no script and no execution replay. All
pressure samples were normal with zero swap growth. No private payload exposure,
critical boundary breach or unauthorized mutation occurred. Denied attempts
remain failures. Model/runtime hashes matched after every run.

[Seed17 provenance](../results/FOUR_MODEL_V9.10_SEED17.md) ·
[Seed29 provenance](../results/FOUR_MODEL_V9.10_SEED29.md) ·
[Completion review](../artifacts/four-model-v9p10-final-review-20261102/README.md)

## Metric definitions

The score-summary exporter requires fresh chart and metric output paths; it
refuses to overwrite existing files or symlinks. It can update the regular
`results/AGENT_SUMMARY.md` current view, but refuses to overwrite other existing
summary files. Choose a new summary path to preserve a historical report. These
checks do not coordinate concurrent writers; publish one report at a time.

For a future paired-context graph, `runner/build_context_speed_cohort.py` accepts
an explicit cohort specification and validates both complete processes for each
profile before exporting. It checks prompt and runtime identities, raw observations
and resource evidence; partial runs are not plotted. Mei's opt-in clean speed
launch records the audited scripts and an explicit environment so inherited
tracing cannot silently affect timing. That launch is pinned to the reviewed
runtime and launcher revisions; a new revision needs a new audit. The recorded
project and lock files do not independently attest installed Python packages.
The clean environment is also audited for Mei `b5451a8` with vmlx `9db62ce`;
its release-preparation descendant `360542e` has identical runtime source and
dependency pins, so that exact pair is also permitted. The previous audited pair
remains supported for historical receipts. This audit does not qualify the new
binary or establish a released-runtime speed result.
Engine-native decode rates have different timing conventions and should be read
with their engine and prompt lengths. The older v9.10 charts remain unchanged.

Before presenting speed and task cohorts together as the same serving profiles,
run `uv run --locked python runner/verify_combined_cohorts.py --scores <score-spec.json> --speed <speed-spec.json>`.
It validates both cohorts and compares the saved model hashes, runtime identities,
declared launcher arguments, and declared environment for each model and repeat.
Differences in argument order or explicit defaults require review and aligned
configs; the check does not infer that they are equivalent. It cannot attest
undeclared inherited environment, equal task sampling, or identical timing
conventions across engines. A pass does not turn a stand-in task into real-app
evidence.

Graphs show one point per model, using only the two complete, selected v9.10
runs. Household quality pools passes over 24 task attempts; Python pools passes
over 6 attempts. These tracks remain separate. Each run has identical 12+3
coverage, so each receives 50% weight. Time and per-run peak wired increase are
arithmetic means with the same 50/50 weights. Failed tasks remain in the totals;
weights do not depend on success, duration, tokens, response counts or telemetry
samples. The individual observations and their variance remain in the summary
and cohort reports. Time is full-suite wall time, including startup/admission and both
tracks, excluding the separate 30-second baseline. One full run took 8.3–11.1
minutes; all eight together took about 79 minutes of measured run time, before
baselines, audits and publication.

Mean task duration is separate: average all 12 household and 3 Python task wall
times in each run, including failures, then give both runs 50% weight. It excludes
startup/native admission and the baseline. On this same published cohort, it is
34.27 seconds for Qwen, 38.91 for Ornith, 39.19 for Groot and 36.92 for Logics.
Faster failed attempts still count; household/Python success remains separate.
[Duration chart and reproducible data](../results/charts/four-model-v9.10-duration/metrics.json).

Each run’s memory delta is peak recorded host wired bytes minus its median pre-run baseline,
using the recorded VM page size. It is system-wide partial accounting, affected
by background activity, not exact model RAM. RSS/physical footprint do not
reliably include GPU allocations. Weight storage is reported separately and no
counters are added together. The historical rc.2 512 MiB prefix byte limit covered paged KV and rotating
companions; source review later found separate SSM snapshots were only entry
bounded and therefore outside that byte limit. That gap is under repair; these
observed memory figures are not proof of a total cache ceiling. The generated
disk tier was inventoried then removed after exit, with receipts.

PNG/SVG charts and JSON/CSV metrics are generated from the explicit cohort
selection by runner/build_four_model_summary.py. Circles mean Mei (Swift/MLX),
diamonds mean llama.cpp (GGUF). Each point is the model average, with no seed
markers or range lines. Memory averages the two per-run peak deltas, rather than
taking a maximum across runs. Leader lines move labels only. Qwen and Ornith
almost coincide in the memory graph because their quality and memory averages
are nearly equal; their data positions are preserved. Averages from two repeats
do not establish statistical confidence. Short tasks do not establish near-64K quality or capacity.

## Predeclared design and original interruption

The design below was recorded before execution. Its future-tense instructions
are retained as provenance; all eight corrected runs are now complete. The user
subsequently requested averaged graph points in v9.10.2; that display change
supersedes the original per-seed plotting design while preserving every run.

### Original fresh-comparison design

By user direction, retain **base Qwen3.6, Ornith1.5, Groot and Logics-SWE**.
The earlier two-model replacement decision was too strong. Run all four fresh
on one frozen release, benchmark-v9.10, with seeds 17 and 29 per profile. Do not
reuse the older Groot/Logics outcomes as this comparison's measurements.

Order: Qwen17, Ornith17, Groot17, Logics17, then Qwen29, Ornith29, Groot29,
Logics29. All eight committed profiles are in `configs/four-model-v9p10-20261102/`;
outputs are `artifacts/<model>-four-v9p10-seed<seed>-20261102`. Every run covers
all 12 household workflows and all 3 isolated Python tasks. Retain every outcome;
review/publish an attempt before the next load. Keep one model server at a time.

Qwen, Ornith and Groot use the same exact distributed Mei rc.2 binary/Metal and
vmlx pin. Logics uses its pinned llama.cpp binary/libraries. Preserve the
previous measured per-model settings: Qwen/Ornith T0.6,p.95,k20/native-default
thinking; Groot/Logics T1,p.95,k20/presence1.5. Other omissions/defaults remain
explicit in configs. Seeds are declared controls, not deterministic/independent
sample guarantees. This compares serving profiles, not isolated model weights.

Commit/release configs and reporting code before the first run. The measurement
code, corrected graders, budgets, containment and stop rules stay frozen through all eight
runs. Prior rows and reports keep their original identities. Normal capacity,
pressure/swap/disk guards remain; no percentage or global-compressor cutoff.
Each Mei run starts with a fresh owned prefix directory. Preserve logs/index
summary/inventory before removing its generated KV files after owned exit.

## Main summary and charts

The [versioned v9.10 summary](../results/AGENT_SUMMARY_V9.10.md) retains the
quality-versus-cost plots, standalone PNG/SVG exports and metric data. The
plots were generated from explicitly selected manifests and resource samples.
The [current-results index](../results/AGENT_SUMMARY.md) links to the latest
complete comparison.

- Household quality versus full-suite wall time: higher success and lower time
  are favorable. Time includes startup/native admission and both tracks,
  excluding the separate 30-second baseline. No dollar pricing is invented.
- Household quality versus peak increase in host wired memory above the median
  baseline. Derive bytes from recorded VM page size and wired pages. This is a
  system-wide partial memory metric, not exact model attribution or total RAM.
  Process RSS/footprint omit GPU accounting; never sum these with allocator or
  host counters. Report model weight storage separately.
- Separate household and Python quality panels; no fabricated intelligence
  index or weighted composite. Show each seed and the observed two-run range,
  not a confidence interval or only the best score.

Use model color and explicit engine labels/marker shapes: **Mei (Swift/MLX)**
versus **llama.cpp (GGUF)**. Include run IDs, native sampler differences, context,
quant/source pins, failed/partial coverage and resource caveats beside charts.
No point is plotted as a completed score for an interrupted/unadmitted run.

### Short- and long-context decode speed

The next summary will add one row per model with two averaged TPS endpoints,
joined by a line: a filled marker for short context and an open marker for long
context. Label both with actual input-token counts. The connector pairs two
observations; it does not predict intermediate speeds. Keep task duration and
the separate household/Python success tracks alongside this view.

Use two predeclared fresh processes per profile and retain every measured
repeat, weighting the processes equally. Match model/runtime pins and the
controlled prompt, output allowance and sampler across the comparison. Exclude
cold/warmup observations from the endpoints, retain them as evidence, and reject
incomplete or mixed-revision input. The aggregation and PNG/SVG renderer live in
`runner/context_speed_summary.py`.

Task-log `tokens_per_second` divides completion tokens by full task wall time;
it includes prefill and tool overhead and is not decode TPS. The current v9.10
response traces retain engine decode timings, but Qwen has no matched long
context: its largest request is about 4.3K tokens. Those traces cannot supply a
controlled 30K comparison. Obtain matched observations for all four profiles,
including Logics/llama.cpp, on the runtime used for the fresh task cohort.

The Logics collector is `runner/qualify_llama_context.py`, with two declared
profiles in `configs/mei-stable-qualification-20261102/logics-context-{1,2}.yaml`
and [the exact selection](../artifacts/mei-stable-qualification-20261102/logics-context-screen.json).
It reuses the owned resource supervisor, verifies the pinned GGUF/runtime before
and after serving, tokenizes natively, requests uncached greedy raw completions,
and rejects partial, cached, truncated or wrong-length evidence. Each process
must complete five measured decodes per context after cold requests/warmups.
These declarations are preparation, not completed measurements. Keep each
engine's native decode timing convention explicit; llama.cpp may exclude its
first sampled token from the measured decode numerator. Do not replace its rate
with output tokens divided by full request wall time.

A clearly marked [qualification layout preview](../artifacts/mei-stable-qualification-20261102/context-speed-layout-preview.png)
uses actual unreleased candidate-only Mei measurements at 17/30,000 input
tokens. It excludes Logics and carries no task score or stable-release claim.
Its [raw observations and averages](../artifacts/mei-stable-qualification-20261102/context-speed-layout-preview.json)
and [performance review](../artifacts/mei-stable-qualification-20261102/default-performance-review.md)
remain separate from the published four-model summary. The final comparison
must not mix these qualification numbers with published rc.2 task results.
To reproduce the layout without overwriting its evidence, run
`uv run --locked python artifacts/mei-stable-qualification-20261102/preview_context_speed.py --output /tmp/mei-context-speed-preview`
with a fresh destination stem.

## Why v9.9 stopped after five attempts

Qwen seed29 correctly listed the persisted routing options and requested
“Please let me know which one you prefer.” The v9.9 grader lost the reference
to prior offered choices and falsely rejected it. Fix the indirect-request
checker with positive/negative regressions. Preserve all five original attempts,
then restart the full eight-run comparison on corrected v9.10. Do not regrade
or relabel their raw rows as new results. Runtime, prompts, tools, budgets,
sampling and resource policy are unchanged; only this held-out grader changes.

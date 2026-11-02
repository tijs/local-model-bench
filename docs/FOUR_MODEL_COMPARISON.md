# Four-model comparison — completed 2 November 2026

All four retained contenders completed two fresh full runs on frozen v9.10,
on the same 32 GiB Apple M1 Max. Both declared seeds remain visible. The
measurement code, profiles, budgets and resource policy stayed fixed throughout
these eight runs. [Main summary and graphs](../results/AGENT_SUMMARY.md).

| Profile / engine | Household, seeds 17 / 29 | Python, seeds 17 / 29 | Full-run time | Wired increase |
|---|---:|---:|---:|---:|
| Base Qwen3.6 / Mei (Swift/MLX) | 9/12 · 11/12 | 2/3 · 2/3 | 8.29–9.81 min | 19.91–20.08 GiB |
| Ornith1.5 / Mei (Swift/MLX) | 9/12 · 11/12 | 3/3 · 1/3 | 9.47–10.99 min | 19.98–20.07 GiB |
| Groot / Mei (Swift/MLX) | 11/12 · 10/12 | 3/3 · 3/3 | 10.23–10.40 min | 15.05–15.08 GiB |
| Logics-SWE / llama.cpp (GGUF) | 11/12 · 11/12 | 3/3 · 3/3 | 8.45–11.07 min | 19.53–19.54 GiB |

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

Quality is shown separately for household (/12) and Python (/3). Every seed is
plotted. Time is full-suite wall time, including startup/admission and both
tracks, excluding the separate 30-second baseline. One full run took 8.3–11.1
minutes; all eight together took about 79 minutes of measured run time, before
baselines, audits and publication.

Memory is peak recorded host wired bytes minus the median pre-run baseline,
using the recorded VM page size. It is system-wide partial accounting, affected
by background activity, not exact model RAM. RSS/physical footprint do not
reliably include GPU allocations. Weight storage is reported separately and no
counters are added together. The 512 MiB Mei prefix budget is resident state;
its generated disk tier was inventoried then removed after exit, with receipts.

PNG/SVG charts and JSON/CSV metrics are generated from the explicit cohort
selection by runner/build_four_model_summary.py. Circles mean Mei (Swift/MLX),
diamonds mean llama.cpp (GGUF); open/filled scatter markers distinguish seeds
17/29. Leader lines move only labels, never data points. Observed ranges are not
confidence intervals. Short tasks do not establish near-64K quality or capacity.

## Predeclared design and original interruption

The design below was recorded before execution. Its future-tense instructions
are retained as provenance; all eight corrected runs are now complete.

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

The current comparison will live in `results/AGENT_SUMMARY.md`, linked from the
README. The README will also embed both quality-versus-cost plots. Preserve
the former v8.3.1 summary separately. Export standalone PNG/SVG
charts and the underlying metric table/data, generated reproducibly from the
explicit selected manifests and resource samples.

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

## Why v9.9 stopped after five attempts

Qwen seed29 correctly listed the persisted routing options and requested
“Please let me know which one you prefer.” The v9.9 grader lost the reference
to prior offered choices and falsely rejected it. Fix the indirect-request
checker with positive/negative regressions. Preserve all five original attempts,
then restart the full eight-run comparison on corrected v9.10. Do not regrade
or relabel their raw rows as new results. Runtime, prompts, tools, budgets,
sampling and resource policy are unchanged; only this held-out grader changes.

# Four retained contenders: fresh comparison

By user direction, retain **base Qwen3.6, Ornith1.5, Groot and Logics-SWE**.
The earlier two-model replacement decision was too strong. Run all four fresh
on one frozen release, benchmark-v9.9, with seeds 17 and 29 per profile. Do not
reuse the older Groot/Logics outcomes as this comparison's measurements.

Order: Qwen17, Ornith17, Groot17, Logics17, then Qwen29, Ornith29, Groot29,
Logics29. All eight committed profiles are in `configs/four-model-20261102/`;
outputs are `artifacts/<model>-four-v9p9-seed<seed>-20261102`. Every run covers
all 12 household workflows and all 3 isolated Python tasks. Retain every outcome;
review/publish an attempt before the next load. Keep one model server at a time.

Qwen, Ornith and Groot use the same exact distributed Mei rc.2 binary/Metal and
vmlx pin. Logics uses its pinned llama.cpp binary/libraries. Preserve the
previous measured per-model settings: Qwen/Ornith T0.6,p.95,k20/native-default
thinking; Groot/Logics T1,p.95,k20/presence1.5. Other omissions/defaults remain
explicit in configs. Seeds are declared controls, not deterministic/independent
sample guarantees. This compares serving profiles, not isolated model weights.

Commit/release configs and reporting code before the first run. The measurement
code, graders, budgets, containment and stop rules stay frozen through all eight
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

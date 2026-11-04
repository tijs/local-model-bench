# Mei 0.10.0 comparison

Eight predeclared held-out runs: Qwen, Ornith, Groot and Logics, each with
seeds 17 and 29, covering twelve synthetic household tasks and three isolated
Python automation tasks. Benchmark measurement and grading inputs are unchanged
from `benchmark-v9.11.5` (commit `7d70334d`); later repository commits add
qualification evidence and these profiles. Results are separate from prior
cohorts and do not establish real Peixinho application acceptance.

Mei profiles pin the published 0.10.0 executable, Metal library and source
commit, with vmlx `9db62ce`. Qwen uses the qualified 512 MiB allocator limit;
Ornith uses its admitted prefill size of 32 and 6 GiB host reserve; Groot uses
its qualified profile. These settings are recorded in each YAML and are not a
pure runtime ablation against older results. Logics uses its pinned llama.cpp
and GGUF profile. Each run has an isolated runtime directory, normal-pressure,
swap and disk guards. Record and review every partial or failed attempt before
starting another model. Two seeds are repeated trajectories, not a confidence
interval.

The schedule and exact configuration paths are in
[mei010-campaign-matrix.json](../../artifacts/mei-stable-qualification-20261102/mei010-campaign-matrix.json).
Run through `runner/run_bench.py` with one model at a time after committing the
configuration. Raw results are append-only; preserve transcripts and owned
runtime receipts, verify model hashes and clean only benchmark-owned caches.

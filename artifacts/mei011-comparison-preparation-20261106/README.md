# Mei 0.11.0 benchmark campaign

The [campaign declaration](campaign.json) fixes eight held-out runs: Qwen,
Ornith, Groot and Logics-SWE with seeds 17 and 29. Each run uses the same
released `benchmark-v9.11.5` method as the [Mei 0.10.0 comparison](../../results/FOUR_MODEL_MEI010_FINAL.md):
12 household workflows and three Python automation tasks. The Mei profiles
use the [published and verified 0.11.0 release](verified-release-delivery.json).
Logics-SWE keeps the same pinned GGUF, llama.cpp revision and launch settings.

The [committed configs](../../configs/mei-0.11.0-comparison-20261107/) preserve
model-card sampling and use 512 MiB allocator pools for Qwen and Groot and
128 MiB for Ornith. Only Groot changes from its prior scored pool of 128 MiB.
The comparison measures serving profiles; it cannot isolate Mei source changes
for Groot, and Logics provides a control for variation between run windows.

The independent [delivery verifier](verify_release_delivery.py) downloaded the
published assets again and checked the tag, archive, Homebrew checksum and
installed executable and Metal library against the qualified build. The
[scored supervisor](run_scored_cohort.py) checks the committed config and
receipt against the released benchmark method. It runs one model at a time,
retains the evidence and replays each task audit before starting the next run.
The live campaign must be reviewed before any continuation; do not restart it
or substitute earlier results for an interrupted attempt.

The [initial Qwen seed 17 attempt](../mei011-qwen-seed17-20261107/README.md)
stopped below the 10 GiB disk floor. The retry uses a fresh owned runtime and
output path; all benchmark parameters are identical. The campaign checks for
23 GiB of headroom before starting each run, based on complete historical runs
leaving up to 7.7 GiB of temporary KV files. The 10 GiB supervisor stop remains
in place. The original progress file and append-only task rows are retained.

The model stores moved to Expansion before the retry. Frozen
configs keep their recorded paths through the store-level aliases. Any change
in full-run time can include model loading and, for GGUF, file-backed reads
from a different device. Prior controlled speed timings precede that storage
change; task outcomes and decode timing should be read separately.
Before starting the retry, run the [migration verifier](verify_model_store_migration.py)
with `--write` and commit its receipt. It binds the verified transfer to the
pinned checkpoint files. The scored runner rechecks that receipt and the
mounted volume before it starts the cohort.

The [first Expansion retry](../mei011-qwen-seed17-disk-retry-20261107/README.md)
stopped at the kernel's memory warning guard during model load, before any
tasks. The next continuation requires a complete residency-on native check on
Expansion before any scoring. It keeps the original serving settings and
reads and verifies the checkpoint before each timed run. The readback can
warm the OS file cache; its time is reported separately and is outside the
scored method. Full-run times are not cold-storage startup comparisons.

## Context-speed evidence

The [final release timing audit](../mei-upstream-qualification-20261106/attention-selector-final-review-20261107.json)
and [Logics control audit](logics-context-controls-review-20261107.json) feed
the [four-model speed specification](../../results/four-model-mei011-context-speed.json).
Each point averages five measured decodes per context in each of two fresh
processes. The short and long prompts are fixed across processes. This is
separate from the scored workflow runs. The
[preceding build's speed inputs](qualified-context-speed-inputs.json) remain
historical and do not qualify the published executable.

## Rebuild the comparison

After all eight runs are terminal and reviewed, run from the repository root:

```sh
uv run --locked python artifacts/mei011-comparison-preparation-20261106/assemble_scored_cohort.py --write
uv run --locked python runner/verify_combined_cohorts.py \
  --scores results/four-model-mei011-comparison.json \
  --speed results/four-model-mei011-context-speed.json
uv run --locked python runner/build_four_model_summary.py \
  --spec results/four-model-mei011-comparison.json \
  --summary results/FOUR_MODEL_MEI011_FINAL.md \
  --figures results/charts/four-model-mei011
uv run --locked python runner/build_context_speed_cohort.py \
  --spec results/four-model-mei011-context-speed.json \
  --output results/charts/four-model-mei011-context-speed
uv run --locked python artifacts/mei011-comparison-preparation-20261106/compare_scored_releases.py
```

The assembler refuses partial cohorts and checks every selected run against
its archived outcome, config and review. The combined verifier binds the two
reports to matching runtime, model and serving settings. Keep earlier graphs
and their source data intact; `AGENT_SUMMARY.md` is the current-results entry
point. The release delta compares distinct matched-seed cohorts and refuses to
reuse the same task rows. Kiem tracks remaining campaign and release work.

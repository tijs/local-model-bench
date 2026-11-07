# Documentation

Start with the [project overview and current scores](../README.md). The current
comparison covers twelve synthetic household tasks and three isolated Python
automation tasks. Peixinho is still a design; these are not application tests.

## Current comparison

[Four-model results](../results/AGENT_SUMMARY.md) links to the latest complete
comparison, including quality, time and memory graphs with one averaged point
per profile, plus individual observations and audit links.

## Earlier results and decisions

- [Retained roster](ROSTER.md): four retained serving profiles, alternatives,
  experimental diffusion, failures and limits.
- [Campaign completion audit](../artifacts/candidate-system-campaign-20261101/final-review-20261102/README.md):
  requirement-by-requirement evidence, released artifacts and separate open work.
- [Six-model v9.5 reference comparison](../results/AGENT_V9.md): selected complete runs,
  exact identities, coverage, time, resource observations and failed checks.
- [Clover v9.7 result](../results/CLOVER_V9.7.md): fresh corrected-method trial,
  8/12 household and 2/3 Python, with [failure review](../artifacts/clover-heldout-v9p7-20261102/README.md).
  Its original v9.6 score remains separate.
- [Reference run selection](../results/agent-v9-20261101.json): machine-readable
  input to the comparison generator. Runs are selected explicitly, not by newest
  timestamp or best score.
- [Finalist repeat design](FINALIST_REPEATS.md): fixed released binaries,
  predeclared seeds and fresh process/cache boundaries.
  [First seed 17 cohort](../results/FINALISTS_V9.8_SEED17.md): Groot and Logics-SWE
  each 11/12+3/3.
  [Seed 29 cohort](../results/FINALISTS_V9.8_SEED29.md): Groot 10/12+3/3;
  Logics-SWE 11/12+3/3. All four declared trials are complete.
- [Candidate campaign](CANDIDATE_CAMPAIGN.md): Groot, ThinkingCap, Logics-SWE,
  Clover and reference retests, with evidence links and open qualification work.
- [Release history](releases/): method and tooling changes. Current release:
  [benchmark-v9.11.9](https://github.com/tijs/local-model-bench/releases/tag/benchmark-v9.11.9);
  the current scored comparison uses the frozen benchmark-v9.11.5 method.

## Running and understanding the benchmark

- [Household workflows](PEIXINHO_STANDIN.md): synthetic state, tools and grading.
- [Python automation](PYTHON_AUTOMATION.md): script tasks, unseen inputs,
  containment and budgets.
- [Resource admission](RESOURCE_ADMISSION.md): capacity estimates, pressure,
  swap and disk stop rules. Free-memory percentage is telemetry.
- [Pinned Clover serving profile](KAPITSA_RUNTIME.md): full-suite lifecycle,
  runtime attribution, sampling and source-patch limits.
- [Clover native diffusion](CLOVER_NATIVE.md): pinned Kapitsa/Metal, automatic
  tools and dependent continuation, separate from scored runs.
- [Native Mei acceptance](MEI_NATIVE_ACCEPTANCE.md): guarded release checks,
  independent of scored household and Python runs.
- [Configurations](../configs/README.md): serving profiles and provenance.

Use the locked Astral environment and commit the exact config before execution.
Start with the supervised command in the [README](../README.md#reproduce-a-run); use fresh
output and owned cache directories. Preserve failed attempts before retrying.

## Historical evidence

- [Four-model v9.10 comparison and graphs](../results/AGENT_SUMMARY_V9.10.md).
- [Previous v8 candidate comparison](../results/CANDIDATES.md).
- [Earlier four-model summary](../results/AGENT_SUMMARY_V8.3.1.md), including Flint's
  retirement and the original MiniCPM, Qwen and Ornith trials.
- [Model-only report](../results/MODEL_ONLY.md): neutral simulated-tool checks,
  separate from household and script execution.
- [Historical application leaderboard](../results/LEADERBOARD.md) and
  [archived Hermes instructions](legacy/HERMES_README.md). Hermes is retired;
  the archived commands are not current run instructions.

Old rows retain their measured method and runtime identities. A native check,
kernel test, interrupted attempt or successful build is not a full task score.
Plans, decisions and open todos live in Kiem project `proj/local_model_bench`.

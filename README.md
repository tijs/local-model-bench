# local-model-bench

Current release: **benchmark-v8.3 — MiniCPM CPU-expert profile**.
See [v8.3 release notes](docs/releases/benchmark-v8.3.md),
[v8.2 release notes](docs/releases/benchmark-v8.2.md),
[v8.1 release notes](docs/releases/benchmark-v8.1.md),
[v8 release notes](docs/releases/benchmark-v8.md),
[MiniCPM probe release notes](docs/releases/benchmark-v7.2.1.md),
[resource admission release notes](docs/releases/benchmark-v7.2.md),
[report patch notes](docs/releases/benchmark-v7.1.1.md), the
[transport patch](docs/releases/benchmark-v7.1.md), and the
[v7 methodology](docs/releases/benchmark-v7.md). Historical v6 results retain
their original method identities and are not directly comparable with v7.

Compare local LLM serving stacks on affordable Apple Silicon Macs. The active
engines are llama.cpp variants and Mei (Swift/MLX). Peixinho is the intended
future application runtime; it is currently a design, so there are no Peixinho
application tests or product scores.

Hermes was retired on 2026-10-25. Its drivers, task definitions, transcripts and
results remain historical evidence. Current commands never reset its profiles,
launch it, or run its coding workloads. Do not reinstall or restore it.

## Primary track: synthetic Peixinho workflows

The `peixinho-standin-v1` scope adds twelve synthetic household workflow
contracts: capture, grounded retrieval/privacy, previewed sharing/private copies,
saved progress, routines and outage recovery. It uses bounded domain operations
and held-out state/journal validators. These are simulator/model evaluations,
not Peixinho app acceptance tests. See [the stand-in guide](docs/PEIXINHO_STANDIN.md)
for the explicit config profile, smoke/full coverage and separate result log/report.
Benchmark-v5 and its model-only results retain their original identities.

## Python automation track

The benchmark includes three real isolated Python CLI tasks: shopping CSV
normalization, decimal-safe expense aggregation, and reminder-export repair.
It uses a bounded write/run/repair loop and unseen post-agent inputs, with a
separate score/report. See [the automation guide](docs/PYTHON_AUTOMATION.md).
The **v8.3** comparison uses the unchanged v8.1 task method and is in progress: Qwen3.6 completed
**10/12 household + 3/3 Python** in7m06s; Ornith1.5 completed **9/12 + 2/3** in10m09s.
Both selected task runs stayed at normal pressure without swap growth. Flint
failed native admission and remains unranked; MiniCPM is pending. See the
[coverage-aware comparison](results/AGENT_LEADERBOARD.md) and
[campaign selection](results/agent-v8p3-20261101.json). These are one-trajectory,
profile-specific results, not statistical superiority or real-app acceptance.
MiniCPM will use q8_0 K/V, ubatch64 and first8 expert layers on CPU after both all-GPU profiles stopped for measured warning pressure;
its Q4_K_M weights and65536context remain. Near64K capacity is a separate experiment and is not implied by a task score.

The v8.1 correction stops counting an ordinary check for an absent advertised
starter file as an invalid tool call; old grades remain unchanged. Historical
v7/v7.1 results and partial/resource-interrupted attempts retain their own method
identities in the [campaign evidence](artifacts/automation-benchmark-20261029/README.md).
Use the documented supervisor and a fresh owned server/cache for each profile.

## Secondary track: model-only v1

- `sanity`: arithmetic and a minimal native tool call.
- `model_tools`: eight neutral tool-selection, chaining, targeted-edit,
  noisy-result and error-reporting cases with six mocked tools.

The tools are simulations: no shell command, search, file edit or application
operation requested by the model is actually executed. The neutral prompt and
small manifest are independent of any application runtime. They replace the
retired large-prompt workload for current model evaluation, with a new suite
identity and explicit `benchmark_scope: model-only-v1` result metadata.

These checks measure model/API behavior. They do not establish real coding,
application safety, Peixinho suitability, or a historical composite ranking.
Mocked tool calls do not test writing and executing Python automation scripts.

## Run

Use the Astral toolchain and locked environment.
Run `uv sync --locked` to install all project dependencies.
`runner/requirements.txt` is a legacy dependency mirror, not the setup entry point:

```bash
uv sync --locked
uv run --locked python -m unittest discover -s runner/tests -v
uv run --locked python runner/run_bench.py --config configs/runtime-attribution-fixturefix-20261029/qwen-full.yaml --trials 1
```

Commit the exact config before starting. Run one model server at a time under
the normal disk gate, preserve source/artifact identities and monitor host
memory pressure and swap. Stop owned servers after completion. CoCore remains
off and is never restored automatically.

Stand-in rows append to `results/standin/log.jsonl`; the generated report is
[results/STANDIN.md](results/STANDIN.md). Raw prompts/responses, state/journal
evidence and immutable config snapshots are retained by the runner.

The secondary `model-only-v1` scope appends to `results/log.jsonl` and generates
[results/MODEL_ONLY.md](results/MODEL_ONLY.md). Each track keeps configuration,
runner, suite and sampling-profile identities separate, with no composite score.

Historical application results stay in [results/LEADERBOARD.md](results/LEADERBOARD.md)
and its charts. The historical report generators exclude model-only rows.
Legacy runtime instructions are archived in [docs/legacy/HERMES_README.md](docs/legacy/HERMES_README.md);
the old orchestration is preserved in `runner/legacy_run_bench.py` for historical
regression tests and is not an executable current benchmark path.

Project state and execution plans live in Kiem (`proj/local_model_bench`); see
[AGENTS.md](AGENTS.md). Preserve append-only results and provenance. Use `uv`,
`ruff` and `ty` for Python work.

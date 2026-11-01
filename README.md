# local-model-bench

Current release: **benchmark-v9.1 — bounded MiniCPM runtime memory profile**.
See the [current release notes](docs/releases/benchmark-v9.1.md) and
[release history](docs/releases/).

Compare local LLM serving stacks on affordable Apple Silicon Macs. The active
engines are llama.cpp variants and Mei (Swift/MLX). Peixinho is the intended
future application runtime; it is currently a design, so there are no Peixinho
application tests or product scores.

## Current v9 results

| Model / serving profile | Household | Python | Full-run time |
|---|---:|---:|---:|
| ThinkingCap Q4_K_M, two checkpoints | 11/12 | 3/3 | 8m 47s |
| MiniCPM Q4_K_M, CPU8, q8 KV, no repacking, two checkpoints | 11/12 | 3/3 | 9m 38s |
| Qwen3.6 4-bit MLX / Mei | 7/12 | 3/3 | 13m 22s |

All three completed with normal pressure throughout and no swap growth. All
grades and tool journals matched on audit; every submitted script passed
independent replay on four fixture variants. ThinkingCap omitted a required
record citation. MiniCPM reused operation IDs for different retry arguments.
Qwen made invalid calls and repeated a deleted code; see the detailed reviews.

See the [v9 comparison](results/AGENT_V9.md) for exact run IDs and profiles.
Ornith and Groot v9 retests are pending. Earlier results below remain
historical references; they are not relabeled v9 scores. The new MiniCPM runtime
profile is a memory/speed tradeoff, not a controlled model-quality comparison.

## Previous completed results (v8 method)

One held-out trial per task on the v8.1-equivalent task method. Times include
startup and native admission, excluding the 30-second host baseline.

| Model | Household workflows | Python automation | Full-run time |
|---|---:|---:|---:|
| MiniCPM-V4.7 Q4_K_M | 12/12 | 2/3 | 5m 30s |
| Groot 19B/A3B, 4.5 bpw MLX | 11/12 | 3/3 | 9m 39s |
| Qwen3.6 35B/A3B, 4-bit MLX | 10/12 | 3/3 | 7m 06s |
| Ornith1.5 35B/A3B, 4-bit MLX | 9/12 | 2/3 | 10m 09s |

See the [verified comparison and exact run IDs](results/CANDIDATES.md).
MiniCPM uses q8 K/V with the first eight expert layers on CPU; the other models
use Mei. These compare complete serving profiles, rather than isolating model
or quantization quality. Independent repeats remain pending.

The [candidate campaign](docs/CANDIDATE_CAMPAIGN.md) is testing Groot,
ThinkingCap, Logics-SWE and Clover. Groot is provisional. ThinkingCap's first
attempt stopped for memory pressure; its bounded-checkpoint retry completed on v9. Logics-SWE and Clover
have not run. The v9 routing-validator correction requires fresh comparisons;
existing grades remain historical and will not be rewritten.

The active roster is **MiniCPM, Groot (provisional), Qwen3.6 and Ornith1.5**.
Flint, including JANGH2, was retired from consideration by user decision on
2026-11-01 after the completed comparison. Its configs, transcripts and results
remain historical evidence; further Flint runs or quant research require an
explicit decision to reconsider it. See the [comparison summary](results/AGENT_SUMMARY.md).

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
The **v8.3.1** comparison uses the unchanged v8.1 task method and is complete with Flint not admitted: Qwen3.6 completed
**10/12 household + 3/3 Python** in7m06s; Ornith1.5 completed **9/12 + 2/3** in10m09s.
Both selected task runs stayed at normal pressure without swap growth. Flint
failed native admission and remains unranked. MiniCPM completed **12/12 + 2/3**
in5m30s with one isolated startup warning and862MiB swap growth, then flat. See the
[coverage-aware comparison](results/AGENT_LEADERBOARD.md), [four-model summary](results/AGENT_SUMMARY.md) and
[campaign selection](results/agent-v8p3p1-20261101.json). These are one-trajectory,
profile-specific results, not statistical superiority or real-app acceptance.
MiniCPM uses q8_0 K/V, ubatch64 and first8 expert layers on CPU after both all-GPU profiles stopped for measured warning pressure;
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

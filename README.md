# local-model-bench

Current release: **benchmark-v9.3 — guarded native Mei acceptance**.
See the [current release notes](docs/releases/benchmark-v9.3.md) and
[release history](docs/releases/).

Compare local LLM serving stacks on affordable Apple Silicon Macs. The active
engines are llama.cpp variants and Mei (Swift/MLX). Peixinho is the intended
future application runtime; it is currently a design, so there are no Peixinho
application tests or product scores.

## Current v9 results

| Model / serving profile | Household | Python | Full-run time |
|---|---:|---:|---:|
| Logics-SWE IQ4_XS / llama.cpp | 12/12 | 3/3 | 8m 37s |
| Groot 19B/A3B, 4.5 bpw MLX / Mei | 12/12 | 3/3 | 11m 05s |
| ThinkingCap Q4_K_M, two checkpoints | 11/12 | 3/3 | 8m 47s |
| MiniCPM Q4_K_M, CPU8, q8 KV, no repacking, two checkpoints | 11/12 | 3/3 | 9m 38s |
| Ornith1.5 4-bit MLX / Mei | 9/12 | 2/3 | 11m 10s |
| Qwen3.6 4-bit MLX / Mei | 7/12 | 3/3 | 13m 22s |

All six completed with normal pressure throughout and no swap growth. All
grades and tool journals matched on audit; every submitted script passed
independent replay on four fixture variants. ThinkingCap omitted a required
record citation. MiniCPM reused operation IDs for different retry arguments.
Qwen made invalid calls and repeated a deleted code. Ornith used an unassigned
operation ID, repeated a deleted code and scheduled the wrong weekdays; its
reminder script worked after an invalid tool call. See the detailed reviews.

See the [v9 comparison](results/AGENT_V9.md) for exact run IDs and profiles.
The selected reference retests are complete. Earlier results below remain
historical references; they are not relabeled v9 scores. The new MiniCPM runtime
profile is a memory/speed tradeoff, not a controlled model-quality comparison.

## What the benchmark tests

The primary track has twelve synthetic household workflows: capture, grounded
retrieval and privacy, previewed sharing, saved progress, routines and recovery.
Models use bounded domain tools; held-out checks inspect the final state and
operation journal. See the [household workflow guide](docs/PEIXINHO_STANDIN.md).

The Python track has three real script-writing tasks: shopping CSV normalization,
decimal-safe expense aggregation and reminder-export repair. Models can read a
synthetic fixture, write `solution.py`, run it and repair it. Final grading uses
four inputs in OS containment, including unseen variants. Invalid calls still
count even if the eventual script works. See the
[Python automation guide](docs/PYTHON_AUTOMATION.md).

Full-run times above include startup/build wait, native admission and both task
tracks, excluding the 30-second host baseline. They compare complete serving
profiles. One trajectory per task does not establish statistical superiority;
task success also does not establish near-64K capacity or actual app acceptance.

## Work in progress

Groot and Logics-SWE are provisional contenders after passing all 15 current
tasks. Independent repeats and the remaining candidate work precede final roster
selection. The [campaign review](docs/CANDIDATE_CAMPAIGN.md) records profiles,
failures, memory fixes and next steps.

- **Clover:** publisher files and diffusion kernel checks verified; native model
  tools and task evaluation pending. Its available MLX-format pack is consumed
  by Kapitsa, a native Metal engine. It is not yet a Mei/MLX runtime result.
- **Mei preview:** the prepared Groot text pack is
  [public](https://huggingface.co/Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly).
  The first rc.2 native qualification failed two direct tool probes at their
  256-token limit; cache and exact-context checks passed. The attempt is
  [preserved](artifacts/mei-rc2-native-groot-20261101/README.md).
  Packaging and preview release remain pending; stable Mei remains 0.9.0.

Flint, including JANGH2, was retired from the roster on 2026-11-01. Hermes was
retired as a runtime on 2026-10-25. Their configs, transcripts and results remain
historical evidence. Do not restore Hermes or run its legacy coding workloads.

## Find results and reproduce them

| Need | Start here |
|---|---|
| Latest six-model scores, exact runs and failures | [Current v9 comparison](results/AGENT_V9.md) |
| Model profiles, audits and remaining work | [Candidate campaign](docs/CANDIDATE_CAMPAIGN.md) |
| Machine-readable current run selection | [v9 selection](results/agent-v9-20261101.json) |
| Previous v8 scores and original provenance | [Historical comparison](results/CANDIDATES.md) |
| Memory admission and stop rules | [Resource guide](docs/RESOURCE_ADMISSION.md) |
| Native release qualification, separate from scores | [Mei acceptance guide](docs/MEI_NATIVE_ACCEPTANCE.md) |
| All guides and historical reports | [Documentation index](docs/README.md) |

Earlier MiniCPM (12/12 + 2/3), Qwen (10/12 + 3/3) and Ornith (9/12 + 2/3)
v8 results remain online with their original method identities. The latest
MiniCPM profile disables CPU repacking and caps recurrent checkpoints at two;
its 11/12 + 3/3 score is a new serving-profile trial. Neither older nor newer
scores are silently substituted or regraded.

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
uv run --locked python runner/supervise_bench.py \
  --config configs/capacity-v8-20261101/qwen.yaml \
  --output artifacts/qwen-fresh-example --trials 1
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

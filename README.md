# local-model-bench

Current release: **benchmark-v9.9 — fresh four-model comparison and charts**.
See the [current release notes](docs/releases/benchmark-v9.9.md) and
[release history](docs/releases/).

Compare local LLM serving stacks on affordable Apple Silicon Macs. The active
engines are llama.cpp variants, Mei (Swift/MLX), and a separately pinned
Kapitsa/Metal profile for Clover diffusion experiments. Peixinho is the intended
future application runtime; it is currently a design, so there are no Peixinho
application tests or product scores.

Retain **base Qwen3.6, Ornith1.5, Groot and Logics-SWE**. All four are being
retested fresh on one frozen version, with two predeclared seeds each; the old
two-model replacement decision was premature. Three use **Mei (Swift/MLX)**;
Logics-SWE uses **llama.cpp (GGUF)**. [Current summary and upcoming graphs](results/AGENT_SUMMARY.md) ·
[Eight-run design](docs/FOUR_MODEL_COMPARISON.md).

Fresh progress: Qwen seed17 **9/12 household + 2/3 Python**; Ornith seed17
**9/12 + 3/3**; Groot seed17 **11/12 + 3/3**. Five predeclared runs remain. All completed with normal
pressure and no swap growth; see the linked summary for audited traces.

No old result is used as a new retest. The final summary will plot quality
against full-run time and measured wired-memory increase, with each seed and
engine visible. The older comparisons below remain historical references.

## Earlier finalist repeats on v9.8 (historical)

| Serving profile | Request seed | Household | Python | Full-run time |
|---|---:|---:|---:|---:|
| Groot public text pack / distributed Mei rc.2 | 17 | 11/12 | 3/3 | 10m19s |
| Groot public text pack / same Mei rc.2 binary | 29 | 10/12 | 3/3 | 10m14s |
| Logics-SWE IQ4_XS / pinned llama.cpp | 17 | 11/12 | 3/3 | 11m34s |
| Logics-SWE IQ4_XS / same llama.cpp binary | 29 | 11/12 | 3/3 | 8m27s |

All completed repeats had normal pressure and no swap growth. Both Groot trials
repeated a deleted numeric value; seed 29 also made an unassigned routing call
before recovering. Logics seed 17 exhausted its turn budget after correctly
recovering retry state; seed 29 attempted a denied private read before refusing. All completed Python tasks passed four-variant replay.


[Seed 17 cohort](results/FINALISTS_V9.8_SEED17.md) ·
[Seed 29 cohort](results/FINALISTS_V9.8_SEED29.md) ·
[Repeat design and reviews](docs/FINALIST_REPEATS.md)

Every predeclared outcome stays visible. Different seeds do not establish
independence or superiority. All four trials are complete; the
[earlier roster review](docs/ROSTER.md) has been superseded by retaining all four.
These are full serving-profile results, not a pure model or quantization ablation.
The broader reference table below retains its earlier measured method.

## Published v9.5 reference results

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

See the [v9.5 six-model comparison](results/AGENT_V9.md) for exact run IDs and profiles.
These retain their measured source identities as the new backend is integrated.
Those selected reference retests are complete on v9.5; the fresh v9.9
comparison above supersedes the older pending-retest plan. Earlier results below remain
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

## Campaign disposition

All four declared v9.8 finalist trials are complete. Logics-SWE scored 11/12
household on both seeds; Groot scored 11/12 and 10/12. Both passed all Python
tasks, and neither passed every household task in these repeats. The current
table keeps every outcome and failure mode visible. The
[campaign review](docs/CANDIDATE_CAMPAIGN.md) records shared improvements and
comparison limits; [the retained roster](docs/ROSTER.md) records the decision.

- **Clover:** publisher files and diffusion kernel checks verified; native model
  automatic tools and dependent continuation
  [passed native diagnostics](artifacts/clover-native-diffusion-20261101/README.md).
  [Cache controls passed](artifacts/clover-cache-diffusion-actual-baseline-20261101/README.md)
  across seven fresh processes with normal pressure and no swap growth. Its
  [fresh v9.7 trial](artifacts/clover-heldout-v9p7-20261102/README.md) scored
  **8/12 household, 2/3 Python in 15m03s** with normal pressure and no swap
  growth. It did not pass the full benchmark and remains experimental. The
  [original v9.6 score](artifacts/clover-heldout-diffusion-full-20261102/README.md)
  stays intact, including its confirmed grader false negative. Kapitsa consumes
  the MLX-format pack through native Metal; this is not a Mei/MLX runtime result.
- **Mei preview:** the prepared Groot text pack is
  [public](https://huggingface.co/Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly).
  [Mei rc.2 is released](https://github.com/tijs/mei/releases/tag/v0.10.0-rc.2)
  through `brew install tijs/tap/mei-preview`. Full native qualification passed
  [13 checks](artifacts/mei-rc2-native-groot-tools1024-20261101/README.md), and
  the installed asset passed [11 smoke checks](artifacts/mei-rc2-installed-groot-smoke-20261101/README.md).
  The first failed attempt stays preserved. Stable Mei remains 0.9.0; stable
  promotion and loaded-status responsiveness remain open.

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

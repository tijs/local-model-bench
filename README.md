# local-model-bench

Reproducible local LLM benchmarks on affordable Apple Silicon Macs. Compare
agent task quality, full-run time, memory and tool reliability with **Mei
(Swift/MLX)** and **llama.cpp (GGUF)**. Peixinho is the intended future app;
it is still a design, so the current tests use synthetic household workflows
and real, contained Python automation.

Current release: **benchmark-v9.10.1** — complete four-model comparison and
quality-versus-cost graphs. [Release notes](docs/releases/benchmark-v9.10.1.md).
All eight measurements use frozen **benchmark-v9.10**; the patch release adds
reports and data without changing the measured tasks or runtime behavior.

## Four retained contenders

All four ran fresh twice on the same 32 GiB Apple M1 Max, using seeds 17 and 29.
Each run covers 12 household workflows and 3 Python tasks. No older result was
substituted and no best repeat was selected.

| Profile / engine | Household, seeds 17 / 29 | Python, seeds 17 / 29 | Full-run time | Wired increase |
|---|---:|---:|---:|---:|
| Base Qwen3.6 / Mei (Swift/MLX) | 9/12 · 11/12 | 2/3 · 2/3 | 8.29–9.81 min | 19.91–20.08 GiB |
| Ornith1.5 / Mei (Swift/MLX) | 9/12 · 11/12 | 3/3 · 1/3 | 9.47–10.99 min | 19.98–20.07 GiB |
| Groot / Mei (Swift/MLX) | 11/12 · 10/12 | 3/3 · 3/3 | 10.23–10.40 min | 15.05–15.08 GiB |
| Logics-SWE / llama.cpp (GGUF) | 11/12 · 11/12 | 3/3 · 3/3 | 8.45–11.07 min | 19.53–19.54 GiB |

Wired increase is the observed peak **host wired memory above its median
baseline**: partial, system-wide accounting, not exact model RAM. Background
activity can affect it. Time includes startup, admission and both task tracks;
the separate 30-second baseline is excluded.

[Full summary, exact observations and audit links](results/AGENT_SUMMARY.md) ·
[Interpretation and method](docs/FOUR_MODEL_COMPARISON.md) ·
[Active roster](docs/ROSTER.md)

![Household quality versus full-run time](results/charts/four-model-v9.10/quality-time.png)

![Household quality versus wired-memory increase](results/charts/four-model-v9.10/quality-memory.png)

Logics-SWE reached 11/12 household and 3/3 Python on both trajectories. Groot
used the least observed wired-memory increase and the smallest weight files,
with 10–11/12 household and 3/3 Python. Qwen and Ornith each reached 9–11/12
household; their Python results were 2/3 both runs and 3/3 then 1/3 respectively.
**All four remain contenders.** Two runs do not establish statistical superiority.
Samplers, quantization, model sizes and engines differ; these compare complete
serving profiles, rather than isolating model weights.

Every task attempt completed. All eight supervisors exited normally, all
pressure samples were normal, and swap did not grow. Task failures include
denied private reads, invalid operation IDs, stale-value reuse and exhausted
budgets. Containment holding does not erase an unsafe attempt. No model passed
every household task in these repeats; actual Peixinho acceptance remains open.

## What is tested

- **Household workflows:** capture, ambiguous routing, multipart recovery,
  grounded retrieval, privacy, previewed sharing, copying, saved progress,
  completion intent, routines, outage retry and untrusted content.
- **Python automation:** CSV normalization, decimal-safe expense aggregation and
  reminder-export repair. Models write and run actual scripts. Submitted scripts
  face four contained inputs, including unseen variants; invalid calls still count.
- **Serving behavior:** exact runtime/model identity, health, cache behavior,
  full-run timing and supervised capacity/pressure/swap/disk policy. Short-task
  success does not prove near-64K quality or maximum context capacity.

[Workflow contracts](docs/PEIXINHO_STANDIN.md) ·
[Python tasks and containment](docs/PYTHON_AUTOMATION.md) ·
[Configuration guide](configs/README.md) · [Documentation index](docs/README.md)

## Reproduce a run

Use the locked Astral environment. Commit a profile with fresh owned runtime,
cache and output paths before a rerun; the published profiles retain the exact
measured choices. Keep one model server at a time and review any partial run
before proceeding.

```sh
uv sync --locked
uv run --locked python -m unittest discover -s runner/tests -v
uv run --locked python runner/supervise_bench.py \
  --config configs/<fresh-committed-profile>.yaml \
  --output artifacts/<fresh-run-id> --trials 1
```

All three MLX profiles use the same distributed
[Mei v0.10.0-rc.2](https://github.com/tijs/mei/releases/tag/v0.10.0-rc.2)
executable and Metal library. Logics-SWE uses its pinned llama.cpp build.
[Exact comparison profiles](configs/four-model-v9p10-20261102/) bind model hashes,
sampling, context, cache, binaries and source revisions.

## Preserved evidence

ThinkingCap and MiniCPM remain alternatives with historical v9.5 evidence.
Clover remains experimental native Kapitsa/Metal diffusion, separate from Mei.
Flint/JANGH2 and the Hermes runtime are retired; their evidence remains intact.
Do not use automatic config discovery as an active-roster selector.

[Earlier six-model comparison](results/AGENT_V9.md) ·
[Earlier v9.8 repeats](docs/FINALIST_REPEATS.md) ·
[Original v9.9 attempts and grader finding](results/FOUR_MODEL_V9.9_INTERRUPTED.md) ·
[Archived v8.3.1 summary](results/AGENT_SUMMARY_V8.3.1.md) ·
[Release history](docs/releases/)

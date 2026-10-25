# Agent guide

<!-- kiem -->
This repo is Kiem project `proj/local_model_bench`. Use `kiem todos` and
`kiem notes` for project state, decisions, and follow-up work; do not turn this
file into a project log.

## Project

`local-model-bench` is a reproducible benchmark project for comparing local LLM
serving stacks, with Peixinho as the primary harness focus. It measures automated task
quality, speed, memory, cache behavior, and tool-use reliability across the
active local engines: llama.cpp variants serving GGUF models and Mei serving
Swift/MLX models.

Hermes was retired as a runtime by user decision on 2026-10-25. Preserve the
legacy Hermes-specific runner code, configurations, transcripts and results as
historical evidence; do not reinstall Hermes, recreate its profiles, restore its
services or run the legacy `hermes chat` fixture path. Peixinho integration and
current benchmark work are governed by the latest Kiem plans. This cleanup does
not claim that a replacement Peixinho driver is already implemented.

Each run uses an isolated copy of a small fixture project. The model sees the
task and normal tools; held-out checks in `checks/` are copied in only after the
agent finishes. The benchmark never reads or modifies a real project during a
fixture run. Results are append-only and are never hand-edited.

## Layout and tools

- `configs/` — pinned model/engine launch configurations and provenance.
- `tasks/` — task-suite definitions and timeouts.
- `fixtures/` — pristine projects copied into isolated runs.
- `checks/` — held-out grading checks and mutation tests.
- `runner/` — launch, health, unload, fixture, grading, metrics, and leaderboard
  scripts; harness tests live in `runner/tests/`.
- `results/log.jsonl` — raw task rows; `results/LEADERBOARD.md` — generated rollup.
- `docs/` and `configs/README.md` — benchmark and configuration documentation.

Use the locked environment:

```bash
uv sync --locked
uv run --locked python -m unittest discover -s runner/tests -v
uv run --locked python runner/run_bench.py --config configs/<model>/<engine>.yaml
```

A benchmark config must be committed before a run. Run one local model server at
a time, use the config's exact served-model identity, preserve the config
snapshot/transcripts, and review every partial or failed run before starting
another model. Keep generated build/runtime files and model weights out of git.

## Mei integration

Mei lives in `/Users/tijs/projects/mei` and is not part of this repository.
`runner/start_mei_server.sh` builds and launches it; `runner/stop_mei_server.sh`
stops it; `runner/run_mei_acceptance.py` and `runner/probe_mei.py` validate the
OpenAI-compatible endpoint. Mei configs declare the model directory, served ID,
port, context, sampling, cache, and build provenance.

## Backend unload rule

`runner/unload_all.sh` may free benchmark-owned ports, but it must not invoke,
mutate, boot, restart, or restore CoCore. CoCore remains off during the current
experiments. The legacy Hermes fallback and its restore script are retired;
do not recreate them. No benchmark run automatically restores local backends.

Do not publish GitHub activity or push changes without explicit permission.

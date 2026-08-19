# Agent guide

<!-- kiem -->
This repo is Kiem project `proj/local_model_bench`. Run `kiem todos` / `kiem notes` for project state, and record progress with `kiem note add` / `kiem todo check`.

## Project context

Benchmark harness for picking a local LLM to drive Hermes (Tijs's local agent
framework at `~/.hermes`) for agentic coding — light JS/TS, Rust, and Swift
work with a large system prompt and many tools. Compares candidate models on
quality, speed, and tool-use reliability, each across two backends: MLX (via
the `cocore` serving stack) and GGUF (via llama.cpp's `llama-server`).

**Project management lives in kiem, not in scratch files or markdown TODOs.**
Use `kiem todos` / `kiem notes` to see state, `kiem note add` to log
findings/decisions, `kiem todo add` / `kiem todo check` to track next steps.
This applies for the life of this project — pick this up automatically in any
new session that opens this repo.

## Methodology (standard agentic-coding-benchmark practice, kept minimal)

- **Automated pass/fail only** — every task is scored by a command exiting
  0/nonzero (build, test, lint), never by an LLM judge or manual eyeballing.
  Keeps scoring cheap, deterministic, and comparable across models including
  weak local judges.
- **Isolated environment per run, fully self-contained** — each suite's
  fixture is a small original project (inspired by, but not copied from, a
  real Tijs project — no real project is ever touched or read at run time)
  committed straight into this repo under `fixtures/`. A run copies it to a
  scratch dir and `git init`s a fresh baseline commit there, so the starting
  state is byte-identical every time and teardown is just deleting the
  directory. Anyone who clones this repo gets everything needed to run the
  benchmark with nothing external required.
- **Held-out grading tests, not agent-authored** — each task's pass/fail test
  lives in `checks/<suite>/<task-id>/`, outside the fixture the agent sees.
  The runner only copies it into the run dir *after* the agent finishes, then
  runs it. The agent is never shown the grading test and never asked to write
  its own — this is the same separation SWE-bench/HumanEval-style benchmarks
  use, and it keeps scoring meaningful (an agent can't special-case a test it
  never sees).
- **Everything held constant except model+backend** — same task prompts, same
  tool/capability set (hermes's full current set, not a curated subset — this
  is deliberately meant to stress-test large-prompt/many-tools behavior), same
  system scaffolding. Only the `custom:bench` provider in hermes's config
  changes between runs.
- **Graduated difficulty, small task count** — ~5 tasks per suite, easy→hard,
  not a large suite. Enough to see where a model breaks down without turning
  every run into an hours-long ordeal on local hardware.
- **Bounded per-task timeout** — a hung/looping model fails the task rather
  than stalling the run.
- **Single trial by default** — LLM agentic runs are stochastic, but repeated
  trials are expensive on local hardware. Default to one attempt per
  task/model/backend; only re-run a specific task if the result looks flaky
  (e.g. a plausible near-pass or a timeout that looks like noise), and note
  the re-run in the log rather than silently overwriting.
- **Raw logs + rollup kept separate** — `results/log.jsonl` is the append-only
  raw record (one row per task attempt); `results/LEADERBOARD.md` is a
  human-readable summary regenerated from it. Never hand-edit the log.
- **No decontamination step needed** — tasks are grounded in Tijs's own
  private repos, which no candidate model could have trained on.

## Layout

- `fixtures/<suite>/` — the pristine starting project, tracked in git,
  copied fresh + re-initialized as its own git repo per run
- `checks/<suite>/<task-id>/` — held-out grading test file(s), overlaid onto
  the run dir only after the agent finishes, never shown during the task
- `tasks/` — one YAML file per suite: task list with prompt, expected tools,
  and the automated pass/fail check command
- `runner/` — orchestration scripts (fixture reset/teardown, backend
  load/unload, hermes provider swap, per-task driver, metrics extraction)
- `results/` — `log.jsonl` (raw) + `LEADERBOARD.md` (rollup)

## Test suites

Each is an original mini-project sized for a single focused agent session,
inspired by the *type and complexity* of work in a real Tijs project — same
languages/tooling, invented code, no dependency on or connection to the real
repo at run time.

| suite | inspired by | languages | tooling |
|---|---|---|---|
| `kiem_mini` | `~/projects/kiem` (notes CLI + app) | Rust, Swift | cargo, swift test |
| `hearth_mini` | `~/projects/hearth-and-oar` (settlement sim game) | TypeScript | vitest |
| `kipclip_mini` | `~/projects/kipclip-appview` (atproto bookmark appview) | TypeScript (Deno) | deno test |

## Backends

- **MLX**: `cocore`'s existing stack — `vllm_mlx.server --model <candidate>`,
  OpenAI-compatible, port 8012.
- **GGUF**: llama.cpp's `llama-server` (not yet installed — `brew install
  llama.cpp`), OpenAI-compatible, port 8013. Multiple quant levels are tested
  per candidate model (not just one), each as a separate log row.
- Hermes routes to whichever is live via a dedicated `custom_providers: bench`
  entry in `~/.hermes/config.yaml`, toggled for the duration of a run and
  restored after. **Unloading/swapping backends is not yet validated live —
  do this supervised on the first real run before trusting it unattended.**

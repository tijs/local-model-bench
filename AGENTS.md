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
- **Isolated environment per run** — each suite run happens in a throwaway
  `git worktree` off the real project repo, torn down after. Nothing touches
  your actual working trees.
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

- `fixtures/` — seed state for each suite (or a pointer to the source repo +
  a base ref/commit to worktree from)
- `tasks/` — one YAML file per suite: task list with prompt, expected tools,
  and the automated pass/fail check
- `runner/` — orchestration scripts (backend load/unload, hermes provider
  swap, per-task driver, metrics extraction)
- `results/` — `log.jsonl` (raw) + `LEADERBOARD.md` (rollup)

## Test suites

| suite | source repo | languages |
|---|---|---|
| `kiem` | `~/projects/kiem` | Swift, Rust |
| `hearth_and_oar` | `~/projects/hearth-and-oar` | JavaScript |
| `kipclip_appview` | `~/projects/kipclip-appview` | TypeScript, atproto |

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

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
- **Three task types per suite, not a graduated list** — every suite has
  exactly one **feature** task (implement a new function against a given
  signature), one **debug** task (fix a real, unhinted bug in existing code —
  the prompt reads like a bug report), and one **test-writing** task (write
  tests for correct-but-under-tested existing code). Separating these
  isolates the signal — a combined task can't tell you whether a model
  failed to plan, to diagnose, or to test. 3 suites × 3 types = 9 tasks per
  model/backend, a small, legible grid rather than a loose graduated list.
  Test-writing tasks are graded by mutation kill rate, not exit code alone:
  the agent's tests must pass against the real implementation and fail
  against every pre-written buggy mutant swapped in one at a time
  (`runner/grade_mutation.sh`) — otherwise an empty test file would trivially
  "pass."
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
| `kipclip_mini` | `~/projects/kipclip-appview` (bookmark appview) | TypeScript (Deno) | deno test |

Each suite fully verified end to end: baseline builds/tests pass clean, every
`feature`/`debug` check fails correctly against baseline and was spot-checked
to pass against a correct fix, and every `test-writing` mutation check was
verified against both a real test file (passes, kills all mutants) and a
trivial one (correctly fails).

**Swift/Xcode note**: Xcode.app lives at `/Applications/Xcode.app` (moved
there from `~/Applications/Xcode.app`, which was a stray install location —
every other app on this machine is in the system-wide folder). The system
default toolchain is still Command Line Tools
(`xcode-select -p` unset via sudo would need Tijs's password to change) — so
Swift/Xcode commands in this project must set
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` explicitly, as the
`kiem_mini-debug` check command already does.

## Backends

- **MLX**: three layers. `vllm_mlx.server --model <candidate>` is the raw
  engine on port 8012 — no server-side tool-call parsing exists in vllm-mlx
  at all (confirmed: no `--tool-call-parser` flag in `vllm_mlx.server
  --help`, only `--reasoning-parser` for `<think>`-style extraction), so it
  returns tool calls as raw text in `content` (e.g. LFM's
  `<|tool_call_start|>[fn(a=1)]<|tool_call_end|>`), not a real `tool_calls`
  array. **The benchmark uses its own proxy for this — `runner/
  bench_local_proxy.py`, started via `runner/start_bench_proxy.sh`, listening
  on port 8015.** This is a fork of `~/.hermes/profiles/fitness/
  mara_local_proxy.py` (the "fitness" hermes profile's own proxy on port
  8013) with one critical difference: that file unconditionally filters
  every caller's `tools` array down to its own ~12-tool allowlist tuned for
  the fitness/Kiri profile. **Never point the benchmark at port 8013** — this
  was discovered live 2026-08-19 after it silently gave false-passing
  `hermes_ops` tool-selection results (the intended tool wasn't even in the
  manifest the model received, and since tool-call parsing is regex-based on
  raw text with no schema validation, the model can still "call" a tool name
  it was never given — which further masked the filtering). All prior
  `results/log.jsonl` rows from before this fix were cleared as invalid.
  `bench_local_proxy.py` is also **parser-pluggable per model family** — it
  registers named parsers (`lfm` confirmed working; `hermes_style` for
  Qwen-style `<tool_call>{...}</tool_call>` JSON blocks, added but not yet
  verified against a real Qwen response) selected via `BENCH_TOOL_PARSER`.
  Every new candidate model's `configs/<model>/mlx.yaml` must research and
  cite its actual raw tool-call format (from the model card/creator docs)
  and set `tool_call_parser:` accordingly — getting this wrong doesn't
  error, it silently produces zero or hallucinated tool calls.
- **GGUF**: llama.cpp's `llama-server` (not yet installed — `brew install
  llama.cpp`), OpenAI-compatible, port 8016 (8012-8015 reserved per above).
  Also TBD: whether `llama-server` returns a proper `tool_calls` array
  natively (its chat-template-driven tool calling is more standardized than
  vllm-mlx's), or still needs a `bench_local_proxy.py`-style shim per model
  family — check with `runner/run_prompt.py` and inspect raw `tool_calls`
  vs. content before trusting any GGUF tool-call results. Multiple quant
  levels are tested per candidate model (not just one), each as a separate
  log row.

## Reproducibility / pinned dependencies

- **Fixtures**: `Cargo.lock` (kiem_mini), `package-lock.json` (hearth_mini),
  `deno.lock` (kipclip_mini) are all tracked in git — a benchmark run should
  be byte-for-byte reproducible, not dependent on whatever happens to be
  latest on a registry that day.
- **Runner scripts** (Python): run with `/Users/tijs/.cocore/python/bin/
  python` (3.12.13) — the only local interpreter confirmed to have PyYAML
  pre-installed; version pinned in `runner/requirements.txt`
  (`pip install -r runner/requirements.txt` into any other interpreter if
  cocore's python ever goes away).
- **Every logged result** carries `config_path` + `config_hash` (a sha256
  prefix of the exact config file content at run time) — so even if a
  `configs/<model>/*.yaml` file is edited later, historical `results/
  log.jsonl` rows stay traceable to exactly what settings produced them.
- Hermes routes to whichever is live via a dedicated `custom_providers: bench`
  entry in `~/.hermes/config.yaml`, toggled for the duration of a run and
  restored after. **Unloading/swapping backends is not yet validated live —
  do this supervised on the first real run before trusting it unattended.**
- Hugging Face auth is configured for higher-rate model downloads (both this
  session and any hermes-spawned agent session): token in
  `~/.cache/huggingface/token` and `HF_TOKEN` exported in `~/.zshrc`.

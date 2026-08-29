# local-model-bench

A benchmark harness for picking the best local LLM to run as the inference
engine for [Hermes](https://hermes-agent.nousresearch.com/docs) (a local
agent framework) for agentic coding work — JS/TS, Rust, Swift, a large
system prompt, and a large tool manifest. Compares candidate models across
three axes: tool-use reliability, speed, and coding capability under
realistic agentic conditions, on a Mac Studio (M1 Max, 32GB unified
memory).

**GGUF/llama.cpp is the primary, proven engine; MLX is an open question
under active investigation, not a closed one.** vllm-mlx and isolated
oMLX were both compared against llama.cpp across many models and
consistently lost by a wide, structural margin. That finding was closed
out 2026-08-25 — but reopened 2026-08-28 after a specific lead pointed at
the MLX *serving layer* (not the underlying `mlx-lm` library) as the
likely cause, which reframes why a third, differently-implemented MLX
serving engine might behave very differently. See
[`docs/INFERENCE_ENGINES.md`](docs/INFERENCE_ENGINES.md) for the full,
current investigation. Until it resolves one way or the other,
GGUF/llama.cpp remains the safe default for new model additions and
speed/reliability work; the `mlx.yaml`/`omlx.yaml` configs and harness
support for both engines stay in the repo either way.

This harness (every runner script, config, task, and fix) was built and is
run by Claude (Anthropic) working autonomously in the terminal, directed
and reviewed by a human. Treat generated numbers/code accordingly, and see
[`AGENTS.md`](AGENTS.md) for the full history of what was found and fixed
along the way.

**Start here for the current pick**: [`results/SUMMARY.md`](results/SUMMARY.md)
is a hand-curated, human-written snapshot of the top candidates and why —
read this first if you just want an answer. [`results/LEADERBOARD.md`](results/LEADERBOARD.md)
is the full, auto-regenerated detail behind it (every config's numbers,
a "Best overall" gate-then-weighted-composite table, a "Blocked configs"
section for models ruled out outright, and a "Speed-gated configs" section
for models that didn't clear the minimum tokens/sec floor) — never
hand-edit that file, it's rebuilt from [`results/log.jsonl`](results/log.jsonl)
(append-only raw record, one row per task attempt) after every run.
Methodology-version boundaries are marked with annotated git tags
(`git tag -l -n1`) — see AGENTS.md's "Best overall" leaderboard section
for what each tag family means. Methodology and every non-obvious harness
gotcha are in [`AGENTS.md`](AGENTS.md) — read
that before touching the runner code. For research on the inference
engines themselves (bugs, version quirks, the MLX-vs-GGUF speed
investigation), see [`docs/INFERENCE_ENGINES.md`](docs/INFERENCE_ENGINES.md);
for oMLX's own per-model settings and provenance, see
[`docs/OMLX_MODEL_MATRIX.md`](docs/OMLX_MODEL_MATRIX.md).

**The speed gate**: a config whose `hermes_ops` run averages under
`bench_common.MIN_HERMES_OPS_TOKENS_PER_SECOND` (currently 4 tok/s — see
that constant's own comment for the full reasoning and history) skips the
far more expensive coding suite rather than spend hours confirming an
outcome the speed data already answered.

## Prerequisites

- **macOS on Apple Silicon.** MLX only runs there; GGUF/llama.cpp would
  work elsewhere but this repo's launch commands assume Metal.
- **[uv](https://docs.astral.sh/uv/)** for the Python orchestration scripts.
  Run `uv sync --locked` to install all project dependencies, including the
  vllm-mlx serving stack. uv is the sole workflow for every benchmark Python
  process: invoke runner and proxy scripts with `uv run --locked python ...`,
  and vllm-mlx serving with `uv run --locked ...`. Set
  `BENCH_HERMES_BIN=/path/to/hermes` only if your external Hermes install
  isn't at `~/.hermes/hermes-agent/venv/bin/hermes`.
- **`llama.cpp`** (`brew install llama.cpp`) for the `llama.cpp` inference
  engine — the primary one; only prerequisite most people need.
- **`vllm-mlx` 0.4.1 or newer** for the `vllm-mlx` inference engine, included
  in the locked project environment. See
  [`docs/INFERENCE_ENGINES.md`](docs/INFERENCE_ENGINES.md) for its
  tool-call-parser version history and a real streaming-mode bug to know
  about. Not required for GGUF-only work; relevant if you're extending the
  ongoing MLX investigation (see the note at the top of this file).
- **oMLX 0.6.2** for the isolated `omlx` inference engine. Bootstrap it with
  `runner/bootstrap_omlx.sh`; that script creates/manages the separate
  environment under `~/.local/share/local-model-bench/`, pins source commit
  `f2d36f3d25a7e7a2401a92eecafc28b8f8968ec7`, and never installs oMLX into
  the project `.venv`, `~/.omlx`, or the CoCore Python environment. See
  `runner/start_omlx_server.sh`. Same status as vllm-mlx above — not
  required for GGUF-only work.
- **[Hermes](https://hermes-agent.nousresearch.com/docs)** installed
  locally, with an isolated `bench` profile
  (`~/.hermes/profiles/bench/config.yaml`) — this is what the coding-suite
  tasks actually drive (via `hermes chat`), kept separate from any real
  daily-driver hermes profile so a benchmark run never touches real
  session/memory state. Each config's `orchestration.hermes_provider` must
  have a matching entry in that profile's `providers:` block.
- A HuggingFace token cached at `~/.cache/huggingface/token` (for gated
  model downloads).

## Running the benchmark

**Everything, one command:**
```
uv run --locked python runner/run_bench.py --all
```
Iterates every `configs/*/*.yaml`, one at a time (strict one-server-at-a-
time — see AGENTS.md's process-discipline note on why running multiple
model servers concurrently causes silent-looking failures that are
actually resource exhaustion). Skips anything marked `viable: blocked` in
its config, prints why, and moves on.

**One model:**
```
uv run --locked python runner/run_bench.py --config configs/Qwen3-Coder-30B-A3B/gguf.yaml
```

Either way, this launches the candidate server (and a tool-call-parsing
proxy in front of it, if the config needs one), runs the `sanity` suite as
a fail-fast gate, then `hermes_ops`, then every task in every coding suite
(`kiem_mini`, `hearth_mini`, `kipclip_mini` — see `--coding-suites` below
to run just the quick single-task spot-check instead) — skipping whichever
of those a config's `orchestration.viable` says isn't reachable for that
model (see the docstring at the top of `runner/run_bench.py` for exactly
what each `viable` value means). Regenerates `results/LEADERBOARD.md`
after every model, tears down the server, and moves to the next.

Run only the sequential isolated oMLX matrix (never concurrently):
```
uv run --locked python runner/run_bench.py --all --inference-engine omlx
```

**Optional flags** (either invocation form above):
- `--trials N` — run each task N times instead of once. A single trial's
  pass/fail is not reliably reproducible (confirmed live: the identical
  model/config/task flipped pass↔fail across two separate runs at
  temperature=0 — MLX/Metal generation isn't bit-deterministic run to run).
  `build_leaderboard.py` surfaces any task with a mixed pass/fail across
  its rows in a dedicated "Flaky tasks" section.
- `--coding-suites kiem_mini,hearth_mini,kipclip_mini` — run EVERY task
  (feature/debug/test-writing) in the named suites. This is now the
  **default** (as of 2026-08-25 — see AGENTS.md for why: "run all tests"/
  "full benchmark" kept getting asked for and getting the old quick
  single-task spot-check instead, a recurring miscommunication). Pass
  `--coding-suites none` for that old quick `kiem_mini-feature`-only
  behavior — much cheaper, useful for a fast sanity pass on a big/slow
  model where the full ~11-task battery would take hours.

**Config-driven, not hardcoded**: every port, launch flag, proxy
requirement, and hermes provider name lives in that model's
`configs/<model>/<name>.yaml` (the engine identity lives in that file's
`inference_engine:` field, not the filename), not in the runner code. See
[`configs/README.md`](configs/README.md) for the full schema.

## Adding a new candidate model

1. Copy the closest-matching existing `configs/<model-slug>/` directory as
   a starting point — GGUF and MLX are separate files
   (`configs/<model-slug>/gguf.yaml`, `.../mlx.yaml`, or `.../omlx.yaml`).
2. Research the model's actual recommended settings — model card, release
   blog post, any linked deployment guide — and update
   `benchmark_launch_command`, `settings:` (with real citations, not
   guesses), and the `orchestration:` block (`raw_port`, `needs_proxy`,
   `hermes_provider`, `viable`).
3. **Spot-check the raw tool-call format live** before trusting any
   result: hit the running server directly with a simple tool-call prompt
   and inspect the response. If it comes back as a proper `tool_calls`
   array, no proxy is needed (`needs_proxy: false`). If it comes back as
   raw text in `content` (or, seen once this session, in
   `reasoning_content` instead), you need a new parser in
   `runner/bench_local_proxy.py`'s `PARSERS` dict — see the existing
   `lfm`/`qwen3_coder`/`poolside_v1`/`hermes_style` parsers for the
   pattern, and AGENTS.md's Backends section for why this step matters
   (getting it wrong doesn't error, it silently produces 0 or hallucinated
   tool calls).
4. Register a provider for the model in
   `~/.hermes/profiles/bench/config.yaml` matching
   `orchestration.hermes_provider`, so the coding-suite spot-check can
   reach it via `hermes chat`.
5. If the model needs thinking/reasoning mode explicitly enabled to run as
   intended (check the model's own deployment docs, not just its sampling
   defaults — see AGENTS.md's standing note on this), set it via
   `--chat-template-kwargs`/`--default-chat-template-kwargs`, or via
   `system_prompt_suffix:` in the config if the mechanism is a system-
   prompt directive rather than a template kwarg (e.g. Muse-Glimmer's
   `"Reasoning strength: high"`). Record which value was used — it's not
   directly comparable across model families, so never leave it implicit.
6. Run it: `uv run --locked python runner/run_bench.py --config configs/<model>/<name>.yaml`.

**When a model underperforms expectations**, don't accept the result at
face value — do deeper research first (a dedicated deployment guide, a
minimum framework/build-version requirement, a required launch flag or
mode toggle). This surfaced real, fixable gaps twice this session
(Laguna-XS-2.1's thinking-mode default, Muse-Glimmer's reasoning-strength
directive) that looked like genuine capability gaps until checked. See
AGENTS.md for the full writeups.

## Special cases

- **DFlash2 speculative decoding** needs a from-source llama.cpp build
  (mainline/Homebrew doesn't have the real loader yet, only a CLI stub —
  see AGENTS.md's DFlash 2 section). Run `runner/setup_dflash2_fork.sh`
  once; it builds into the gitignored `runner/.dflash2-fork/`.
- **Luna** (`configs/Luna/api.yaml`) isn't a local model at all — it's
  reached through hermes's `openai-codex` OAuth provider (a hosted model,
  included as a comparison point with the user's explicit go-ahead, given
  the same category of concern that got Haiku excluded — see AGENTS.md).
  Only the coding spot-check runs for it; `sanity`/`hermes_ops` need a
  plain OpenAI-compatible endpoint this provider doesn't expose.
- **Laguna-XS-2.1 MLX** is currently blocked outright — `mlx-lm` (the
  library under `vllm-mlx`) doesn't recognize this model's architecture at
  all. GGUF-only until that changes.

## Repo layout

- `configs/<model-slug>/<name>.yaml` — one file per model+inference-engine,
  everything needed to reproduce a result (see `configs/README.md`).
- `tasks/*.yaml` — the suite definitions (`sanity`, `hermes_ops`,
  `kiem_mini`, `hearth_mini`, `kipclip_mini`); see `tasks/SCHEMA.md`.
- `fixtures/`, `checks/` — the coding-suite fixture projects and their
  held-out grading tests.
- `runner/` — every script; `run_bench.py` is the entry point, everything
  else is called by it (or directly, for debugging one suite at a time).
- `results/log.jsonl` / `results/LEADERBOARD.md` / `results/SUMMARY.md` —
  raw record / auto rollup / hand-curated snapshot.
- `docs/INFERENCE_ENGINES.md` — research on the inference engines
  themselves (bugs, version quirks, the MLX-vs-GGUF investigation).
  `docs/OMLX_MODEL_MATRIX.md` — oMLX's per-model settings and provenance.

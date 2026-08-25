# Agent guide

<!-- kiem -->
This repo is Kiem project `proj/local_model_bench`. Run `kiem todos` / `kiem notes` for project state, and record progress with `kiem note add` / `kiem todo check`.

## Project context

Benchmark harness for picking a local LLM to drive Hermes (Tijs's local agent
framework at `~/.hermes`) for agentic coding — light JS/TS, Rust, and Swift
work with a large system prompt and many tools. Compares candidate models on
quality, speed, and tool-use reliability, each across two inference engines: MLX (via
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
- **Everything held constant except model+inference-engine** — same task prompts, same
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
  model/engine, a small, legible grid rather than a loose graduated list.
  Test-writing tasks are graded by mutation kill rate, not exit code alone:
  the agent's tests must pass against the real implementation and fail
  against every pre-written buggy mutant swapped in one at a time
  (`runner/grade_mutation.sh`) — otherwise an empty test file would trivially
  "pass."
- **Bounded per-task timeout** — a hung/looping model fails the task rather
  than stalling the run. For the prompt suites this is FOUR separate,
  explicitly-declared budgets (per-turn total, per-task total, first-progress,
  stream-idle) rather than one number reused as three things — see
  "Timeout and liveness budgets" in `tasks/SCHEMA.md` for what each one bounds
  and for the 11-hour oMLX stall that made the distinction necessary. A row
  that times out records WHICH budget ran out (`timeout_phase`) and where its
  partial output was preserved (`partial_output_path`), and counts as a
  model/engine failure rather than a `harness_error`.
- **Single trial by default** — LLM agentic runs are stochastic, but repeated
  trials are expensive on local hardware. Default to one attempt per
  task/model/engine; only re-run a specific task if the result looks flaky
  (e.g. a plausible near-pass or a timeout that looks like noise), and note
  the re-run in the log rather than silently overwriting.
- **Raw logs + rollup kept separate** — `results/log.jsonl` is the append-only
  raw record (one row per task attempt); `results/LEADERBOARD.md` is a
  human-readable summary regenerated from it. Never hand-edit the log.
- **Full coding-suite transcripts are saved, not just the final grade
  output** — `results/transcripts/<suite>/<task_id>/<timestamp>_<model>.log`
  (referenced by each log row's `transcript_path`), committed like everything
  else. Added 2026-08-20 after discovering that no transcript had ever been
  saved anywhere all session, which made a genuinely-suspicious result
  (Luna failing a task it should have handled easily — see the stale-
  build-cache bug below) impossible to verify without a slow manual
  live rerun. Every result before this fix was judged on exit code + the
  final compile/test error only, never the agent's actual behavior — if a
  result looks surprising, read its transcript before trusting it.
- **No decontamination step needed** — tasks are grounded in Tijs's own
  private repos, which no candidate model could have trained on.
- **When a model doesn't work as expected, always do deeper research before
  accepting the result** — per Tijs (2026-08-20). "Doesn't work as expected"
  means: an unexpectedly poor/unstable result, a surprising failure mode, or
  anything that doesn't match what the model card's own claims would
  predict. Don't stop at the first plausible sampling-settings citation —
  check for a dedicated deployment guide, a minimum framework/build version
  requirement, a required launch flag, or a mode toggle (reasoning
  strength, thinking mode) that the model needs to run as intended. This is
  what surfaced Laguna-XS-2.1's `enable_thinking` default-off template
  behavior and Muse-Glimmer-30B's "Reasoning strength: <level>" system-
  prompt mechanism (both found only by searching beyond the first model-
  card settings table) — a result that looks like a genuine capability gap
  can actually be a missed setup step, and the only way to tell the two
  apart is to dig deeper before writing the result down as final.
- **Thinking/reasoning mode: always pick a reasonable setting per model, and
  always record which value was actually used** — per Tijs (2026-08-20): a
  single "thinking mode" setting isn't directly comparable across model
  families (some default on, some off, some have no toggle at all, the
  enabling mechanism differs — a `chat_template_kwargs` flag, a dedicated
  CLI flag, a system-prompt instruction), so don't try to force one global
  policy. Instead: (1) research and cite what the model's own card/docs
  recommend, matching the setting used in that model's own official
  benchmarks where stated; (2) write the exact value used as its own
  labeled `settings:` entry in `configs/<model>/*.yaml`, not buried in
  prose elsewhere; (3) if a model's default and its "recommended for
  benchmarking" value differ, use the latter and say so explicitly, since
  the default is not necessarily what the model card's own numbers
  reflect. Testing both a low and a high thinking-mode setting per model
  (Tijs's suggestion) is a reasonable deeper follow-up if there's time —
  not done as standard practice this session given the added run cost,
  but worth doing for any model whose thinking-mode setting is suspected
  of materially changing results.

## Layout

- `fixtures/<suite>/` — the pristine starting project, tracked in git,
  copied fresh + re-initialized as its own git repo per run
- `checks/<suite>/<task-id>/` — held-out grading test file(s), overlaid onto
  the run dir only after the agent finishes, never shown during the task
- `tasks/` — one YAML file per suite: task list with prompt, expected tools,
  and the automated pass/fail check command
- `runner/` — orchestration scripts (fixture reset/teardown, backend
  load/unload, hermes provider swap, per-task driver, metrics extraction)
- `runner/tests/` — automated regression tests for the harness itself
  (not the model-facing task suites below). Added 2026-08-21, after a
  third independent adversarial review found every one of its Critical/
  High findings by directly exercising a harness function against a
  synthetic input in minutes — something this repo had zero automated
  coverage for until then, despite two prior review rounds' worth of
  fixes. Run with:
  `uv run --locked python -m unittest discover -s runner/tests -v`
  Covers: grade_prompt.py's check-grading logic (strip_reasoning,
  normalize_punctuation, the error-recovery forbidden-phrase regex, the
  tool-call-argument combined-predicate fix), run_fixture_suite.py's
  restore_harness_files/grade_mutation guards, build_leaderboard.py's
  harness_error exclusion, bench_common.py's git_sha dirty-check paths,
  and a real (not mocked) smoke test of grade_mutation.sh's backup/
  restore correctness against kiem_mini's actual rust fixture. Extend
  this file, don't just fix-and-move-on, the next time a review finds a
  bug in harness code these tests touch.
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

**Caveat, corrected 2026-08-21 (3rd adversarial review, low finding):**
"passes against a correct fix" is necessary but not sufficient — a THIRD
independent adversarial review found two `feature` checks (hearth_mini's
storehouse-affordability check, kipclip_mini's tag-filter check) that also
passed against an INCORRECT fix (one ignoring `canAfford` for one resource,
one matching tags by substring instead of exact equality), because no test
case happened to distinguish correct from incorrect behavior on that
specific dimension. Both were strengthened and re-verified against a
deliberately-wrong implementation, not just a correct one. Spot-checking
only the correct-fix direction leaves this exact class of gap; a check is
only as strong as its weakest untested edge case, and "passes against
correct" proves nothing about whether it "fails against incorrect" unless
that's checked too.

**Swift/Xcode note**: Xcode.app lives at `/Applications/Xcode.app` (moved
there from `~/Applications/Xcode.app`, which was a stray install location —
every other app on this machine is in the system-wide folder). The system
default toolchain is still Command Line Tools
(`xcode-select -p` unset via sudo would need Tijs's password to change) — so
Swift/Xcode commands in this project must set
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` explicitly.

Corrected 2026-08-25 (improvement plan, low finding): this paragraph used
to end "…as the `kiem_mini-debug` check command already does", but that
check actually ran `DEVELOPER_DIR=$(xcode-select -p)` — i.e. it took
whatever the machine's *ambient* default happened to be, which is exactly
the Command Line Tools toolchain this note warns against. Both Swift
checks in `tasks/kiem_mini.yaml` now pin the path literally, with
`BENCH_DEVELOPER_DIR` as an override for a machine where Xcode lives
somewhere else. A Swift task graded against CLT `swift` and one graded
against Xcode `swift` are not the same task, and nothing in the log row
would have shown which one ran.

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

  **vllm-mlx version note, discovered live 2026-08-20**: the "no
  --tool-call-parser flag exists" statement above was true for the
  installed **0.4.0**, but is NOT a fundamental vllm-mlx limitation — it's
  a stale-dependency artifact. **0.4.1** (one patch version up, now
  installed in `~/.cocore/python` — upgraded live with Tijs's explicit
  go-ahead, since that's also his real daily-driver Python env, not a
  benchmark-isolated one) ships a real `vllm-mlx` CLI (`vllm-mlx serve
  <model> --enable-auto-tool-choice --tool-call-parser <name>`, a
  different, richer entry point than the bare `python -m vllm_mlx.server`
  module invocation used all session) with native parsers for `qwen`,
  `qwen3_coder` (exact match for the custom parser hand-written for
  Qwen3-Coder-30B this session), `mistral`, `llama`, `hermes`, `deepseek`,
  `harmony`/`gpt-oss`, `granite`, `nemotron`, `xlam`, `functionary`,
  `gemma4`, `glm47`, `minimax`, plus `auto` (tries all). There's also a
  `poolside_v1` parser registered internally (exact name match for
  Laguna-XS-2.1's undocumented tool-call format) — but it's missing from
  `vllm-mlx serve`'s hardcoded `--tool-call-parser` argparse `choices=`
  list (confirmed: `--tool-call-parser poolside_v1` is hard-rejected even
  though the parser class exists and IS in `--reasoning-parser`'s choices)
  — use `--tool-call-parser auto` for Laguna, not a direct name, to reach
  it without patching vendor code.

  **CRITICAL CAVEAT, also discovered live 2026-08-20**: the native
  `qwen3_coder` parser has a real bug specifically in **streaming** mode.
  Confirmed via a controlled A/B test on Qwen3-Coder-30B-A3B MLX: the
  exact same request (identical system/user prompt, `temperature=0`,
  everything else equal) produces a clean, correct tool call every time
  under `stream: false`, but produces malformed tool_calls with an EMPTY
  function `name` and truncated/garbled `arguments` (e.g. `{"query": `
  with no closing, or a stray literal `<tool_call>` token leaking into an
  argument value) under `stream: true` — which `run_prompt.py` always
  uses (deliberately, to measure real TTFT). This is why the qwen3_coder
  MLX numbers in this leaderboard use **`bench_local_proxy.py`'s own
  custom parser, not the new native one** — the proxy always parses the
  complete non-streaming response before faking SSE back to the client,
  so it structurally cannot hit this streaming-specific bug. **Lesson: for
  any model where a native vllm-mlx parser exists, verify it against BOTH
  a streaming and non-streaming request before trusting it for this
  benchmark (which requires streaming) — do not assume "native support
  exists" implies "native support works safely under streaming."** The
  custom-proxy approach, while more manual, turned out to be the *safer*
  default for models with complex multi-parameter tool-call formats (XML/
  parameter-tag styles), not just a workaround for a missing feature.
  Simpler single-JSON-blob formats (plain `qwen`, `hermes`/`nous`) were not
  re-tested for this same bug and may or may not be affected — don't
  assume either way without checking.
- **GGUF**: llama.cpp's `llama-server` (installed via `brew install
  llama.cpp`, build 10470), OpenAI-compatible, port 8016 — **no proxy
  needed**, confirmed live: it returns proper `tool_calls` natively for LFM
  (unlike vllm-mlx), plus real streaming usage counts (`usage_estimated:
  false`), so hermes's `local-gguf` provider points straight at it. Still
  worth spot-checking a new model family's raw output before trusting
  results (`run_prompt.py` against 8016 directly), since "native for LFM"
  isn't a guarantee for every family, but no proxy work needed unless that
  check fails. Multiple quant levels are tested per candidate model (not
  just one), each as a separate log row.
- **DFlash 2** (speculative decoding, Inco AI/z-lab): **WORKING, as of
  2026-08-20 — reverses the earlier "abandoned" conclusion below.** The
  Homebrew-installed llama.cpp (build 10470) has the `--spec-type
  draft-dflash` CLI flag but NOT the actual DFlash2 tensor-loading logic —
  that only exists in **PR #27342** (`ggml-org/llama.cpp#27342`, still open/
  unmerged at time of writing), whose actual code lives in the author's own
  fork: `z-lab/llama.cpp-fork`, branch `dflash2`. Confirmed via
  https://inco.ai/blog/dflash2/, which explicitly says llama.cpp support
  "requires building from PR #27342." Built it from source (cmake + Ninja +
  Metal, ~2 min build) — kept entirely separate from
  the Homebrew install so `brew`'s `llama-server` is untouched for every
  other model in this benchmark. Two issues on the way to a working
  request, both resolved:
  1. The old "expected 81, got 58" tensor-count error is GONE with this
     fork's binary — that was purely a Homebrew-build limitation (stub flag,
     no loader), not a genuine upstream/checkpoint bug as the earlier
     (wrong) conclusion below claimed.
  2. First real request hit a Metal OOM (`kIOGPUCommandBufferCallbackErrorOutOfMemory`)
     during the draft model's decode — caused by the server's default 4
     parallel slots quadrupling KV-cache memory across BOTH the target and
     draft models at once. Fixed with `--parallel 1`.
  Confirmed live: `bartowski/Qwen3.8-27B-GGUF:Q4_K_M` +
  `incoai/Qwen3.8-27B-DFlash2-GGUF` (Q4_K_M drafter), `--spec-draft-n-max 7`
  per the PR's own benchmark command, `--parallel 1`, `--ctx-size 32768`.
  Real completion: draft_n=791, draft_n_accepted=389 (~49% acceptance),
  9.32 tok/s vs. this benchmark's own baseline non-spec Qwen3.8-27B GGUF
  result (~6.5 tok/s) — a real ~1.4x speedup (less than the PR's cited
  1.85x on a 64GB M5 Pro, plausibly due to this being a 32GB machine plus
  `<think>` reasoning tokens counted in the total). **To reproduce**: run
  `runner/setup_dflash2_fork.sh` (builds into `runner/.dflash2-fork/`,
  gitignored — a durable, one-command setup, not scratchpad-only), then
  launch `runner/.dflash2-fork/build/bin/llama-server` with `--spec-type
  draft-dflash --spec-draft-hf <drafter-repo> --spec-draft-n-max 7
  --parallel 1`. This fork binary is NOT installed system-wide like the
  Homebrew build — every config using it must point at
  `runner/.dflash2-fork/build/bin/llama-server` explicitly.
  <!-- Earlier (2026-08-19/20), wrongly concluded abandoned: -->
  <details><summary>superseded reasoning (kept for context, do not trust)</summary>
  Originally concluded broken upstream after 3 Homebrew-build attempts on
  Qwen3.8-27B and 1 on Muse-Glimmer-30B all hit the same tensor-count
  error, reasoning that two unrelated checkpoints hitting an identical
  error ruled out a per-checkpoint problem. That inference was correct
  in isolation but incomplete — it didn't consider that the INSTALLED
  BUILD itself (not the checkpoints) was the actual common cause, since
  Homebrew's llama.cpp only merged the CLI flag, not PR #27342's loader
  implementation. Lesson: a bug reproducing identically across multiple
  models is strong evidence against a per-model cause, but does not by
  itself rule out a shared-tooling cause — check the tool's own version/
  build provenance against the feature's actual merge status before
  concluding "upstream broken," especially for a flag that exists but a
  PR implementing it is still open.
  </details>

## Unloading local backends (validated live 2026-08-19)

`runner/unload_all.sh` / `runner/restore_local_backends.sh`. Two
**independent** supervisors were found keeping a `vllm_mlx.server` alive on
port 8012, and both had to be stopped properly (pkill alone just gets
fought and respawned):

1. **`cocore`** — not just a personal local-model server: a client for the
   decentralized `cocore.dev` compute network, paired to Tijs's `tijs.org`
   ATProto identity, actively **serving inference to that network**
   (`cocore agent active` → `serving`). Stopping it for a benchmark run
   takes the machine offline as a network provider for the duration —
   confirm with Tijs before running unload_all.sh if that matters that day.
   `cocore agent pause` only stops new work being routed here, it does
   **not** unload the model from memory (~11.5GB for LFM2.5-2.6B) — actually
   freeing it needs `cocore agent models set ""`, which (despite being
   documented as "bounces the daemon") fully unloads the LaunchAgent and
   needs `launchctl bootstrap` to bring back, not just a re-run of `models
   set` with a real model.
2. **hermes's own separate LaunchAgent**, `ai.hermes.mara-mlx` — the
   "fitness" profile's own local-model fallback, entirely independent of
   cocore, also targeting port 8012. Stop via `launchctl bootout gui/501/
   ai.hermes.mara-mlx`, restore via `launchctl bootstrap`.

## Hermes's hard minimums (applies to every future model config)

- **`context_length` must be >= 64,000** in the bench profile's provider
  entry, or `hermes chat` refuses to start at all ("Failed to initialize
  agent: ... below the minimum 64,000 required by Hermes Agent") —
  discovered 2026-08-19 testing Qwen3.5-9B at `--ctx-size 32768`. This only
  bites the **coding suites** (driven via `hermes chat`) — `sanity`/
  `hermes_ops` go through `run_prompt.py` directly and don't hit hermes's
  own startup checks. When picking a server `--ctx-size` for a new model,
  size it for the coding suites' needs (>=64K) even if `hermes_ops`'s own
  prompt would fit in less — one server config serves both types of test.

## Reproducibility / pinned dependencies

- **Fixtures**: `Cargo.lock` (kiem_mini), `package-lock.json` (hearth_mini),
  `deno.lock` (kipclip_mini) are all tracked in git — a benchmark run should
  be byte-for-byte reproducible, not dependent on whatever happens to be
  latest on a registry that day.
- **Runner scripts** (Python): `pyproject.toml` declares the control-plane
  dependencies plus the pinned MLX serving stack; `uv.lock` pins the resolved
  environment. Set up the project with `uv sync --locked`; uv is the sole
  benchmark Python workflow, so invoke runner/proxy scripts and vllm-mlx with
  `uv run --locked ...`. Do not reuse CoCore's Python environment for benchmark
  processes. Hermes remains an intentionally
  external CLI and may be selected with `BENCH_HERMES_BIN=/path/to/hermes`.
- **Every logged result** carries `config_path`, `config_hash` (a sha256
  prefix of the exact config content at run time), and `runner_git_sha`
  (the harness's own git sha, `+dirty` if graded by uncommitted code).
  **Fixed 2026-08-21** (adversarial review, finding C3): `config_hash`
  alone did NOT make a row traceable — every config gets edited after
  being run, so the hash in an old row stopped matching the live file, and
  the leaderboard linked to settings that no longer existed. `runner/
  bench_common.py`'s `snapshot_config()` now saves a verbatim copy of the
  exact config content to `results/configs/<hash>.yaml` on every run (not
  just the hash), and the leaderboard links there instead; rows from
  before this fix are flagged "unsnapshotted, predates 2026-08-21 fix" and
  "config since changed" rather than silently presented as trustworthy.
  Similarly, `runner_git_sha` joined the leaderboard's grouping key
  (finding C4) — the max_turns=6 bug, the mock-wording leak, the
  stale-cache bug, and other runner/grading fixes all changed the
  *meaning* of a result without changing any config, so pre-fix and
  post-fix runs used to get silently averaged into the same leaderboard
  cell purely because they shared a config_hash.
- Hermes routes to whichever is live via a dedicated `custom_providers: bench`
  entry in `~/.hermes/config.yaml`, toggled for the duration of a run and
  restored after. Validated end-to-end live 2026-08-20 (see commit
  `c716b3a`): `run_bench.py`'s full unload → launch → health-check →
  sanity → hermes_ops → coding spot-check → leaderboard sequence ran
  unattended and matched historical data exactly.
- Hugging Face auth is configured for higher-rate model downloads (both this
  session and any hermes-spawned agent session): token in
  `~/.cache/huggingface/token` and `HF_TOKEN` exported in `~/.zshrc`.

## Isolated oMLX backend (added 2026-08-21)

oMLX is a third, first-class framework, not another spelling of `mlx`.
The pinned 0.6.2 checkout lives under
`~/.local/share/local-model-bench/omlx-src` at commit
`f2d36f3d25a7e7a2401a92eecafc28b8f8968ec7`; `runner/bootstrap_omlx.sh` uses
uv to create/update its dedicated virtualenv. Its model root, base path, port
8020, logs, and caches do not overlap CoCore, Mara, vllm-mlx, llama.cpp,
`~/.omlx`, or the project's uv `.venv`. Do not add oMLX or its patched pinned
MLX stack to `pyproject.toml`; the isolated runtime is intentional.

- Start through `runner/start_omlx_server.sh`; it requires an exact local
  served-directory ID, disables implicit Hugging Face cache discovery, writes
  validated global/per-model settings, and distinguishes cold, hot-only, and
  SSD cache modes plus Lightning MTP off/on.
- Stop through `runner/stop_omlx_server.sh`. `run_bench.py` invokes it in a
  `finally` path, including identity/load/sanity failures, so no stale Metal
  model is left on port 8020.
- A successful `/v1/models` catalog response is not readiness. Require exact
  served-ID membership, a real plain completion, and
  `runner/probe_omlx.py`'s streaming/non-streaming schema validation before
  recording tool-use results.
- The Qwen/LFM `oQ4e-fp16` / `oQ4-fp16` artifacts are mixed-precision 4-bit
  oQ models with FP16-preserved tensors, not full-FP16 controls. Keep
  `quant_family`, `cache_mode`, and `mtp_mode` explicit in every config.
- Use `uv run --locked python runner/run_bench.py --all --inference-engine omlx` for
  the sequential oMLX-only matrix. Never launch two local model servers
  concurrently.

## Killed-task retry hazard (found live 2026-08-20, auto-fixed 2026-08-21)

If a `run_fixture_suite.py` invocation gets killed (e.g. a backgrounded
shell task terminated externally), killing the client process does not
cancel its already-in-flight request server-side (`bench_local_proxy.py`'s
queue has no way to abort an in-progress `urllib` call — see
`GenerationQueue`'s own docstring). That orphaned request keeps generating
and can collide with a retry's first request: the retry queues behind it,
`hermes chat`'s own client-side timeout fires while waiting, the proxy logs
a `cancelled` queue event, hermes silently retries — and in the one case
observed live, that cancel+retry cycle was enough to produce a spurious
FAIL (a `filter_by_tag` patch that should have applied cleanly appeared not
to). A clean rerun against an *idle* proxy passed with no issue.

**Fixed 2026-08-21**: `run_fixture_suite.py` now reads the config's
`orchestration.needs_proxy`/`proxy_port` itself and calls
`wait_for_proxy_idle()` before the task loop starts — it polls `/healthz`
(which already reports `generation_queue.active`/`.queued`, no proxy
changes needed) and refuses to proceed until both read zero, exiting with
a clear message after 60s if they never do. This is automatic now, not a
manual discipline to remember — but the underlying cause (urllib can't
cancel an in-flight request) is unfixable short of a different HTTP client,
so the hazard itself still exists; this just stops it from silently
producing a bad result.

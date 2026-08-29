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

**Full coding-suite battery is the default (changed 2026-08-25):** an
adversarial review (finding H1) added `--coding-suites` so `run_bench.py`
could run every task in every suite instead of the single historical
`kiem_mini-feature` spot-check, but left it opt-in. That kept causing a
real, recurring miscommunication: "run all tests"/"full benchmark run"
requests kept getting the quick single-task spot-check by default instead,
more than once, because opt-in meant the flag had to be remembered every
time. All three suites (11 tasks total) now run by default; pass
`--coding-suites none` for the old quick behavior when a fast sanity pass
on a big/slow model is what's actually wanted — the full battery can turn
a few-minutes-per-config sweep into hours.

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

  **vllm-mlx 0.4.1+ ships native tool-call parsers** (`vllm-mlx serve
  <model> --enable-auto-tool-choice --tool-call-parser <name>`, a
  different, richer entry point than the bare `python -m vllm_mlx.server`
  module invocation used elsewhere in this repo) — but two real bugs/gaps
  were found in it (the `poolside_v1`/Laguna parser missing from the CLI's
  `choices=` list — use `--tool-call-parser auto` as the workaround; and a
  critical streaming-mode bug in the native `qwen3_coder` parser, which is
  why this benchmark's qwen3_coder MLX numbers use `bench_local_proxy.py`'s
  own parser instead of the native one). Full story, versions, and the
  exact reproduction in
  [`docs/INFERENCE_ENGINES.md`](docs/INFERENCE_ENGINES.md)'s vllm-mlx
  section — read it before trusting any new native vllm-mlx parser for
  this benchmark's streaming requests.
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
- **DFlash 2** (speculative decoding, Inco AI/z-lab): **WORKING**, but
  needs a from-source llama.cpp build — the Homebrew build has the CLI
  flag (`--spec-type draft-dflash`) but not the real tensor-loading logic,
  which only exists in `ggml-org/llama.cpp#27342` (still open/unmerged),
  built from the author's fork `z-lab/llama.cpp-fork`, branch `dflash2`.
  Full discovery story (including a misdiagnosis worth reading for the
  general lesson) and confirmed real speedup numbers in
  [`docs/INFERENCE_ENGINES.md`](docs/INFERENCE_ENGINES.md). **To
  reproduce**: run `runner/setup_dflash2_fork.sh` (builds into
  `runner/.dflash2-fork/`, gitignored), then launch
  `runner/.dflash2-fork/build/bin/llama-server` with `--spec-type
  draft-dflash --spec-draft-hf <drafter-repo> --spec-draft-n-max 7
  --parallel 1` (the `--parallel 1` is required — the server's default 4
  parallel slots quadruples KV-cache memory across target+draft models
  and OOMs on Metal otherwise). This fork binary is NOT installed
  system-wide like the Homebrew build — every config using it must point
  at `runner/.dflash2-fork/build/bin/llama-server` explicitly.

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

## "Best overall" leaderboard ranking (four rounds of redesign, 2026-08-25 — 2026-08-29)

`runner/build_leaderboard.py`'s composite ranking has gone through four
designs, each triggered by a real bad ranking found on live data — the
full round-by-round formula history lives in the code's own docstrings
(`rank_groups()` and `_composite_coding_score()`), not duplicated here.
Summary, oldest to newest:

- **Round 1** (2026-08-25, commit `fa0046f`, methodology review finding
  F3): a weighted blend, `score = 0.5*coding_pass_rate +
  0.3*hermes_ops_pass_rate + 0.2*speed_score`, gated so a group needed at
  least one coding-suite row, deduped to the most-evidenced fragment per
  `(model, inference_engine, quant)`, with mild small-sample shrinkage on
  the coding rate so a lucky 1/1 didn't tie a properly-tested 11/11.
- **Round 2** (2026-08-26, commit `5203553`, user feedback): the blend
  still let speed and hermes_ops act as *peers* of coding instead of
  subordinate to it. Replaced with gate-then-rank: hermes_ops ≥50%
  became a hard pass/fail usefulness gate (not a weighted input), plain
  `coding_pass_rate` (no shrinkage) became the primary sort among
  gate-passers, avg tok/s only a tie-break.
- **Round 3** (2026-08-27, commits `a752772`/`319b144`, benchmark v2):
  gate-then-rank couldn't distinguish "genuinely better at coding" from
  "barely scraped a pass after using every turn," and gave a
  slow-but-eventually-correct model no credit for finishing once the
  coding-suite timeouts were bumped. Replaced the primary sort with a
  weighted composite (pass 45%, speed 25%, time 20%, turns 10%) among
  gate-passers; the hermes_ops gate itself was unchanged, and hermes_ops
  still wasn't part of the score.
- **Round 4** (2026-08-29, commit `d327fdf`, user feedback): a
  bare-50%-hermes_ops model was scoring identically to a 100%-hermes_ops
  one once both cleared the gate — hermes_ops quality above the gate was
  invisible to score. "pass" is now the COMBINED hermes_ops+coding pass
  rate (every task, either suite, counts as one equal unit), not coding
  alone. The gate itself is still unchanged.

Two more fixes landed the same day as round 4, at the eligibility/dedup
layer rather than the score formula: dedup now prefers a fragment that's
complete on all three axes over one that merely has more raw evidence
but is missing an axis (commit `778c513` — see "known side-effect" below,
now partially fixed); and eligibility requires the FULL suite on both
hermes_ops and coding (`FULL_HERMES_OPS_TASKS`/`FULL_CODING_TASKS` in
`build_leaderboard.py`, not just "at least one row") plus a
`runner_git_sha` at or after the `benchmark-v2` git tag, not pre-v2
methodology (commit `e86cf80`).

**Versioning via git tags**: this repo marks methodology-version
boundaries with annotated git tags rather than only prose — `git tag -l
-n1` is the live source of truth, don't duplicate exact tag wording into
markdown (it will drift). Two tag families exist: `benchmark-v*` marks
GRADING/execution methodology boundaries (e.g. `benchmark-v2` is the
Swift-fixture-fix + timeout-bump commit that `runner/build_leaderboard.py`'s
`_is_v2_or_later()` actually checks rows against — data before it isn't
comparable to current data regardless of suite coverage); `leaderboard-
ranking-v*` marks SCORING-formula boundaries (the four rounds above, v1
through v4) — these don't affect whether a model's raw results are
valid, only how already-recorded results get ranked/displayed. Bumping
`FULL_CODING_TASKS` past 11 (e.g. once the 2026-08-29 benchmark-hardening
wiring's 12-task `kipclip_mini` suite has real rerun data behind it) is
exactly the kind of change that should get a new `benchmark-v*` tag.

**Known side-effect, partially fixed 2026-08-29**: the strict "all three
axes in one `(config_hash, runner_git_sha)` fragment" eligibility check
is sensitive to `runner_git_sha` changing mid-run. If a harness-code
commit lands while a background benchmark process is still executing,
that config's rows can split across two or three `runner_git_sha`
values purely because git HEAD moved, not because the run itself was
incomplete. Commit `778c513` fixed the case where a genuinely complete
fragment exists somewhere among the split (dedup now prefers it over an
incomplete-but-richer one — this was silently erasing Luna/OpenRouter
from "Best overall" entirely before the fix). Still open: a model with
NO single fragment that's complete on its own, only complementary
partial ones — merging evidence across fragments graded by different
harness code risks blending incompatible grading semantics, so this
case still doesn't appear (the Qwen3.8-27B xhigh-effort row is a live
example — `results/SUMMARY.md` reconciles it by hand). Worth avoiding
(don't commit harness code while a benchmark process is mid-run) rather
than fully solving in the grouping logic, unless it keeps recurring.

## Backend health-check timeout raised 600s -> 1800s (2026-08-26)

`bench_common.BACKEND_HEALTH_TIMEOUT_SECONDS` (used as `wait_for_health()`'s
default in `run_bench.py`) was 600s from the start of the project. Confirmed
twice this session that a large GGUF's cold-cache first load can genuinely
exceed that on this hardware while the server is loading fine, not hung:
`LiquidAI/LFM2.5-8B-A1B-GGUF:BF16` and `ornith-ai/Ornith-1.5-35B-A3B-
GGUF:Q4_K_M` (~17.5min real load time) both reported "backend never became
healthy" at 600s — verified both times via the server log ("model
loaded"/"listening") and a live curl showing the server actually up and
responding. Each false negative cost a manual `unload_all.sh` + relaunch
cycle (the model is OS-cached after the failed attempt, so the retry loads
fast). Raised to 1800s — a genuinely dead backend still gets caught, just
later, which is cheap for a benchmark that already runs unattended for
hours per config.

## 12-config trimmed-list full rerun (2026-08-25 to 2026-08-26)

After the near-duplicate retirement decision (see `results/SUMMARY.md`'s
"retired near-duplicate configs" section) trimmed the active GGUF
candidate list to 12 configs, every one of them was rerun with the full
3-suite battery (sanity, hermes_ops, all three coding suites) under
current grading, one config at a time, autonomously, committing after
each. Result: a three-way tie at 91% coding pass rate between
Ornith-1.5-35B-A3B, Qwen3.6-35B-A3B-Uncensored, and Qwen3.8-27B
(UD-Q5_K_M) — see `results/SUMMARY.md` for the full comparison and current
pick. Two genuine harness issues surfaced and were fixed during this rerun
(both documented above): the leaderboard ranking redesign and the
health-check timeout raise. One config (Laguna-XS-2.1) remains unresolved
— its GGUF server responds to real completions but this harness's plain-
completion probe doesn't recognize its reasoning-only output shape; not a
model failure, a probe gap.

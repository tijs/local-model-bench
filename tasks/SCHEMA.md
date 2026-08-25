# Task file schema

One YAML file per suite in `tasks/`. Loaded by `runner/run_fixture_suite.py`
(fixture-based suites) or `runner/run_prompt_suite.py` (prompt-based suites) —
`runner/run_bench.py` is the actual single entry point that drives either,
per config (adversarial review finding M7: this doc previously named a
`runner/run_suite.sh` that has never existed in this repo). Two
families, distinguished by the top-level `runner:` field:

- **`runner: fixture`** (or omitted, the default) — `kiem_mini`, `hearth_mini`,
  `kipclip_mini`. A real project the agent edits with real tools (file edit,
  git, cargo/npm/deno). See "Fixture-based tasks" below.
- **`runner: prompt`** — `sanity`, `hermes_ops`. No project, no file edits: a
  single (or scripted multi-turn) chat-completions exchange against a
  model+inference-engine endpoint, with tool calls intercepted and given a scripted mock response.
  Driven by `runner/run_prompt.py` + graded by `runner/grade_prompt.py`. See
  "Prompt-based tasks" below.

## Fixture-based tasks

```yaml
suite: <slug>              # matches tasks/<slug>.yaml, fixtures/<slug>/, checks/<slug>/
languages: [rust, swift]
timeout_seconds: 900          # per-task wall-clock budget; exceeding it is a fail

tasks:
  # Every suite has exactly 3 tasks, one of each type (see AGENTS.md):
  #   feature      — implement a new function against a given signature
  #   debug        — fix a real, unhinted bug in existing code
  #   test-writing — write tests for correct-but-under-tested existing code
  - id: <suite>-feature
    title: <short human label>
    type: feature                # feature | debug | test-writing
    difficulty: 1-5
    language: rust
    prompt: |
      Exact instruction text sent to the agent as the task. Self-contained,
      describes the feature/fix from the user's point of view. Never mentions
      or hints at the grading test — that lives separately under checks/.
    expected_tools: [file_edit, git, cargo]
    check:
      type: command
      command: "cargo test --test check_<name>"
      cwd: .                     # relative to run dir
      expect_exit_code: 0

  - id: <suite>-testwrite
    title: <short human label>
    type: test-writing
    difficulty: 1-5
    language: rust
    prompt: |
      Names the exact file the agent must write its tests into, and
      describes the behaviors/edge cases to cover — without revealing the
      mutants used to grade it.
    expected_tools: [file_edit, cargo]
    check:
      type: mutation
      agent_test_file: rust/tests/<name>.rs   # where the agent must put tests
      source_file: rust/src/lib.rs             # file swapped for each mutant
      test_command: "cargo test --test <name>"
      mutants:
        - checks/<suite>/<task-id>/mutants/mutant1_lib.rs
        - checks/<suite>/<task-id>/mutants/mutant2_lib.rs
      require_kill: all          # agent's tests must pass on the real impl
                                  # AND fail against every mutant
```

Graded via `runner/grade_mutation.sh <run-dir> <source_file> <test_command>
<cwd> <mutant...>` for `type: mutation` tasks — see that script for the
exact semantics. `<cwd>` (relative to run-dir, e.g. "rust" for a Cargo
project living under run-dir/rust/) was added 2026-08-21 (1st adversarial
review, finding H1); this doc previously still showed the old 4-argument
form missing it, which would produce a confusing "test cwd not found"
error for anyone invoking the script by hand per these docs (3rd
adversarial review, finding CR3-16).

## Run lifecycle

Implemented as functions inside `runner/run_fixture_suite.py` —
`reset_fixture()` / `overlay_check_files()` / `grade_command()` /
`grade_mutation()`. (This section previously named `runner/new_run.sh` /
`runner/grade_run.sh`, neither of which has ever existed in this repo — the
lifecycle has always lived as functions in run_fixture_suite.py itself, not
separate scripts. Corrected 2026-08-21, adversarial review finding M7.)

1. **Reset**: copy `fixtures/<suite>/` to a scratch run dir, `git init -q &&
   git add -A && git commit -q -m baseline` there — this is the fixed,
   identical starting point every time.
2. **Task**: the agent works in the run dir using only what `prompt` says.
   The held-out check file(s) under `checks/<suite>/<task-id>/` do not exist
   in the run dir yet and are never shown to the agent.
3. **Grade**: copy `checks/<suite>/<task-id>/*` into the run dir (adding the
   grading test file(s) alongside whatever the agent wrote), then run
   `check.command`. Exit code 0 = pass. This is the only scoring signal —
   never an LLM judge, never manual review.
4. **Teardown**: delete the run dir. Next task/model starts from step 1
   again, so every attempt sees the exact same byte-identical baseline.

Held-out tests, not agent-authored tests: this mirrors SWE-bench/HumanEval —
the agent is scored against a test it never had the chance to special-case,
which is what makes automated pass/fail meaningful instead of gameable.

## Prompt-based tasks

```yaml
suite: sanity
runner: prompt
timeout_seconds: 60
max_turns: 40   # optional, defaults to 6 (run_prompt.py's CLI default) if omitted
# Optional liveness/total budgets — see "Timeout and liveness budgets" below
task_timeout_seconds: 14400
first_progress_timeout_seconds: 600
stream_idle_timeout_seconds: 300
connect_timeout_seconds: 60

tasks:
  - id: sanity-tool
    type: tool-call              # prompt-response | tool-call
    prompt_spec:
      system_prompt: "..."
      user_prompt: "..."
      tools: [ {type: function, function: {...}}, ... ]   # OpenAI tool schema, omit for prompt-response
      mock_tool_responses: { tool_name: "<string returned as the tool result>" }
      force_tool_error: [tool_name, ...]   # optional — return a scripted error instead
    check:
      type: tool_call_then_response   # regex | contains | contains_any | tool_call_then_response | chained_tool_calls
      expected_tool: add_numbers
      expected_args: { a: 15, b: 27 }  # optional — omit/empty to accept any arguments.
        # A REQUIRED SUBSET of the actual call's arguments (extra args the
        # model passes are fine), numeric-aware value comparison (15 == 15.0),
        # order-agnostic on which key the dict lists first — but keys must
        # match exactly (add_numbers(x=15,y=27) does NOT satisfy {a:15,b:27}).
        # This is NOT "order-agnostic on values" (a value multiset match) —
        # that was the ORIGINAL, exploitable behavior, replaced 2026-08-21;
        # this doc is corrected to match, not describing an aspiration.
      expected_args_match: { query: "(?i)amsterdam" }  # optional — per-argument
        # regex, checked against whichever call(s) also satisfy expected_args
        # (or any call to expected_tool if expected_args is omitted/empty).
        # Needed because mock_tool_responses is keyed by TOOL NAME ONLY — an
        # empty/omitted expected_args accepts a call with ANY arguments, so a
        # task that cares WHAT the model searched/asked for (not just which
        # tool it picked) needs this to actually verify that.
      response_contains: "42"   # or response_matches: "regex" for a value that
        # needs a boundary a bare substring can't express (e.g. "18" must not
        # match inside "2018" — use response_matches: "(?<!\d)18(?!\d)")
```

Any check dict, regardless of `type`, may also carry — checked BEFORE the
type-specific logic, against `final_text`:
```yaml
      must_not_contain_any: ["it says", "the file contains"]  # hard veto: a
        # match here fails the check even if the positive condition ALSO
        # matched — for ruling out a specific wrong-but-plausible-looking
        # answer (e.g. a model fabricating file contents it was never given)
      must_not_match: "some regex"   # same, as a regex
```

`chained_tool_calls` takes `expected_sequence: [tool_a, tool_b, ...]` (each
must appear in order, not necessarily contiguous) and optionally
`write_file_arg_contains` (substring match on the `content` argument
specifically, not any argument), `write_file_arg_equals` (exact match,
whitespace-stripped — for a prompt asking to write JUST a value, where
`_contains` would also accept a sentence wrapped around it), and
`write_file_arg_path` (suffix match on the `path` argument — neither of the
two content checks above verifies WHERE the model wrote to).

Check types: `regex`/`contains` match `final_text` directly and are
case-sensitive (an exact literal/pattern check shouldn't silently accept
a differently-cased answer). `contains_any` takes `phrases: [...]` and
passes if any appear, case-INsensitively — used for error-recovery tasks
where several acceptable phrasings exist; deliberately not the same case
sensitivity as `contains`/`regex`, since it's for natural-language phrase
matching where case carries no meaning. `tool_call_then_response` requires
a specific tool was called (optionally with specific/regex-matched
argument values) and the final response contains/matches a string.
`large fixture files` (a full real tool manifest, a large system
prompt) go in `prompt_spec` as `tools_file`/`system_prompt_file` (paths
relative to repo root) instead of inlining huge JSON/text into the YAML —
`run_prompt_suite.py` resolves and merges them before calling
`run_prompt.py`.

Runner mechanics: `prompt_spec` is written to a temp `spec.json` and passed to
`runner/run_prompt.py --base-url <backend> --model <candidate> --spec
spec.json`, which sends the exchange (mocking any tool call named in
`mock_tool_responses`/`force_tool_error`, looping until the model stops
calling tools or `--max-turns` is hit) and prints a result JSON (full
transcript, `tool_calls`, `final_text`, token counts, `tokens_per_second`).
`check` is written to a temp `check.json` and graded via
`runner/grade_prompt.py --result <result.json> --check check.json` — prints
PASS/FAIL, exit 0/1.

**Reasoning-trace stripping**: several local models (LFM included) emit an
inline `<think>...</think>` block before the real answer. `grade_prompt.py`
strips it before matching, so grading only ever scores the actual answer, not
whether the model reasoned first.

**max_turns matters more than it looks**: defaults to 6 (run_prompt.py's own
CLI default) if the suite file omits it — an arbitrary number, not matched
to anything. `hermes_ops` sets it explicitly to 40 to match this
benchmark's own `~/.hermes/profiles/bench/config.yaml` `agent.max_turns`
(discovered live 2026-08-20 that the un-set default silently produced 14
false "exceeded max_turns" failures across nearly every model tested —
verified on Qwen3.8-27B that the same model/temperature converges cleanly
by turn 11 given 15 turns instead of 6, doing reasonable diagnostic
exploration rather than looping). Always set this explicitly for a new
suite rather than relying on the fallback.

### Timeout and liveness budgets

Added 2026-08-25 after repeated live hangs: an oMLX backend's SSE stream
would stall mid-response (many tiny completions, or one partial one that
never converged) while the harness's only bound — a derived
`timeout_seconds * max_turns + 60` subprocess deadline, about **11 hours**
for `hermes_ops` — never fired. The run then sat there holding a server
slot until a human noticed and killed it by hand. That happened on at
least four configs in one session, and one Ornith-1.5-9B run burned the
full 11 hours.

The root cause was one number doing three incompatible jobs:
`timeout_seconds` was passed to `urllib.request.urlopen()`, where it acts
as a **socket inactivity** timeout — so any occasional byte (an SSE
keepalive comment, a usage-only chunk, one partial delta) reset it
forever. Lowering it was not an option: a genuinely slow-but-progressing
model produced a passing `hermes_ops-selection` row at 1277.383s, and
passing `hermes_ops` rows reach 8839.930s.

There are now four **explicit, separately meaningful** budgets, all
measured on `time.monotonic()`:

| key | scope | enforced by |
| --- | --- | --- |
| `timeout_seconds` | total budget for ONE HTTP turn | `run_prompt.py` |
| `task_timeout_seconds` | total budget for one suite task (all turns) | `run_prompt_suite.py` |
| `first_progress_timeout_seconds` | response headers → first *meaningful* SSE event | `run_prompt.py` |
| `stream_idle_timeout_seconds` | gap between two *meaningful* SSE events | `run_prompt.py` |
| `connect_timeout_seconds` | TCP connect + request send + response headers | `run_prompt.py` |

**"Meaningful"** means a content delta, a tool-call delta, a
`finish_reason`, or the terminal `[DONE]`. It deliberately excludes blank
lines, `:`-prefixed SSE comments/keepalives, role-only opening deltas, and
usage-only chunks — precisely the traffic a stalled stream keeps emitting.

The generous total budgets are kept so a slow-but-progressing model is
never rejected for being slow; the liveness watchdogs catch a stalled
response in **minutes**. Omitting `task_timeout_seconds` falls back to
`min(timeout_seconds * max_turns + 60, 14400)` — the old derived value,
but capped so no suite can silently inherit an 11-hour ceiling again.

When a task deadline fires, the request subprocess's whole **process
group** is terminated (SIGTERM, then SIGKILL after a grace period) so no
grandchild or in-flight backend request is left running, and its partial
stdout/stderr is preserved next to the durable result. The log row records
`timeout_phase` (`connect` / `first_progress` / `stream_idle` /
`turn_total` / `task_deadline`, or `null`) and `partial_output_path`, so a
stalled engine, a merely slow model, and a dead backend are three
distinguishable outcomes rather than one. A task deadline is recorded as a
**model/engine** failure (`pass: false`), *not* `harness_error` — the
harness did exactly what it was supposed to.

`bench_local_proxy.py` keeps its own separate pair: `UPSTREAM_TIMEOUT`
(now a real monotonic overall deadline, returning `504` when it fires) and
`BENCH_PROXY_UPSTREAM_READ_IDLE_TIMEOUT`. It deliberately does *not* use a
token-progress watchdog, because it issues a non-streaming upstream
request and buffers the whole response into one SSE chunk — there are no
incremental tokens on that path to watch.

**Temperature is deliberately fixed at 0** for every `run_prompt.py` call
(`sanity`/`hermes_ops`) — these suites test precise behavior fidelity (right
tool, right args, converges vs. loops), where determinism matters more than
matching a model's "recommended" sampling settings. This means a model's
researched `temperature`/`top_k`/`repetition_penalty` (in `configs/<model>/
*.yaml`) do **not** apply to sanity/hermes_ops — the client always overrides
the server default. They **do** apply to the coding suites, since `hermes
chat` (used by `run_fixture_suite.py`) doesn't hardcode temperature and
respects the server's launch flags. Don't attribute a sanity/hermes_ops
result to a sampling-settings change without checking this first (a
2026-08-19 result was initially mis-attributed this way — see kiem notes).

**Endpoint matters more than it looks**: for an MLX config whose model needs
translation (`orchestration.needs_proxy: true`), always point `--base-url` at
**this repo's own `runner/bench_local_proxy.py`, port 8015** — never
`vllm_mlx.server` directly on 8012 (raw engine, can return a tool call as
unparsed text instead of a real `tool_calls` array) and never port 8013
(`mara_local_proxy.py`, the "fitness" hermes profile's OWN proxy — it
unconditionally filters every caller's `tools` array down to its own ~12-tool
allowlist, which silently produced false-passing tool-selection results
before this was caught; see AGENTS.md "Backends"). This doc previously named
8013 as the example to follow, which was exactly backwards — corrected
2026-08-21 (adversarial review finding M6).

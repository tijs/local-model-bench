# Task file schema

One YAML file per suite in `tasks/`. Loaded by `runner/run_suite.sh`. Two
families, distinguished by the top-level `runner:` field:

- **`runner: fixture`** (or omitted, the default) — `kiem_mini`, `hearth_mini`,
  `kipclip_mini`. A real project the agent edits with real tools (file edit,
  git, cargo/npm/deno). See "Fixture-based tasks" below.
- **`runner: prompt`** — `sanity`, `hermes_ops`. No project, no file edits: a
  single (or scripted multi-turn) chat-completions exchange against a model
  backend, with tool calls intercepted and given a scripted mock response.
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
<mutant...>` for `type: mutation` tasks — see that script for the exact
semantics.

## Run lifecycle (see `runner/new_run.sh` / `runner/grade_run.sh`)

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
      expected_args: { a: 15, b: 27 }  # optional — omit/empty to accept any arguments; order-agnostic on values otherwise
      response_contains: "42"
```

Check types: `regex`/`contains` match `final_text` directly. `contains_any` takes
`phrases: [...]` and passes if any appear (case-insensitive) — used for
error-recovery tasks where several acceptable phrasings exist.
`tool_call_then_response` requires a specific tool was called (optionally
with specific argument values) and the final response contains a string.
`chained_tool_calls` takes `expected_sequence: [tool_a, tool_b, ...]` (each
must appear in order, not necessarily contiguous) and optionally
`write_file_arg_contains` to check a later call used an earlier call's
result. `large fixture files` (a full real tool manifest, a large system
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

**Endpoint matters more than it looks**: always point `--base-url` at the
proxy layer a real backend needs (e.g. `mara_local_proxy` on port 8013 for
MLX, not `vllm_mlx.server` directly on 8012 — see AGENTS.md "Backends"). The
raw engine can return a tool call as unparsed text instead of a real
`tool_calls` array, which would silently and unfairly fail every tool-call
check.

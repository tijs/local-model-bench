# Task file schema

One YAML file per suite in `tasks/`. Loaded by `runner/run_suite.sh`.

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

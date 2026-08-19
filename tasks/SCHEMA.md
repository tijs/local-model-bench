# Task file schema

One YAML file per suite in `tasks/`. Loaded by `runner/run_suite.sh`.

```yaml
suite: <slug>              # matches tasks/<slug>.yaml filename
repo: <path>                # source repo this suite's worktrees are cut from
languages: [rust, swift]
base_ref: main               # branch/commit the worktree starts from
timeout_seconds: 900          # per-task wall-clock budget; exceeding it is a fail

tasks:
  - id: <suite>-01
    title: <short human label>
    difficulty: 1-5           # graduated easy -> hard
    language: rust             # primary language touched
    prompt: |
      Exact instruction text sent to the agent as the task. Self-contained —
      no hidden context beyond what's in the repo itself.
    expected_tools: [file_edit, git, cargo]   # tools the run is expected to touch
    check:
      type: command
      command: "cargo test --test content_fixtures"
      cwd: .                  # relative to worktree root
      expect_exit_code: 0
```

Scoring is always automated (`check.command` exit code) — never an LLM judge,
never manual review. If a task needs the agent to write its own test to prove
the fix, say so explicitly in the prompt and have `check.command` run that
suite's normal test command so the new test is included.

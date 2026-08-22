Each suite here is a small, self-contained fixture project (`fixtures/<suite>/`),
tracked directly in this repo — not sourced live from a real project via `git
worktree`. Per task run, `runner/run_fixture_suite.py`'s `reset_fixture()`
copies the suite's directory into a fresh scratch run dir, `git init`s it, and
commits it as the `baseline` tag — a fixed, identical starting point every
time, fully isolated from any real project. No real repo (Tijs's own or
otherwise) is ever touched at run time.

Corrected 2026-08-22 (methodology review, finding F13): this file previously
described an abandoned `git worktree`-against-the-real-repo design (`repo`/
`base_ref` fields in `tasks/<suite>.yaml`) that was never actually built — no
task file has ever contained those fields, and both `tasks/SCHEMA.md` and
AGENTS.md have always documented the self-contained-copy design above. Left
uncorrected, this was the one file a reader would open specifically to verify
the "no real project is ever touched" isolation guarantee, and it said the
opposite of what's actually true.

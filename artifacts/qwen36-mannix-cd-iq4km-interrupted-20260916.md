# Qwen3.6-27B ManniX CD-IQ4_K_M — INTERRUPTED benchmark leg marker — 2026-09-16

Candidate: `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M`
(config `configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml`).

**Status: INTERRUPTED / PARTIAL — 13 of 25 expected rows. This leg is NOT a
completed run, is NOT rank-eligible, and must not be counted as one anywhere
(no leaderboard entry, no completion claim).** The 13 rows are append-only
evidence; they are never hand-edited.

## Measured facts (verified against the checkout at reconciliation, 2026-09-16)

- **Config hash:** `02c0f591926b` — equals the sha256 prefix of the pre-run
  config byte content. Immutable snapshot
  `results/configs/02c0f591926b.yaml` exists and is byte-identical to the
  config file at the run's HEAD commit (`cmp` identical; sha256
  `02c0f591926be85a7dfc6fe5c42f57d1c45a8f0d731acafb558d1625adaab2d9`).
- **Runner SHA:** `91c123cb02a0` (full `91c123cb02a0f8c167cd43bb93773540a22b0ad2`,
  main, ahead of origin). This is the clean runner/config commit used by the
  run; all 13 rows record `runner_git_sha: 91c123cb02a0`.
- **Row shape (results/log.jsonl, append of 13 rows, all `trial` 1, all
  `harness_error: false`):**
  - `sanity` 2 — `sanity-basic`, `sanity-tool` (both pass)
  - `hermes_ops` 8 — `selection`, `chaining`, `error-recovery`,
    `targeted-edit`, `noisy-result`, `multi-step-chain` (FAIL),
    `persistent-failure`, `no-tool-needed`
  - `kiem_mini` 3 — `feature` (FAIL), `rename`, `debug`
  - Totals: **11 pass / 2 fail / 0 harness errors**. Rows span
    `2026-09-16T11:56:12Z` → `12:19:12Z`.
- **Failure classification (both model/task-level, NOT harness):**
  - `hermes_ops-multi-step-chain` — `pass: false`,
    `run_error: "response truncated (finish_reason=length) before a final
    answer — max_tokens=16384 was likely too low for this turn"`,
    `within_budget: false`, `harness_error: false`. Model response hit the
    config's `hermes_ops_max_tokens: 16384` cap.
  - `kiem_mini-feature` — `pass: false`, `harness_error: false`,
    `hermes_exit_code: 0`; held-out Rust graded check failed
    (`error: test failed, to rerun pass --test check_cli_tag_flag`), so the
    agent's diff did not satisfy the task. Model/task-level outcome.
  - `kiem_mini-debug` passed (`pass: true`) but `within_budget: false`
    (360.5 s wall).
- **Transcripts (3, untracked, current methodology):**
  `results/transcripts/kiem_mini/kiem_mini-feature/20260916T121042Z_…_CD-IQ4_K_M.log`,
  `results/transcripts/kiem_mini/kiem_mini-rename/20260916T121302Z_…_CD-IQ4_K_M.log`,
  `results/transcripts/kiem_mini/kiem_mini-debug/20260916T121904Z_…_CD-IQ4_K_M.log`
  (timestamps 12:10:42Z / 12:13:02Z / 12:19:04Z; file mtimes 14:10 / 14:13 /
  14:19 local).
- **Server log observation** (`/tmp/bench_Qwen3.6-27B-A3B-Coder-MTP-GGUF_gguf-cd-iq4km_server.log`,
  copied to `artifacts/qwen36-mannix-cd-iq4km-interrupted-20260916-server.log`):
  112143 bytes, mtime `2026-09-16 14:20:11 +0200` (12:20:11Z). Loads the
  pinned GGUF from the immutable snapshot path. Routine per-turn
  `stop: cancel task` lines appear throughout (stream-stop semantics of the
  harness; the last is task 43815 at 23:47). The log ends during an ongoing
  generation (task 45033, `n_gen` 126→746) with a single
  `operator(): cleaning up before exit...` line at 24:14 (≈14:20:11 local);
  **no shutdown cause or exit code is recorded in the log — the cause is NOT
  proven and must not be inferred.**
- **At reconciliation:** no benchmark/model/server process and no
  benchmark-port listener remains (checked via `pgrep`/`lsof`; port 8017 and
  8082 free; the sole `:5000` listener is macOS ControlCenter, unrelated).
  Beyond the 13-row log append, the snapshot, and the 3 transcripts, the
  working tree had no other changes.
- **Runner exit code: NOT available** in any durable artifact (no run summary
  or exit-code file exists, and the server log records none) — therefore not
  claimed here.

## Missing rows (12 of 25) — not produced before interruption

- `kiem_mini-parse-note`, `kiem_mini-testwrite` (2)
- `hearth_mini-feature`, `hearth_mini-debug`, `hearth_mini-testwrite` (3)
- `kipclip_mini-feature`, `kipclip_mini-debug`, `kipclip_mini-testwrite`,
  `kipclip_mini-merge` (4)
- `hearth_full-feature`, `hearth_full-debug`, `hearth_full-testwrite` (3)

Expected full battery: sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3
+ kipclip_mini 4 + hearth_full 3 = **25 rows** (runner's default
`--coding-suites default` battery since 2026-08-25). The last row present is
`kiem_mini-debug` at 12:19:12Z; the run stopped there with 12 rows outstanding.

## Decision

- This is an **interrupted/partial leg**, never complete or rank-eligible.
  The 13 rows remain append-only evidence and must not be counted as a
  completed/ranked run; the interruption cause is not proven.
- Any future completion of this arm is a fresh run with its own rows; before
  any ranking claim, the full 25-row battery must land and this leg's 2
  model-level failures must be reviewed per the repo's zero-harness-review
  rule. `results/log.jsonl`, `results/LEADERBOARD.md`, and the immutable
  snapshot are not modified by this reconciliation beyond preserving the
  13-row append.
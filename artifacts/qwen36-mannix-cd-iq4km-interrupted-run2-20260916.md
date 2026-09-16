# Qwen3.6-27B ManniX CD-IQ4_K_M — INTERRUPTED benchmark leg marker #2 (run2) — 2026-09-16

Candidate: `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M`
(config `configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml`).

**Status: INTERRUPTED / PARTIAL — 18 of 25 expected rows (second attempt, after
the 13/25 leg in `qwen36-mannix-cd-iq4km-interrupted-20260916.md`). This leg is
NOT a completed run, is NOT rank-eligible, and must not be counted as one
anywhere (no leaderboard entry, no completion claim).** The 18 rows are
append-only evidence; they are never hand-edited.

## Measured facts (verified against the checkout at reconciliation, 2026-09-16)

- **Config hash:** `71b86463d35f` — equals the sha256 prefix of the pre-run
  config byte content. Immutable snapshot
  `results/configs/71b86463d35f.yaml` exists and is byte-identical to the
  config file at the run's HEAD commit (`cmp` identical; sha256
  `71b86463d35f693c3469f00858cc30c8aab3eeb35b23b59cdd08ec172389ee45`).
- **Runner SHA:** `a018d59cefab` (full `a018d59cefabf4d8ea8afda57420e72a4be8220a`,
  main, ahead of origin). This is the clean runner/config commit used by the
  run (working-tree HEAD at reconciliation); all 18 rows record
  `runner_git_sha: a018d59cefab`.
- **Row shape (results/log.jsonl, append of the LAST 18 rows, all `trial` 1, all
  `harness_error: false`):**
  - `sanity` 2 — `sanity-basic`, `sanity-tool` (both pass)
  - `hermes_ops` 8 — `selection`, `chaining`, `error-recovery`,
    `targeted-edit`, `noisy-result`, `multi-step-chain` (FAIL),
    `persistent-failure`, `no-tool-needed` (7 pass, 1 fail)
  - `kiem_mini` 5 — `feature` (pass), `rename` (pass), `debug` (FAIL),
    `parse-note` (FAIL), `testwrite` (FAIL)
  - `hearth_mini` 3 — `feature` (pass), `debug` (pass), `testwrite` (pass)
  - Totals: **14 pass / 4 fail / 0 harness errors**. Rows span
    `2026-09-16T14:01:59Z` → `15:36:09Z` (UTC).
  - `within_budget: false` on 3 rows: `hermes_ops-multi-step-chain` (fail,
    492.8 s wall), `kiem_mini-debug` (fail, 1939.2 s wall),
    `hearth_mini-feature` (pass, 2039.1 s wall). All other rows
    within_budget true.
- **Failure classification (all four model/task-level, NOT harness):**
  - `hermes_ops-multi-step-chain` — `pass: false`,
    `run_error: "response truncated (finish_reason=length) before a final
    answer — max_tokens=16384 was likely too low for this turn, not a real
    answer to grade"`, `within_budget: false`, `harness_error: false`. Model
    response hit the config's `hermes_ops_max_tokens: 16384` cap.
  - `kiem_mini-debug` — `pass: false`, `harness_error: false`. Swift
    compiler failure in the held-out grade (`error: call can throw, but it is
    not marked with 'try' and the error is not handled` → `error: fatalError`);
    agent's diff did not compile/grade clean.
  - `kiem_mini-parse-note` — `pass: false`, `harness_error: false`. Swift
    compiler/type failure in the held-out grade (`error: cannot convert value
    of type 'String.SubSequence' (aka 'Substring') to expected argument type
    'String'`).
  - `kiem_mini-testwrite` — `pass: false`, `harness_error: false`. Mutation
    grading: baseline passed, mutant1 and mutant2 killed, mutant3 SURVIVED
    ("agent's tests did not catch this bug") → `FAIL: 1 mutant(s) survived`
    (2/3 mutants killed).
  - None of the four is a transport/harness failure; there are 0
    `harness_error: true` rows in the leg.
- **Transcripts (8, untracked, current methodology):**
  - `results/transcripts/kiem_mini/kiem_mini-feature/20260916T141657Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/kiem_mini/kiem_mini-rename/20260916T142023Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/kiem_mini/kiem_mini-debug/20260916T145245Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/kiem_mini/kiem_mini-parse-note/20260916T145451Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/kiem_mini/kiem_mini-testwrite/20260916T145738Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/hearth_mini/hearth_mini-feature/20260916T153141Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/hearth_mini/hearth_mini-debug/20260916T153344Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  - `results/transcripts/hearth_mini/hearth_mini-testwrite/20260916T153607Z_ManniX-ITA_Qwen3.6-27B-A3B-Coder-MTP-GGUF_CD-IQ4_K_M.log`
  (timestamps match the row start-times 14:16:57Z…15:36:07Z; kiem_mini and
  hearth_mini only — sanity/hermes_ops rows are one-shot prompt-suite tasks,
  no agentic transcript.)
- **Server log observation**
  (`/tmp/bench_Qwen3.6-27B-A3B-Coder-MTP-GGUF_gguf-cd-iq4km_server.log`,
  copied to `artifacts/qwen36-mannix-cd-iq4km-interrupted-run2-20260916-server.log`):
  280999 bytes, mtime `2026-09-16 17:37:xx +0200` (15:37Z, seconds after the
  last row). Loads the pinned GGUF from the immutable snapshot path
  (`…/models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF/snapshots/
  75a75137d610ed037a09b46c29ca1d37fd000f2e/Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`)
  and listens on `http://127.0.0.1:8017` as the config prescribes. Routine
  per-turn `stop: cancel task` lines appear throughout (stream-stop semantics
  of the harness). The log ends at 95:26 (≈15:36 local) with
  `operator(): operator(): cleaning up before exit...` immediately after a
  `stop: cancel task, id_task = 176256` — i.e. cleanup ordered after a
  generation; **no runner exit code or shutdown cause is recorded anywhere
  durable — the cause is NOT proven and must not be inferred.**
- **At reconciliation:** no benchmark/model/server process (no llama-server,
  no run_bench/bench_common) and no benchmark-port listener remains — 8017,
  8082, 8080 are all free (`lsof`); the sole `:5000` listener is macOS
  ControlCenter (unrelated), and 8766/9119 are long-running Hermes
  infrastructure (tailnet_dashboard_router / hermes dashboard), not
  benchmark. Beyond the 18-row log append, the snapshot, the 8 transcripts,
  and this marker + copied server log, the working tree has no other
  changes (`git status` clean of anything else; verbose
  `results/prompt_results/` files are gitignored and not committed).
- **Runner exit code: NOT available** in any durable artifact (no run summary
  or exit-code file exists, and the server log records none) — therefore not
  claimed here.

## Missing rows (7 of 25) — not produced before interruption

- `kipclip_mini-feature`, `kipclip_mini-debug`, `kipclip_mini-testwrite`,
  `kipclip_mini-merge` (4)
- `hearth_full-feature`, `hearth_full-debug`, `hearth_full-testwrite` (3)

Expected full battery: sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3
+ kipclip_mini 4 + hearth_full 3 = **25 rows** (runner's default
`--coding-suites default` battery since 2026-08-25). The last row present is
`hearth_mini-testwrite` at 15:36:09Z; the run stopped there with 7 rows
outstanding. (This leg covers sanity + hermes_ops + kiem_mini + hearth_mini
completely; the earlier 13/25 leg already produced kiem_mini feature/rename/
debug rows under its own hash 02c0f591926b.)

## Decision

- This is an **interrupted/partial leg**, never complete or rank-eligible.
  The 18 rows remain append-only evidence and must not be counted as a
  completed/ranked run; the interruption cause is not proven.
- Any future completion of this arm is a fresh run with its own rows; before
  any ranking claim, the full 25-row battery must land and this leg's 4
  model-level failures (multi-step-chain truncation at the 16384 cap;
  kiem_mini-debug and kiem_mini-parse-note compiler/type failures;
  kiem_mini-testwrite 1-of-3 surviving mutant) must be reviewed per the
  repo's zero-harness-review rule. `results/log.jsonl`,
  `results/LEADERBOARD.md`, and the immutable snapshot
  `results/configs/71b86463d35f.yaml` are not modified by this reconciliation
  beyond preserving the 18-row append.
- The live config's prose was reconciled in a separate config-only commit
  (this marker's second sibling commit) so it acknowledges this second 18/25
  partial attempt under hash `71b86463d35f` / runner `a018d59cefab` while
  preserving the 13/25 history; that prose edit intentionally changes the
  config hash, and **no benchmark was or will be run against the edited
  config in this cycle**.
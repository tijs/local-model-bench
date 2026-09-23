# Bonsai 2 PTQ1_0 — fresh current-hash native gate + bounded canary (2026-09-23)

**Status: ADMITTED / GATED / UNRANKED.** This unit ran one fresh single-server
bounded native gate (7/7 pass) plus the fixed six-task one-trial canary
(2 passed, 0 failed, 4 errors) under the **current** config hash
`5e4c9a30643f`, then tore the server down. It did **not** run `run_bench.py`,
append `results/log.jsonl`, create a benchmark config snapshot, run coding
suites, touch CoCore, or change the leaderboard. This is admission/capability
evidence only — not a quality or ranking result.

## Identity

- Config: `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml` (byte-identical
  to the run's config; pre-edit SHA-256 re-verified this session == the run's
  recorded `config_sha256`)
- Config hash: `5e4c9a30643f`
- Config SHA-256:
  `5e4c9a30643fc16de04a42f3b13ded6041fc9d7c2ce2892e90997eadd4648aae`
- Run HEAD: `1bd7d8810d53dd59cf189231a84c7268db0d2e6a`; runner SHA carried by
  the canary header and preflight: `1bd7d8810d53`
- Model: `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0`; engine: `llama.cpp-prism`
- Served identity: `bench-5e4c9a30643f`; endpoint `http://127.0.0.1:8017/v1`
- Artifact: revision `6ed5e12bf84b7a63069882c91dd9e9218647d17b`,
  `Ternary-Bonsai-2-27B-PTQ1_0.gguf`, **5,946,648,928 bytes**, SHA-256
  `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`
- Prism runtime: source commit
  `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6`; binary
  `/Users/tijs/.local/share/local-model-bench/prism-llama-5d80cff/build/bin/llama-server`
  — `--version` = `0.2.0-dev (build 1, commit 5d80cff)`, AppleClang for Darwin
  arm64 (identity re-verified at reconciliation)
- Run dir:
  `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260923T-current-5e4c9a30643f`
- Window: server started epoch 1790151768.95664 = **2026-09-23 08:22:48 UTC**
  (10:22:48 CEST), `server_pid 90198`; canary ran 08:39:03 → 08:49:30 UTC.

## Preflight (raw `preflight.json`)

- free disk: `13,561,950,208` bytes = **12.63 GiB**, `free_gate_pass: true`
  (above the runner's 10 GiB `MIN_FREE_DISK_GB_BEFORE_LAUNCH` floor)
- artifact: `artifact_exists: true`, size 5,946,648,928, SHA-256 == expected
  `53107f53…`; `config_sha256` == expected `5e4c9a…`
- git: `head` `1bd7d8810d53dd59cf189231a84c7268db0d2e6a`; `git_status`
  `## main...origin/main [ahead 121]`
- processes/listeners before launch: `matching_processes_before: []`,
  `ports_before: []` — clean single-writer state.

## Fresh native gate (7/7 pass, 0 errors, 0 fails)

All checks ran against the exact pinned binary + staged artifact:

| # | Check | Observed result | Elapsed |
|---|---|---|---|
| 1 | Exact `/v1/models` identity | HTTP 200; sole served ID `bench-5e4c9a30643f` | 0.0016 s |
| 2 | Plain non-stream | `READY`, `finish_reason=stop`; 30 completion / 60 prompt / 90 total tokens | 3.6778 s |
| 3 | Plain streaming | `STREAM_READY`, 32 chunks, `finish_reason=stop`, 0 raw-line errors | 3.0415 s |
| 4 | Native non-stream tool | `lookup({"city":"Amsterdam"})`, `finish_reason=tool_calls` | 8.6753 s |
| 5 | Native streaming tool | `lookup({"city":"Rotterdam"})`, 42 chunks, `finish_reason=tool_calls`, 0 raw-line errors | 5.1781 s |
| 6 | Growing cache reuse | Recall reported `cached_tokens: 312`; response `CACHE_RECALL_7` (first pass 6.6756 s, recall 4.1361 s) | — |
| 7 | Context near boundary | 64,900 content / 64,951 prompt / 64,952 total tokens vs the 65,536 harness ceiling; HTTP 200; `finish_reason=length`; no crash (sizing: probe 2, estimate_repeats 64835, sample_count_1000 1001, tokenizer `/tokenize`) | 930.4619 s |

Gate summary: `passed: true`, `passes: 7`, `errors: 0`, `fails: 0`,
`completed: true`; summed check time ≈ 961.8 s (~16.0 min), dominated by the
930.5 s boundary probe. The server remained usable for the canary.

Raw: run-dir `native-gate.json`, SHA-256
`0d19b110ee39823932577caa9ed2078d44e4b7863a01519a280488119e7fd970`.

## Bounded canary (verbatim command from `run-summary.json`)

```
/opt/homebrew/bin/uv run --locked python runner/canary.py \
  --endpoint bench-5e4c9a30643f@http://127.0.0.1:8017/v1 \
  --trials 1 --max-tokens 2048 --max-turns 2 --timeout 300 \
  --output /Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260923T-current-5e4c9a30643f/canary-2048-t2.jsonl
```

One trial, `temperature=0`, fixed six-task suite. **Completed** with
**2 passed, 0 failed, 4 errors** (`completed=true`; runner returncode 1 due to
the four errors):

| Task | Outcome | Detail | Elapsed |
|---|---|---|---|
| `sanity-basic` | **PASS** | final `42` | 3.3458 s |
| `hermes_ops-chaining` | error | exceeded `max_turns (2)` without a final non-tool-call response (2 turns / 147 completion tokens) | 270.5647 s |
| `hermes_ops-noisy-result` | error | exceeded `max_turns (2)` (3 tool calls across 2 turns) | 38.3509 s |
| `kiem_mini-feature` | error | response truncated (`finish_reason=length`) before a final answer | 148.2449 s |
| `kiem_mini-testwrite` | error | response truncated (`finish_reason=length`) before a final answer | 148.7314 s |
| `canary-multi-turn` | **PASS** | final `cache-reuse-ok` | 17.8116 s |

**Error classification — model/output-budget behavior, not harness failures:**
the two `hermes_ops` errors are tool-chain tasks the model kept driving past
the deliberately tight `max_turns=2` cap of this exploratory canary; the two
`kiem_mini` errors are long reasoning streams cut by the `max_tokens=2048`
output budget (`finish_reason=length`) — the runner itself flags
“max_tokens=2048 was likely too low”. `failed=0`; no transport or harness
errors. Determinism: both passing tasks were identical in the one trial; the
four erroring suites had no comparable non-error trials. The 2/6 shape with
these exact four error kinds matches the 2026-09-18 / 2026-09-22 canaries —
consistent artifact behavior, not a regression.

Raw: run-dir `canary-2048-t2.jsonl`, SHA-256
`8d038f0b3b50575f62e182c28f2445966038f0b57ec9c592982885539018577b`;
`canary.stderr.log` SHA-256
`320d773ab39d1cb796f1cbea22118f0a6418c5bf9291ea8c07808f32f4c9f9e4`;
`canary.stdout.log` empty.

## Zero new benchmark rows / ranking

- `results/log.jsonl` contains **0** rows carrying `5e4c9a30643f`;
  `results/LEADERBOARD.md` contains **0** mentions. No
  `results/configs/5e4c9a30643f.yaml` snapshot exists (only the preserved
  interrupted-leg snapshot `results/configs/5b760871ce84.yaml`).
- Both files predate the run: `log.jsonl` mtime 2026-09-23 08:05 UTC,
  `LEADERBOARD.md` mtime 2026-09-22 13:31 UTC vs run start 08:22:48 UTC —
  untouched by this unit.
- No rows were appended, no speed-gate record, no leaderboard entry, no
  ranking. The candidate remains **gated / unranked**.

## Teardown

- `run-summary.json` records `matching_processes_after: []` and
  `ports_after: []` — no benchmark runner, no canary process, no `llama-server`,
  no listener remains on 8017 or any benchmark port.
- Archived `server.log` (31,360 bytes): single model load, one listener line
  `llama_server: listening on http://127.0.0.1:8017`; the final logged task
  (4868, generated 100 tokens, `tg = 14.19 t/s`, `truncated = 0`) completes,
  then `operator(): cleaning up before exit...` — orderly shutdown.
- Byte-identical server-log copy archived at
  `artifacts/bonsai2-ptq1-current-gate-20260923-server.log`, SHA-256
  `ff68fb34217df5405e507a491ff8011ceaf3702eff6af8b2523a3c96a2c86020` ==
  run-dir `server.log` (verified byte identity at copy time).
- No CoCore action was taken; no server was left running.

## Decision

Keep PTQ1_0 **gated and unranked**. Both 2026-09-23 evidence items are now
documented on the candidate: the interrupted old-hash fragment (config hash
`5b760871ce84`, runner SHA `0d384a593830`, 2 sanity rows, commit `d656bcc` —
preserved per `artifacts/bonsai2-ptq1-interrupted-20260923.md`) and this fresh
current-hash native gate (7/7) plus bounded canary (2/6). The config's first
`known_gaps` entry was updated to carry both and the config is otherwise
unchanged; because that entry is part of the hashed config, future runs will
carry a new config hash — the 2026-09-23 hashes above refer to the
byte-identical pre-edit config this run gated. A full 25-row battery remains
the only path to ranking and is not justified by this evidence alone.
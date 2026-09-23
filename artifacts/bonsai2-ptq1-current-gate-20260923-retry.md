# Bonsai 2 PTQ1_0 — bounded admission gate retry (corrected context sizing) + one-trial canary (2026-09-23)

**Status: still ADMITTED as a gated / UNRANKED bounded baseline.** A fresh,
bounded native-gate run under the current config hash `7e3130a235b9` first
failed **only** on the context near-boundary check (context-sizing helper
under-filled the prompt), then a corrected retry with long-sample tokenizer
sizing passed all 7/7 native checks against the pinned Prism fork runtime and
the staged PTQ1_0 artifact on 2026-09-23. The six-task one-trial canary
completed with 2 pass / 4 model/output-budget errors. This is **admission
capability evidence only** — NOT a quality or ranking result. No full 25-row
battery ran, no leaderboard/ranking entry exists, and no rows were appended to
`results/log.jsonl`. The candidate remains gated / unranked.

## Scope / boundary

- Bounded native gate (7 fresh native checks, all re-run in the corrected
  retry) + fixed six-task one-trial canary only. **No full 25-row run**, **no
  leaderboard/ranking**, **no `results/log.jsonl` rows**, no transcripts, no
  config snapshot, no speed-gate row, no coding suites. The canary carries no
  benchmark-row schema and confers no rank.
- Two gate attempts ran under the same config hash on 2026-09-23; both are
  recorded in the External raw evidence below. No attempt crashed the engine.
- This report only records the resulting external evidence; the owned server
  was torn down after the canary (see Teardown) and benchmark ports are free.

## Immutable model / artifact / runtime provenance

| Item | Value |
|---|---|
| Model id | `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0` (GGUF PTQ1_0 ternary, 1.75 bpw, single file) |
| HF repo revision (immutable pin) | `6ed5e12bf84b7a63069882c91dd9e9218647d17b` |
| Artifact file | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` |
| Artifact bytes | 5,946,648,928 |
| Artifact sha256 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` (recorded by preflight/gate; not re-computed this session) |
| Engine | llama.cpp-prism — Prism fork of llama.cpp, runtime source commit `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6` |
| Local binary | `/Users/tijs/.local/share/local-model-bench/prism-llama-5d80cff/build/bin/llama-server` |
| Served model id | `bench-7e3130a235b9` (served via `--alias`; every gate check and canary trial echoed this id) |
| Endpoint | `http://127.0.0.1:8017/v1`, ctx-size 65536, parallel 1, flash-attn, prompt cache on |
| Context cap used | 65536 (harness ceiling; model native 262144 per server health meta) |

## Config hash and served alias

- Config file (unchanged, not edited): `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`.
- Full config SHA-256: `7e3130a235b9420a71385ea4e9168dd3367ebc32b327731f947af5125b4d6a5a`.
- Short config hash (runner algorithm, first 12 hex): **`7e3130a235b9`**.
- Canonical served id: **`bench-7e3130a235b9`** — no alias discrepancy.
- Committed HEAD at run and report time: `e0d37d0c8d52312a9785fcf3e673ca39c65e38a1`
  (the canary records runner git sha `e0d37d0c8d52` for the same commit).

## Preflight / teardown

- **Preflight (first attempt, `prism-20260923T132010Z-current-7e3130a235b9`)**:
  free disk **12,959,064,064 bytes / 12.069068908691406 GiB**; git tree clean
  at HEAD `e0d37d0c…e38a1`; `matching_processes_before: []`,
  `ports_before: []` (no processes/listeners). The retry run's own preflight
  re-checked the same gates (free disk 12,956,442,624 bytes / 12.0666… GiB,
  clean tree, no processes/listeners) before launching.
- **Teardown (retry run-summary)**: `matching_processes_after: []`,
  `ports_after: []` — no owned process or listener left; the server was
  stopped after the canary. The copied `server.log` is an archive, not a live
  listener.

## First gate attempt — failed ONLY the context near-boundary check

Attempt `prism-20260923T132010Z-current-7e3130a235b9` (same config hash, same
pinned binary/artifact): 6/7 checks passed
(`identity`, `plain_nonstream`, `plain_stream`, `tool_nonstream`,
`tool_stream`, `cache_reuse`), **no engine crash** (teardown clean). The
`context_near_boundary` check failed only because the context-sizing helper
used `probe_count` directly instead of long-sample tokenizer scaling:
`candidate_count: 32551`, `candidate_error: 32349`, `probe_count: 2`, no
`sample_count_1000`/`estimate_repeats` keys — the prompt under-filled to
**32,551 content / 32,602 prompt tokens** (passing `content_token_count` check
failed) after **407.3059 seconds**, `finish_reason=length`, no error text.

## Corrected retry — native gate 7/7 PASS (2026-09-23)

Retry `prism-20260923T132914Z-retry-context-7e3130a235b9` used the corrected
long-sample tokenizer sizing (`sample_count_1000: 1001`,
`estimate_repeats: 64835`, `target_content_tokens: 64900`). All probes against
`http://127.0.0.1:8017/v1`, model `bench-7e3130a235b9`. Raw evidence:
`native-gate.json` (see External raw evidence). Every check passed (`passes: 7,
fails: 0, errors: 0, passed: true`).

| # | Check | Measured result | Verdict |
|---|---|---|---|
| 1 | `/v1/models` exact identity | served id + alias exactly `bench-7e3130a235b9` (0.002 s) | PASS |
| 2 | Plain non-stream completion | 3.6339 s, content `READY`, `finish_reason=stop` | PASS |
| 3 | Plain streaming completion | 3.0676 s, 32 chunks, `STREAM_READY`, `finish_reason=stop`, 0 raw-line errors | PASS |
| 4 | Native required-tool non-stream | 8.7376 s, `lookup("Amsterdam")`, `finish_reason=tool_calls` | PASS |
| 5 | Native required-tool stream | 5.2024 s, 42 chunks, `lookup("Rotterdam")`, 0 raw-line errors | PASS |
| 6 | Cache reuse | 1st 6.6704 s, 2nd 4.1616 s with `cached_tokens=312` on recall (342-prompt-token conversation) | PASS |
| 7 | Context near-boundary | **64,900 content / 64,951 prompt / 64,952 total tokens**, 930.6137 s, `finish_reason=length`, no server crash | PASS |

## Canary — exact six-task shape and outcomes (2026-09-23)

`canary-2048-t2.jsonl` (8 rows: 1 run + 6 trials + 1 summary). Runner git sha
`e0d37d0c8d52` = HEAD at run time, endpoint `http://127.0.0.1:8017/v1`, model
`bench-7e3130a235b9`, fixed six-task suite, one trial per task,
`temperature=0`, `max_tokens=2048`, `max_turns=2`, `timeout=300s`, canary
version 0.1.0.

| Task | Outcome | Measured | Detail |
|---|---|---|---|
| `sanity-basic` | **PASS** | 3.4845 s | final `42`, `finish_reason=stop` |
| `hermes_ops-chaining` | error | 270.6893 s | `exceeded max_turns (2) without a final non-tool-call response` — web_search calls until turn cap |
| `hermes_ops-noisy-result` | error | 37.5617 s | same `max_turns` error — search_files/read_file calls until turn cap |
| `kiem_mini-feature` | error | 148.5313 s | `response truncated (finish_reason=length) before a final answer — max_tokens=2048 was likely too low` |
| `kiem_mini-testwrite` | error | 148.7437 s | same `truncated` error — reasoning stream hit the 2048 cap |
| `canary-multi-turn` | **PASS** | 17.886 s | scripted mid-conversation continuation, final `cache-reuse-ok` |

Summary row: `{"completed": true, "passed": 2, "failed": 0, "errors": 4,
"tasks_total": 6, "error": null}`. Determinism: identical (`differing_trials:
[]`, `identical: true`) for both passing tasks (`canary-multi-turn`,
`sanity-basic`); the four error tasks have no comparable non-error trials.

**Honest classification of the four errors — model / output-budget behavior,
not harness errors:** two `max_turns=2` errors (model kept emitting tool calls
without a final non-tool response within the turn cap) and two `max_tokens=2048`
truncation errors (reasoning stream exceeded the completion budget; the artifact
itself flags 2048 "was likely too low"). By design the canary exits with these
outcomes and appends **no benchmark rows and confers no rank** — reference
evidence for runner sizing, not a quality result.

## External raw evidence

Root: `/Users/tijs/.local/share/local-model-bench/results-mei/
Ternary-Bonsai-2-27B-PTQ1_0/` (disposable, outside the repo):

- **First (failed) attempt**: `prism-20260923T132010Z-current-7e3130a235b9/`
  — `preflight.json`, `native-gate.json` (6 pass / 1 fail on
  `context_near_boundary`), `run-summary.json`, `server.log`,
  `native_gate_supervisor.py`.
- **Corrected retry (passing)**: `prism-20260923T132914Z-retry-context-7e3130a235b9/`
  — `preflight.json`, `native-gate.json` (7/7 pass), `run-summary.json`
  (with canary summary, health, teardown), `server.log`, `native_gate_supervisor.py`,
  `canary-2048-t2.jsonl`, `canary.stdout.log`, `canary.stderr.log`.

Checksums computed this session (from the raw files):

| File | sha256 |
|---|---|
| retry `server.log` (also copied into this repo as `artifacts/bonsai2-ptq1-current-gate-20260923-retry-server.log`) | `db612ce691423f0cc9979a07f7c2970d54fe4e441443df0d7893ab8eb300a47a` |

Other hashes (config SHA-256, artifact SHA-256, retry run-summary
contents) are quoted from the raw JSON evidence files themselves and were not
independently re-computed this session; the raw paths above are authoritative.

## Results status — no rows appended

- `results/log.jsonl`: **no rows appended** by this gate/canary cycle or by
  this report.
- `results/LEADERBOARD.md`: **no PTQ1_0 entry / no leaderboard change**; no
  config snapshot, no speed-gate row, no coding-suite rows.
- The only repository changes from this cycle are the two artifact files
  referenced by this report; the external raw evidence was written outside the
  repo, append-only results were preserved untouched, and no commit was made.

## Decision and next action

- **Decision**: the candidate **remains gated / UNRANKED**, consistent with
  the 2026-09-19 bounded baseline. The corrected retry proves admission
  capability on the pinned Prism fork binary (`5d80cff`) + staged PTQ1_0
  artifact under the current config hash — but the canary's 2 pass / 4
  model/output-budget errors (max_turns and max_tokens limits) show this is
  **not** a quality/ranking result.
- **No 25-row battery is justified**: this bounded admission cycle adds no
  new capability signal beyond the already-established gated baseline, and
  running the full battery now would consume the benchmark queue without
  changing the gated/unranked status. Keep the candidate gated/unranked; no
  CoCore action was taken and none is triggered by this result.
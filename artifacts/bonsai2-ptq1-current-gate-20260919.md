# Bonsai 2 PTQ1_0 — fresh bounded admission gate + one-trial canary (2026-09-19)

**Status: ADMITTED as a gated / UNRANKED bounded baseline.** A fresh, bounded
native gate run (identity / plain+streaming / tool / cache) plus the fixed
six-task one-trial canary completed against the pinned Prism fork runtime and
the staged PTQ1_0 artifact on 2026-09-19. This is **admission capability
evidence only** — it is NOT a quality or ranking result. No full 25-row
battery ran, no leaderboard/ranking entry exists, and no rows were appended to
`results/log.jsonl`. The candidate remains gated / unranked.

## Scope / boundary

- Bounded native gate (6 checks) + fixed six-task one-trial canary only.
  **No full 25-row run** (sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3
  + kipclip_mini 4 + hearth_full 3), **no leaderboard/ranking**, **no
  `results/log.jsonl` rows**, no transcripts, no config snapshot, no
  speed-gate row. The canary carries no benchmark-row schema and confers no
  rank.
- The external `server.log.snapshot` is an **archive snapshot of the
  disposable probe server's log**, not a current listener — the server was
  torn down after the gate (see Teardown) and port 8017 is free.
- This task did not start/stop any server and did not re-run anything; it only
  inspected existing evidence, re-verified hashes, and wrote this report.
- **Context near-boundary is explicitly carried forward, not rerun** on this
  date: the 64,951-prompt-token measurement at the 65,536 harness ceiling
  (931.308 s) comes from the committed 2026-09-18 evidence
  (`artifacts/bonsai2-ptq1-native-gate-20260918.md` +
  `artifacts/bonsai2-ptq1-canonical-alias-recheck-20260918.md`), taken on the
  identical binary (`5d80cff`) and artifact (sha256
  `53107f53…fe33ee3`). See the gate table for the carried-forward row.

## Immutable model / artifact / runtime provenance

| Item | Value |
|---|---|
| Model id | `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0` (GGUF PTQ1_0 ternary, 1.75 bpw, single file) |
| HF repo revision (immutable pin) | `6ed5e12bf84b7a63069882c91dd9e9218647d17b` |
| Artifact file | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` |
| Artifact bytes | 5,946,648,928 (5.538 GiB) |
| Artifact sha256 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` (re-verified on-disk this session) |
| Runtime | PrismML-Eng/llama.cpp fork, source commit `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6` (MIT) |
| Local binary | `/Users/tijs/.local/share/local-model-bench/prism-llama-5d80cff/build/bin/llama-server` — `--version` 0.2.0-dev, build 1, commit 5d80cff (local Metal source build) |
| Server load line (from log snapshot) | `load_model: loading model '.../models--prism-ml--Ternary-Bonsai-2-27B-gguf/snapshots/6ed5e12bf84b7a63069882c91dd9e9218647d17b/Ternary-Bonsai-2-27B-PTQ1_0.gguf'` (one model load) |
| Listener line (from log snapshot) | `llama_server: listening on http://127.0.0.1:8017` |
| Context cap used | 65536 (harness ceiling; model native 262144 per card) |

## Config hash and served alias

- Config file (unchanged, not edited): `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`.
- Full sha256 (re-verified this session):
  `04cfe963d51ea5d213ecc5eb33083ade60b582d5939553b917cb3fd4adc01bcd`.
- Short config hash (runner algorithm, first 12 hex): **`04cfe963d51e`**.
- Canonical served id: **`bench-04cfe963d51e`** — every gate check and every
  canary trial echoed exactly this id. Unlike the 2026-09-18 run, the served
  alias equals the runner-canonical `bench-<config_hash>` (no discrepancy).
- Committed HEAD before this report was written: `d1dfce9f4fb66c3370aae579df8da57e546a62a6`
  (the canary records runner git sha `d1dfce9f4fb6` for the same commit).

## Preflight / teardown

- **Single-writer**: checkout clean and no other writer active at report time;
  port 8017 is shared with every other llama.cpp config, and the probe server
  held the only backend during the gate.
- **Teardown (re-verified this session)**: `lsof -iTCP:8017 -sTCP:LISTEN` →
  no listener; `pgrep` → no runner/canary/`llama-server` process. The external
  log snapshot is an archive, not a live listener.

## Native gate checks (fresh measured results, 2026-09-19)

All probes against `http://127.0.0.1:8017/v1`, model `bench-04cfe963d51e`.
Raw evidence: `native-gate.json` (see External raw evidence). Every check passed.

| # | Check | Measured result | Verdict |
|---|---|---|---|
| 1 | `/v1/models` exact identity | served id + alias exactly `bench-04cfe963d51e` (elapsed 0.009 s) | PASS |
| 2 | Plain non-stream completion | **3.17 s**, content `READY`, `finish_reason=stop`, 0 tool calls | PASS |
| 3 | Plain streaming completion | **2.84 s**, 29 chunks, `STREAM_READY`, `finish_reason=stop`, 0 raw-line errors | PASS |
| 4 | Native required-tool non-stream | **8.12 s**, `tool_choice="required"`, `lookup("Amsterdam")`, no prose, `finish_reason=tool_calls` | PASS |
| 5 | Native required-tool stream | **4.11 s**, 26 chunks, `lookup("Rotterdam")`, no raw-line errors | PASS |
| 6 | Cache reuse | 1st call 6.51 s, 2nd call **2.99 s** with `prompt_tokens_details.cached_tokens=304` on recall (324-prompt-token conversation) | PASS |
| 7 | Context near-boundary | **carried forward, not rerun** — see below | PASS (carried) |

**Context near-boundary (carried forward, explicit):** the 64,951-prompt-token
completion at the 65,536 cap, 931.308 s wall, `max_tokens=1`,
`finish_reason=length`, no server crash — taken 2026-09-18 on the identical
binary (`5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6`) and identical artifact
(sha256 `53107f53…fe33ee3`), already in the committed gate evidence:

- `artifacts/bonsai2-ptq1-native-gate-20260918.md`
- `artifacts/bonsai2-ptq1-canonical-alias-recheck-20260918.md`

It was **not** re-run in this cycle (bounded budget); it is recorded in the
gate JSON as `status: carried_forward`, `pass: true`.

## Canary — exact six-task shape and outcomes (2026-09-19)

`canary.jsonl` (8 rows: 1 run + 6 trials + 1 summary). Runner git sha
`d1dfce9f4fb6` = HEAD at run time, endpoint `http://127.0.0.1:8017/v1`, model
`bench-04cfe963d51e`, **fixed six-task suite, one trial per task**,
`temperature=0`, `max_tokens=2048`, `max_turns=2`, `timeout=180s`, canary
version 0.1.0. Ran 17:59:37Z → 18:09:40Z (≈10.1 min wall).

| Task | Outcome | Measured | Detail |
|---|---|---|---|
| `sanity-basic` | **PASS** | 2.92 s | final `42`, `finish_reason=stop` |
| `hermes_ops-chaining` | error | 180.00 s | `request timed out after 180s` (`error_kind=timeout`) — no response within the 180 s budget |
| `hermes_ops-noisy-result` | error | 105.80 s | `exceeded max_turns (2) without a final non-tool-call response` — tool calls until turn cap, `finish_reason=tool_calls` |
| `kiem_mini-feature` | error | 148.31 s | `response truncated (finish_reason=length) before a final answer — max_tokens=2048 was likely too low` |
| `kiem_mini-testwrite` | error | 148.54 s | same `truncated` error — reasoning stream hit the 2048 cap |
| `canary-multi-turn` | **PASS** | 17.83 s | scripted mid-conversation continuation, final `cache-reuse-ok` |

Summary row: `{"completed": true, "passed": 2, "failed": 0, "errors": 4,
"tasks_total": 6, "error": null}`.

**Honest classification of the four errors — model / slow-budget behavior, not
harness errors:** the timeout shows the model did not finish within 180 s; the
`max_turns` error shows the model kept emitting tool calls without a final
non-tool response within two turns (slow, deliberative behavior); the two
`truncated` errors show the model's reasoning stream exceeded the canary's
2048-completion-token budget before a final answer, and the artifact itself
flags that 2048 "was likely too low" for this reasoning-emitting family (the
benchmark config defensively uses `hermes_ops_max_tokens: 16384`). By design
the canary exits with these outcomes and appends **no benchmark rows and
confers no rank** — this is exploratory evidence for runner sizing, not a
quality result.

## External raw evidence

Root: `/Users/tijs/.local/share/local-model-bench/results-mei/
Ternary-Bonsai-2-27B-PTQ1_0/prism-20260919T-current-04cfe963d51e/`
(disposable, outside the repo):

| File | sha256 |
|---|---|
| `native-gate.json` | `b99fad65f6335398830893e8bdff3a12c2d055c921cfa9375dc4fe846803ebf4` |
| `canary.jsonl` | `5509651844cd4708ed2bcbbaf33f8cf6b1b9eca0de3c96b1cd2140b19529910e` |
| `server.log.snapshot` | `c84f2370e9d1fab130b0f3f8c7030d9cab883523c94a1dfcc461f5392ffd8083` |

All three hashes re-verified on-disk this session and matching the run record.
Config `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml` sha256
`04cfe963d51ea5d213ecc5eb33083ade60b582d5939553b917cb3fd4adc01bcd` re-verified
this session (unchanged).

## Results status — no rows appended

- `results/log.jsonl`: **zero exact PTQ1_0 rows** (verified this session); no
  row was appended by this gate/canary or by this report.
- `results/LEADERBOARD.md`: **no PTQ1_0 entry** (verified this session).
- The only change in this cycle is this report file; nothing else was
  modified, no configs were edited, no servers were launched or stopped.

## Decision and next action

- **Decision**: **ADMITTED as a gated / UNRANKED bounded baseline.** The fresh
  gate passes on the pinned Prism fork binary + staged PTQ1_0 artifact
  (commit `5d80cff`), proving admission capability; the canary's
  model/slow-budget outcomes (2 pass / 4 model-behavior errors) are recorded
  as reference evidence for runner sizing (max_tokens/max_turns/timeout),
  **not** as a quality or ranking result. Full benchmark completion still
  requires the complete 25-row battery with zero harness errors and reviewed
  partial rows.
- **Next action**: **keep gated / unranked.** Do **not** launch Gravity and do
  **not** launch the Bonsai MLX/Mei candidate in this cycle. The candidate
  stays as the bounded next baseline pending the serialized queue review.
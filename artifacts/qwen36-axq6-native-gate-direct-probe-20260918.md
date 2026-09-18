# AXQ6 Native Gate: Direct Probe Result — plain_completion timeout (BLOCKED), 2026-09-18

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**Config hash:** `f0c165be1ebe` — the final committed config used for this direct run
**Pinned Mei source:** `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` (Mei tag v0.5.0 baseline)
**Local vmlx fix identity:** `15bada58953b5f830d1b52f40850b695b87efdf8` (vmlx-swift type-check fix, pinned as local PATH dependency per the typecheck-fix artifact `artifacts/qwen36-axq6-native-gate-typecheck-fix-20260918.md`)

## Verdict: BLOCKED — slow/model admission blocker

This is a **slow/model admission blocker**, not a benchmark row and not a
harness result. The direct native-gate probe (built to isolate admission
evidence from the budget-heavy cache/context stages) **failed**: `plain_completion`
timed out after **3600.030 s**, so the overall probe status is **failed** and the
acceptance battery, coding battery, and any successor-model work **must not
start**.

- **No AXQ6 rows exist:** results/log.jsonl holds **0 rows** for
  `f0c165be1ebe` and for all prior pre-gate hashes (`703118869d87`,
  `942fd0c767d0`, `11c43b26cb6b`); leaderboard has no AXQ6 references.
- No coding battery or successor model may start until the admission blocker
  is resolved with a real passed gate.

## Direct probe output (external evidence — authoritative)

`/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260918T120000Z-direct/probe.json`

Overall `status: "failed"`. Per-stage results:

| Stage | Status | Detail |
|---|---|---|
| models_identity (exact identity) | passed | served id `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP` |
| mei_status | passed | model loaded, listening on 8025 |
| parity_stream_vs_nonstream | passed | content `parity-ok` |
| native non-streaming tool call | passed | `add_numbers(15, 27)` via `finish_reason: tool_calls` |
| native streaming tool call | passed | `add_numbers(15, 27)` assembled stream, `finish_reason: tool_calls` |
| plain_completion | **failed** | `elapsed_seconds 3600.030347666994`, `TimeoutError: timed out` |

Cache/context stages were **explicitly skipped** in this direct run (probe
invoked with `--skip-cache --skip-context`); the probe key list contains only
the six stages above — no cache or context stage.

## Load / memory / latency facts (recorded from probe.json)

- Active memory after load: **24,401,171,724 bytes** under the
  **30,000,000,000-byte** limit (probe-time active reported
  `24401171740` bytes; load-time line was `active 24401171724`, matching the
  typecheck-fix artifact's server load evidence).
- Peak request memory: **25,568,486,742 bytes** (`mei_memory_peak_bytes`),
  consistent across parity and tool stages.
- Tool non-streaming request took **968.1908 s** (`request_seconds
  968.190760`, elapsed 968.1956) for a 293-token prefill + 109-token
  completion with `generate_ms 11477` and `tokens_per_second 9.50` — i.e.
  functional native tool calls but extremely slow decode for a 24.4 GB 6-bit
  MoE, consistent with the dense-27B speed-gate evidence in this repo.

## Archived server snapshot (archived after teardown)

`/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260918T120000Z-direct/server.log.snapshot`

- **sha256:** `e37e0322f0b7713aa99d7d2630f3986e1ef2945c8da450c65c60cabfab654dd5`
- **Size:** 2,527,717 bytes
- **Lines:** 48,562
- Companion sidecar `server.log.snapshot.json` (579 bytes) present in the same
  direct run directory.

## Teardown (verified for this note)

- PID **47984** stopped — `ps -p 47984` reports no such process.
- `server.pid` **absent** for this run / no Mei AXQ6 server pid on disk.
- Port **8025 free** — `lsof -nP -iTCP:8025 -sTCP:LISTEN` returns nothing.
- No AXQ6 probe/runner remained — `pgrep -fl 'mei|probe_mei|run_bench'`
  returns nothing.

## Status of this record

The direct-probe output is **external evidence** (lives under
`~/.local/share/local-model-bench/`, outside this repo). This artifact is a
**review record only — it is not a pass**. The native admission gate remains
unpassed; the AXQ6 candidate stays blocked and no benchmark work may begin.
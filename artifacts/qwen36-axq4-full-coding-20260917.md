# AutomatosX AXQ 4-bit — full 25-row Mei benchmark run, 2026-09-17

ONE full current-methodology battery for
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` @
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24` (Mei 0.5.0 prebuilt binary, vmlx
`44461ffd`). Kiem plan 7f5c67e7 todo 19 (AXQ 4-bit). Native gate PASSED first
(12/12 — see `artifacts/qwen36-axq4-native-gate-20260917.md`); this run then
executed the default four coding suites.

## Command and provenance

```
uv run --locked python runner/run_bench.py --config configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/mei.yaml
```

- config_hash `984425a7e143` (immutable snapshot: `results/configs/984425a7e143.yaml`,
  byte-identical to the committed config)
- runner_git_sha `48e4bbe5c88c` (clean; the config/setup commit) on every row
- served/requested model id: `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`
  (exact; identity gate passed against a stale-bind-free port 8024)
- Server: launch line + controls identical to the gate (see gate note);
  benchmark server stdout archived at
  `artifacts/qwen36-axq4-bench-server-20260917.log` (wrapper launch line +
  "mlx.metallib already present" + mei load/listen lines; benchmark segment of
  `mei-runtime/logs/server.log` lines 48509-48522: memory after load active
  20,536,358,156 / limit 30 GB, listening max-tokens 8192, 3/6 unaligned
  WARNING, prefix cache disk-backed at kv-axq4-mtp).

## Result: 25 rows, 21 pass, 4 fail, 0 harness errors

All 25 rows: config_hash `984425a7e143`, runner_sha `48e4bbe5c88c`,
harness_error false. Append-only `results/log.jsonl` grew 4120 -> 4145 rows
(+25, exactly this run). LEADERBOARD rebuilt from 4145 rows — AXQ group ranked
12 of 20 groups, PASS 88% head row, suite table added. No speed-gate entry
(results/speed_gate.jsonl untouched; hermes_ops avg 5.9 tok/s > 4.0).

| Suite | Shape | Pass |
| --- | --- | --- |
| sanity | 2 | 2/2 |
| hermes_ops | 8 | 7/8 |
| kiem_mini | 5 | 3/5 |
| hearth_mini | 3 | 3/3 |
| kipclip_mini | 4 | 4/4 |
| hearth_full | 3 | 2/3 |
| **Total** | **25** | **21/25 (84%)** |

Genuine task failures (all harness_error=false, i.e. model/harness-task
outcomes, not infrastructure errors):
- hermes_ops-multi-step-chain — FAIL (1.7 min, 12.3 tok/s)
- kiem_mini-feature — FAIL (7.7 min)
- kiem_mini-testwrite — FAIL (4.1 min)
- hearth_full-feature — FAIL (4.3 min)

hermes_ops tokens/s per task: 1.7 / 3.7 / 8.3 / 4.3 / 4.5 / 12.3 / 6.6 / 5.8
(avg 5.9); sanity tps 42.4 / 35.9. Coding rows do not carry tokens_per_second
(suite convention). Wall per task ran 0.1-7.7 min; total battery wall ~77 min
plus ~7 min hermes_ops/sanity and ~3.4 min for context-cap probes (gate).

Transcripts (all 15 coding tasks, hermes-driven):
`results/transcripts/{kiem_mini,hearth_mini,kipclip_mini,hearth_full}/*/*.log`
(fixture-suite spelling `AutomatosX_AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`).

## Teardown / listener evidence

- `runner/stop_mei_server.sh` (run_bench.py run_one finally):
  `Stopped isolated Mei PID 95192.`
- Post-run: `lsof -nP -iTCP:8024 -iTCP:8012,... -sTCP:LISTEN` → no listeners
  (lsof exit 1); `mei-runtime/server.pid` gone; no mei/run_bench/run_fixture
  processes remain.
- No second server was ever started; the runner owned launch/health/teardown.

## Notes / honest classification

- Sanity-block access: runner's own plain-completion probe passed via
  reasoning_content; sanity suite 2/2.
- Speed gate did NOT trip (avg 5.9 > 4.0) so the 15-row coding battery ran to
  completion; no speed_gate.jsonl entry.
- kiem_mini-feature shortened to 7.7 min (its own suite timeout applies in the
  harness); every row recorded.
- Scope caveat (as in config): TEXT/TOOL path only. Vision conditioning and
  the MTP path (mtp.safetensors) were NOT benchmarked. AXQuant calibration is
  development evidence (manifest calibration null); local gate/run numbers are
  the only local evidence.
- NEXT LEG: AXQ 6-bit (todo 20) remains QUEUED and was NOT started; gated
  Gravity also not started. Do not launch either from this unit.
# Qwen3.6 mixed 4/6 native-gate attempt — context-boundary crash, 2026-09-14

Candidate `EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit` (mixed 4/6 quant:
down/up/gate half at 6-bit, all attention 6-bit, embed 5-bit, group 64), served
from the **aligned** repack dir `mei-models/Qwen3.6-35B-A3B-mixed46-aligned`
(4/4 shards realigned, 2–3 bytes header padding per shard, tensor payload
sha256 unchanged — see `configs/Qwen3.6-35B-A3B-mixed46/mei.yaml` header).
Config exists for this lane but the gate ran the **safe** control set, which
differs from the config's pinned launcher (see below).

**Gate evidence only. This candidate is NOT ranked. NO `results/log.jsonl` rows
were appended by this gate (the 25 existing mixed-4bit rows are the 2026-09-13
DWQ legs, config `4f91b7aee214`), and no leaderboard change belongs to it.**

## Provenance (as-run)

- Mei source worktree `/tmp/mei-v050-qwen36-research` @
  `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` == tag `v0.5.0`, vmlx
  `44461ffd` (`mei_source_commit` / `mei_commit` in the mei.yaml).
- Build: `mei-build-qwen36-mixed46-050/release/mei` (release scratch build,
  mlx Python wheel 0.31.1 metallib).
- Port 8024, endpoint `http://127.0.0.1:8024/v1`, `--context-cap 65536`,
  `--kv-cache-dir mei-runtime/kv-mixed46-safe`, request log
  `/tmp/qwen36-mixed46-safe-requests.jsonl`.

Exact launch line (verbatim first line of `/tmp/qwen36-mixed46-safe-server.log`):

```
mei isolated launch: /Users/tijs/.local/share/local-model-bench/mei-build-qwen36-mixed46-050/release/mei --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-mixed46-aligned --served-model-id EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit --host 127.0.0.1 --port 8024 --context-cap 65536 --temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true --cache-reuse true --max-tokens 4096 --prefill-step-size 1024 --kv-cache-dir /Users/tijs/.local/share/local-model-bench/mei-runtime/kv-mixed46-safe --memory-limit-bytes 30000000000 --compiled-decode false --load-mmap true --request-log /tmp/qwen36-mixed46-safe-requests.jsonl --log-requests true
```

Safe controls, all verified in the launch line: `VMLX_ENABLE_UNSAFE_COMPILE=0`,
`--compiled-decode false`, `--load-mmap true`, `--memory-limit-bytes
30000000000`, `--prefill-step-size 1024`, `--max-tokens 4096`. Note: the
config's own `benchmark_launch_command` still pins `VMLX_ENABLE_UNSAFE_COMPILE=1`
without `--compiled-decode`; this gate deliberately ran the safe C1 operating
point (`--load-mmap true` is fine here because the -aligned dir needs no
realignment). Reconcile that divergence before any coding run.

## Pass/fail matrix (from `artifacts/qwen36-mixed46-native-gate-20260914.json`)

| Probe | Status | Evidence |
|---|---|---|
| models_identity | **PASS** | served_ids `[EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit]` |
| plain_completion | **PASS** | content `ready`, 132 completion tokens, ~48.1 tps |
| parity_stream_vs_nonstream | **PASS** | `parity-ok`, 174/174 completion tokens on both paths, ~48.0–48.2 tps |
| tool_nonstreaming (`add_numbers`) | **PASS** | finish_reason `tool_calls`, args `{"a":15,"b":27}`, validated |
| tool_streaming (`add_numbers`) | **PASS** | same assembled call, same usage 196 tokens |
| cache_growing_turn1 | **PASS** | prompt 790, cached 785 |
| cache_growing_turn2_reuses_slot | **PASS** | prompt 809, cached 804 |
| cache_repeat_1 (6170-token prefix) | **PASS** | cached 6165/6170, ~61.7k prompt tps on reuse |
| cache_repeat_2 | **PASS** | cached 6165/6170 |
| mei_status (memory) | **PASS** | active 20.01 GB, cache 3.40 GB, peak 21.90 GB; limit 30 GB, cache-limit 32.64 GB |
| context_exact_cap (65536) | **FAIL** | `RemoteDisconnected: Remote end closed connection without response` after 119.78 s |
| context_over_cap_rejected | **FAIL (not meaningful)** | `Connection refused` (Errno 61) — server had already crashed |

All PASS probes also confirmed in the per-request log
(`/tmp/qwen36-mixed46-safe-requests.jsonl`, cache_hit chain 0 → 6165/6165 →
785 → 804).

## Failure evidence (context boundary)

The 65536-token boundary request killed the server mid-prefill. Request log has
**no** entry for it — the process died before completing the request:

- Gate JSON: `context_exact_cap` `error: RemoteDisconnected`, elapsed 119.78 s.
- Wrapper log `/tmp/qwen36-mixed46-safe-server.log` ends:
  `start_mei_server.sh: line 236: 30768 Trace/BPT trap: 5`.
- Runtime `mei-runtime/logs/server.log` (actual Swift fatal): `pp stage=prefill`
  climbs to `completed=44032 total=65536`, then
  `MLX/ErrorHandler.swift:343: Fatal error: [METAL] Command buffer execution
  failed: Insufficient Memory (00000008:***)` at
  `vmlx-swift/Source/Cmlx/mlx/mlx/backend/metal/eval.cpp:51` (build
  `mei-build-qwen36-mixed46-050`).
- With the server dead, `context_over_cap_rejected` could only observe
  `Connection refused` — over-cap rejection behavior was **not** exercised.

## Classification

**Model/runtime context-boundary blocker** — the serving binary exhausts Metal
memory while prefilling the 64K-boundary prompt under the 30 GB memory limit on
this 32 GB machine (cf. the sibling OptiQ `Insufficient Memory` trap). Not a
`harness_error` (every other probe, including memory reporting, passed clean),
and not a coding result (no coding suite was run and none can be until the
boundary is fixed). Nothing was appended and no leaderboard change belongs to
this gate.

## Next action

**Explicitly defer the full coding gate.** Diagnose the 64K-prefill Metal OOM
first: e.g. confirm the KV-cache growth path at long prefill (cache-limit
32.64 GB vs memory-limit 30 GB vs ~20 GB active weights on 32 GB device),
test a lower boundary (e.g. 32768/49152) to locate the crash threshold, and
check whether a smaller `--prefill-step-size` or a tighter context-cap avoids
the allocation spike. Only after the context boundary is understood should the
mixed46 lane get a coding run — and that run must reconcile the config's
`VMLX_ENABLE_UNSAFE_COMPILE=1` launcher against this gate's safe controls
first.
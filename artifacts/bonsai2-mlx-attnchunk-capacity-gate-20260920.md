# Bonsai 2 MLX — feature-on attnchunk-64 capacity gate — 2026-09-20

## Verdict

The feature-on operating point (`VMLX_QWEN35_FA_CHUNK=64` +
`VMLX_BONSAI_PRISM_HADAMARD=1`, fresh release binary built against vmlx
`f9fb21c0`, aligned diagnostic model) loaded and passed the full functional
admission surface — **10 of 12 probe slots passed** — but the exact
36,864-token context-cap request failed again: the client observed
`RemoteDisconnected` after **318.51 s**, and the server never served another
request (the 36,865 over-cap rejection check hit connection refused).

This is the same capacity boundary the previous gates failed at (unaligned run:
35,840-token failure; aligned feature-off run: Metal "Insufficient Memory"
fatal at exact 36,864 after 407.57 s). **No credible capacity improvement is
measured: the exact 36,864 boundary still fails, roughly 89 s earlier than the
aligned feature-off run.** The candidate stays **gated/unranked**; no
`results/log.jsonl` rows, leaderboard or benchmark config changes were made.

## Exact operating point

- Source pins: Mei `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` (throwaway,
  manifest → local path dependency `vmlx-swift`), vmlx
  `f9fb21c0274083612887e4c7d8b3fe07743141fa` (branch
  `vmlx-swift-bonsai-attnchunk`, submodules mlx @ `73312d3e…`, mlx-c @
  `7bede8f1…`). Build gate: local-model-bench commit
  `ec14647943ee58e7376322078e4b9be31b9733bf`.
- Binary: `/Users/tijs/.local/share/local-model-bench/mei-runtime-bonsai2-attnchunk-20260920/launch/mei`,
  SHA-256 `271e9a949f2785f1213e6655c07d9178db5b2039eebc7f181b6358dc884cc780`
  (89,421,136 B; byte-copy of the build-gate artifact
  `mei-release-arm64-bin`). Metallib made reachable by colocating
  `mlx.metallib`+`default.metallib` (SHA-256
  `ac03ae43…252741`, 3,154,810 B) with the binary — the first fallback of
  MLX's `load_default_library`. Confirmed loaded: log shows model load and
  Metal context active (no metallib failure).
- Model: aligned diagnostic copy
  `…/mei-models/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919`
  (`model.safetensors` 8,595,477,992 B; SHA-256
  `d33e7fb7…02cb055`). Source pack untouched (recorded SHA-256
  `130de592…9f269ed`). `load-mmap true` accepted: log confirms
  `mmap=true`.
- Serve flags: `--served-model-id prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919-attnchunk64-cap36864`,
  `--host 127.0.0.1 --port 8027 --context-cap 36864 --prefill-step-size 1024`,
  `--temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true`,
  `--cache-reuse true --max-tokens 4096`,
  `--kv-cache-dir …/mei-runtime-bonsai2-attnchunk-20260920/kv-cache` (fresh,
  empty at launch), `--compiled-decode false` (explicit), `--load-mmap true`.
- Env: `VMLX_BONSAI_PRISM_HADAMARD=1 VMLX_QWEN35_FA_CHUNK=64
  VMLX_ENABLE_UNSAFE_COMPILE=0`.

## Resource gate (pre-launch recheck, 2026-09-20T11:53Z)

| Check | Result |
|---|---|
| Free disk | 17,205,304 KiB (~16.4 GiB) ≥ 10 GiB |
| Matching Mei/probe/runner process | none |
| Port 8027 | free |

## Probe results (runner/probe_mei.py, --context-cap 36864 --timeout 1800)

Passed (10/10 functional slots):

- `models_identity` — exact served ID present
- `mei_status` — status ok; device applegpu_g13s 34.36 GB; limit
  24,051,816,857 B; load-time active 9,494,405,628 B
- `plain_completion` — "ready"
- `tool_nonstreaming` — validated `add_numbers({"a":15,"b":27})`,
  finish_reason tool_calls
- `tool_streaming` — same native call, assembled from stream
- `parity_stream_vs_nonstream` — "parity-ok", identical usage
- `cache_repeat_1` / `cache_repeat_2` — 6,207 cached of 6,212 prompt tokens
- `cache_growing_turn1` / `cache_growing_turn2_reuses_slot` — 823 cached of
  851 prompt tokens

Failed (2/12):

- `context_exact_cap` — **318.51 s**, `RemoteDisconnected: Remote
  end closed connection without response` (no response, no usage)
- `context_over_cap_rejected` — connection refused (server already gone);
  rejection behavior **not evaluated**

## Context boundary versus prior comparison points

| Run | Boundary | Outcome |
|---|---|---|
| Previous unaligned gate (feature-off) | 35,840 tokens | Metal OOM failure |
| Previous aligned gate (feature-off, 6a81 binary) | exact 36,864 | Metal "Insufficient Memory" fatal after 407.57 s; server exit -5 |
| This feature-on gate (attnchunk-64, f9fb21c0 binary) | exact 36,864 | RemoteDisconnected after 318.51 s; server exit -15 |

Boundary shift: **none measurable**. The feature-on point fails at the same
exact 36,864 cap, earlier than the aligned feature-off run — so it cannot even
claim to have moved capacity from the 35,840 failure point. The planned
"single extra higher-boundary request" was deliberately not taken: the exact
comparison 36,864-vs-35,840 is already answered (still failing at the higher
boundary), and the server was not healthy after the boundary failure.

## Memory and throughput

- Active/peak (engine-reported, from probe usage and /v1/mei/status):
  peak **14,182,689,312 B** (~14.18 GB), max active **12,443,607,556 B**, max
  cache **13,409,405,408 B**; allocator limit 24,051,816,857 B (~22.4 GiB);
  device 34,359,736,832 B. On-disk KV suffix after run: 1.9 GB; last KV write
  12:01:38Z = start of the exact-cap request (no post-failure growth).
- Decode: 15.25–16.46 tokens/s (same band as the aligned feature-off gate).
- Prefill: 93.1 tokens/s on the 6,212-token cache prompt; 18,076 tok/s on the
  fully-cached repeat (6207 cached).
- Streaming tool TTFT (client): 4.58 s.
- During the run the server was sampled at ~12–38% CPU with the listener up;
  after the boundary failure the listener was gone, the process lingered
  ~4 min, then exited.

## Server exit mechanics (evidence, recorded honestly)

- Server PID 44991, uptime 1,109 s, **exit code -15 (SIGTERM)**. Probe exit
  code **1** (`PROBE_EXIT=1`).
- Unlike the aligned gate, no Metal `Insufficient Memory` fatal line was
  captured this run: the server stdout/stderr was not redirected to a file
  (the session capture holds only the 10 startup lines). The failure point is
  the preserved evidence: connection dropped mid exact-36,864 request at
  318.51 s with no response; over-cap probe 0.36 s later got connection
  refused; no KV-cache writes after request start; no new crash report in
  `~/Library/Logs/DiagnosticReports`; no macOS memory-pressure/jetsam kill,
  no GPU reset, and no harness/gateway kill recorded in unified-log or
  `~/.hermes/logs` windows around the exit. The request failure at the exact
  cap is classified as **model/runtime memory capacity**, consistent with both
  prior gates at this boundary, and is **not** a harness failure.

## Teardown

- Port 8027 free; no matching Mei/probe/runner process; no orphaned
  descendants (`process_manage` session list empty, no mei children).
- Free disk after: 15.2 GiB.

## Raw evidence

`/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-mlx-2bit/attnchunk64-featureon-20260920T115205Z-cap36864/`
(launch.sh, server.log, command.txt, hashes.txt, probe.json, teardown.txt,
run-summary.json).

## Conclusion and remaining steps

**No credible improvement.** The feature-on attnchunk-64 operating point did
not move the exact-context capacity boundary at 36,864 on this 32 GiB device;
if anything it failed faster than the aligned feature-off run. The candidate
pack and binary remain gated/unranked. Remaining gate (unchanged from the
aligned run): a larger-device validation or a separately designed,
source-reviewed cache-memory remedy is required before any exact-cap claim for
Bonsai 2 MLX at 36,864; the character of the boundary failure (Metal
eye-memory exhaustion during the full-cap prefill) is unchanged.

## Scope preservation

- `/Users/tijs/projects/mei` main: untouched (HEAD `950e8c2f`, only the
  pre-existing user-owned untracked `Casks/` and `tap/` remain).
- `/Users/tijs/projects/vmlx-swift-bonsai-attnchunk` worktree: untouched.
- Source model pack, configs, Kiem, GitHub, CoCore, leaderboard: untouched.
- Benchmark repo change: this file only.
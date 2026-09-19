# Bonsai 2 MLX / Mei aligned scratch admission gate — 2026-09-19

## Verdict

The payload-preserving aligned scratch copy **loaded successfully** through the
isolated Prism-Hadamard Mei/vMLX path and passed the functional admission surface:
exact model identity, plain completion, streaming/non-streaming parity, native
streaming and non-streaming tool calls, and growing/repeated cache reuse. The
bounded probe recorded **10 of 12 probe slots passed**.

The exact context-cap request at the deliberately bounded `36,864` tokens then
caused Mei to exit with a Metal `Insufficient Memory` fatal error. The client saw
`RemoteDisconnected`; the subsequent `36,865` over-cap rejection check could not
run because the server was gone. This is a **model/runtime memory-capacity
blocker**, not a harness or HTTP-protocol result. The candidate remains
**gated/unranked**. No `results/log.jsonl` rows, benchmark config, or leaderboard
entry were created.

This run does not establish that the aligned repack moved the capacity boundary:
the current server log does not expose a completed-token progress line for this
request, and the prior unaligned run failed in the same general boundary window.

## Exact operating point

- Pinned model source revision: `3f926b415992eaa2ae9dd7b573706494d6bbf787`.
- Source model directory remained untouched:
  `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit`.
- Diagnostic aligned directory:
  `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919`.
- Alignment manifest: the source payload is byte-identical; the 2-byte header
  padding produced `unaligned_after: 0` for all 2,390 tensors.
- Isolated runtime source: `vmlx-swift-bonsai-prism@6a81ca32656fc2dc824c589f88e7d5541158c224`.
- Served binary SHA-256:
  `8db9bc79a65d9665579fdfc20c293a0e44789940630251aa89d5a28798a74a70`.
- Safe controls: `VMLX_BONSAI_PRISM_HADAMARD=1`,
  `VMLX_ENABLE_UNSAFE_COMPILE=0`, `--compiled-decode false`, prefill step
  `1024`, `--load-mmap true`, disk-backed KV cache, context cap `36864`.
- Served identity:
  `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919`.
- Endpoint: `127.0.0.1:8027`.

The server log confirms 402 packed modules installed from 1,608 checkpoint keys,
model load completed, and the model was listening. It reported device memory
`34,359,738,368` bytes, memory limit `24,051,816,857` bytes, recommended working
set `26,800,603,136` bytes, and active memory after load `9,494,405,628` bytes.

## Probe results

Passed:

- `models_identity`
- `mei_status`
- `plain_completion` (`ready`)
- `parity_stream_vs_nonstream` (`parity-ok`)
- `tool_nonstreaming` — validated `add_numbers({"a":15,"b":27})`
- `tool_streaming` — validated the same native call
- `cache_growing_turn1`
- `cache_growing_turn2_reuses_slot` — 823 cached of 851 prompt tokens
- `cache_repeat_1`
- `cache_repeat_2` — 6,207 cached of 6,212 prompt tokens

Representative safe-path decode throughput was approximately 15.4–16.7
tokens/second. The largest recorded probe memory values were active
`12,443,607,556` bytes, cache `13,698,721,484` bytes, and peak
`15,493,473,364` bytes during the pre-context probes.

Failed:

- `context_exact_cap`: 407.570 seconds, `RemoteDisconnected`.
- `context_over_cap_rejected`: connection refused after the server crash; this
  is **not** evidence that the rejection behavior failed.

The archived server log ends with:

```text
MLX/ErrorHandler.swift:343: Fatal error: [METAL] Command buffer execution failed: Insufficient Memory (00000008:***) at /private/tmp/vmlx-swift/Source/Cmlx/mlx/mlx/backend/metal/eval.cpp:51
```

The server process exited with code `-5`; the probe exited with code `1` after
writing its complete JSON record.

## Lifecycle and evidence

- Probe JSON: `artifacts/bonsai2-mlx-aligned-gate-20260919T1200Z-cap36864/probe.json`
- Archived server log: `artifacts/bonsai2-mlx-aligned-gate-20260919T1200Z-cap36864/server.log`
- Exact launch/probe commands:
  `artifacts/bonsai2-mlx-aligned-gate-20260919T1200Z-cap36864/command.txt`
- Archived probe SHA-256:
  `70929be29d5a0f0dde5df30181ac2754d75ca49e3962f762cbdf5056d9651cd3`
- Archived server-log SHA-256:
  `60526912fc4b2a8f64fb709d04f686125f640b6539035a1ee5efdb744cfd8451`

Immediately after the crash and probe exit, port `8027` was free and no matching
Mei, `probe_mei.py`, `run_bench.py`, `llama-server`, or oMLX process remained. A
candidate search found zero matching lines in `results/log.jsonl` and zero in
`results/LEADERBOARD.md`.

A separate process appeared later, after this gate had terminated, and currently
occupies the same port: PID `55896`, launched by PID `55171` through
`start_mei_server.sh`, serving the **unaligned** source model with a separate
`mei-build-bonsai2-prism-6a81-cycle2` runtime and `context-cap 65536`. It is not
part of this archived gate. It was left untouched as an unowned/external workload;
no successor launch or teardown action was attempted against it.

## Boundary and next direction

- Do not run the coding battery, append benchmark rows, enable unsafe compile,
  or change shipped Mei defaults for this candidate.
- The aligned repack removes the measured unaligned-load condition, but this
  supervised load/capacity probe still does not prove exact-context capacity or
  a useful boundary improvement on this 32 GiB device.
- Keep the pinned MLX pack and aligned copy as gated/unranked evidence. The
  credible next path is a larger-device validation or a separately designed,
  source-reviewed architecture/cache-memory remedy. Do not repeat the same
  full admission probe without a new hypothesis.
- The separate PTQ1_0 GGUF admission evidence remains gated/unranked; no model
  successor is launched from this partial MLX result.

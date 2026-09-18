# AXQ6 Native Gate: Build Failure (2026-09-18)

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**HF revision:** bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924
**Config hash:** 942fd0c767d0
**Date:** 2026-09-18

## Command and setup

Native gate command (exactly as run):

```
uv run --locked python runner/run_mei_acceptance.py --config configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml
```

Execution used:

- Committed clean Mei v0.5.0 source export: `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`
- Dedicated build path: `mei-build-qwen36-axq6-pinned-050`
- Port: 8025
- Safe controls enabled: `VMLX_ENABLE_UNSAFE_COMPILE=0`, `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0`, `BENCH_NO_FUSED_GATE_UP=1`, `MLX_SAFETENSORS_MMAP=0`, `--load-mmap false`, `--compiled-decode false`
- Exact served identity: `--served-model-id AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`

## Result: BLOCKED / INCOMPLETE

The launcher exited `rc=1` before the `/v1/models` health check, during the fresh Swift production build. Consequences:

- No probe.json
- No 12/12 health checks
- No benchmark rows
- No leaderboard change
- Elapsed: ~34.304 seconds

Build log (`build.log`) first real failures — `CompileMetalFile` failures followed by `Build failed`:

- `scaled_dot_product_attention.metal`
- `steel_attention.metal`
- `rms_norm.metal`
- `random.metal`
- `rope.metal`
- `layer_norm.metal`
- `gemv.metal`
- `conv.metal`

`vmlx-swift` resolved at `44461ffdf8dca836b624b2d0d268c800dedea05e`.

## Classification

Pinned-source / build / toolchain setup failure — not a model quality failure and not a harness-row failure.

## Evidence

Raw evidence and archived copies:

- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-record.json`
- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-launcher.log`
- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-swift-build.log`

The external run directory below is authoritative raw evidence. Its original
`launcher.log` SHA-256 is `b62a01337bf73baa6f57ab909385cee5557a19774992b73543f29a339c9a3ffd`;
the committed copy removes only the generated trailing space on line 1 so the
scoped evidence commit passes `git diff --check`. The raw external file remains
untouched.

External results-mei run directory:

`/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260918T070730Z`

## Teardown (verified after failure)

- No AXQ6 runner/server/probe process running
- Port 8025 free
- `server.pid` absent

The partial dedicated build directory (`mei-build-qwen36-axq6-pinned-050`) remains in place for forensic inspection; no deletion was performed.

## Next action

Do not launch the 25-row battery. Investigate/reconcile the pinned-source Metal build failure in a separate bounded unit before another gate.
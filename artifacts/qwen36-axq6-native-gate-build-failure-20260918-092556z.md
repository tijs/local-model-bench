# AXQ6 Native Gate: Build Failure (2026-09-18, run 092556Z)

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**HF revision:** bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924
**Config hash:** `942fd0c767d0` (sha256 short prefix of `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml`: `942fd0c767d092d57f7d89222d6099d47b28870e4af3f53e8a4bd486f3b2fea2`)
**Date:** 2026-09-18 — run dir `mei-20260918T092556Z` (started 11:25:56 CEST, finished 11:28:00 CEST)

## Command and setup

Native gate acceptance command (exactly as run):

```
uv run --locked python runner/run_mei_acceptance.py --config configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml
```

Pinned sources used for the fresh production build:

- Mei source export (committed clean): `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`
  (`--mei-repo /Users/tijs/.local/share/local-model-bench/mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`)
- vmlx-swift, pinned revision in that export's `Package.resolved`: `44461ffdf8dca836b624b2d0d268c800dedea05e`
- Dedicated build path: `/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050`

Toolchain: **Xcode 27.0 (Build 27A266a)** present; **MetalToolchain** mounted at
`/var/run/com.apple.security.cryptexd/mnt/com.apple.MobileAsset.MetalToolchain-v27.1.266.1.U2DV6k/Metal.xctoolchain`.

Safe launch controls (from `record.json` launcher env/command, all applied):

- `VMLX_ENABLE_UNSAFE_COMPILE=0`
- `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0`
- `BENCH_NO_FUSED_GATE_UP=1`
- `MLX_SAFETENSORS_MMAP=0`
- `--load-mmap false`
- `--compiled-decode false`
- Port: **8025**
- `--served-model-id AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`, `--context-cap 65536`,
  `--prefill-step-size 512`, `--memory-limit-bytes 30000000000`, `--enable-thinking true`,
  `--temperature 0.6`, `--top-p 0.95`, `--top-k 20`, `--emit-reasoning true`, `--cache-reuse true`,
  `--kv-cache-dir /Users/tijs/.local/share/local-model-bench/mei-runtime/kv-axq6-mtp`

Run preflight (per run recording): fresh disk space **63.419 GiB**; model manifest verification **20/20**.

## Result: BLOCKED / INCOMPLETE — launcher rc=1 before health

`record.json` status `error`; error `"RuntimeError: launcher exited before health, rc=1"`.
Elapsed **~123.96 s** (`started_epoch 1789723556.723744`, `finished_epoch 1789723680.68519`).
The fresh Swift production build failed before the server ever launched.

Build log (`mei-runtime/logs/build.log`, this run) root cause — **SwiftCompile failed**
(vmlx-swift `Libraries/MLXLMCommon/Evaluate.swift:3398:80`):

```
error: SwiftCompile normal arm64 failed with a nonzero exit code. Command line: cd /Users/tijs/.local/share/local-model-bench/mei-source
/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050/checkouts/vmlx-swift/Libraries/MLXLMCommon/Evaluate.swift:3398:80: error: the compiler is unable to type-check this expression in reasonable time; try breaking up the expression into distinct sub-expressions
3396 |                         // and the outcome for each boundary considered.
3397 |                         FileHandle.standardError.write(Data(
3398 |                             ("[vmlx][cache/store-boundary] boundary=\(boundary)"
3399 |                                 + " store=\(storeBoundary) stable=\(isStableBoundary)"
3400 |                                 + " allowRederive=\(allowRederive)"
...
error: Build failed
```

The compiler cannot type-check the concatenated string/interpolation expression inside
`FileHandle.standardError.write(Data(...))` at the cache/store-boundary diagnostic (Evaluate.swift:3397-3400)
under Xcode 27.0's Swift frontend. Note this differs from the earlier 070730Z gate failure
(`qwen36-axq6-native-gate-build-failure-20260918.md`), which failed earlier at `CompileMetalFile`
for the Metal kernels; this run passed Metal compilation and failed later, in SwiftCompile.

Consequences:

- No `probe.json` in the run output dir (it contains only `record.json` and `launcher.log`)
- No benchmark rows: `results/log.jsonl` has **0 rows** for `AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`
- No leaderboard change: `results/LEADERBOARD.md` has no AXQ6 entry

Teardown (verified after failure):

- No server/listener on port 8025 (`lsof -nP -iTCP:8025` → none)
- No mei process (`pgrep -fl mei` → none); no `server.pid`
- No AXQ6 KV dir: `mei-runtime/kv-axq6-mtp` does not exist (build failed pre-launch; nothing persisted)

## Classification

**Pinned-source / build / compiler setup blocker** — a Swift frontend type-check failure in the
pinned vmlx-swift source under Xcode 27.0. Not a model failure and not a harness-row failure.

## Evidence

Raw external evidence (originals **not altered**; SHA-256 of originals):

- Run record: `.../results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260918T092556Z/record.json`
  — SHA-256 `0bdc0e83086c2c4bb73b66a687d3548ad3f872a8f11f71abf88762ac92f724b3`
- Run launcher log: same dir `launcher.log`
  — SHA-256 `b62a01337bf73baa6f57ab909385cee5557a19774992b73543f29a339c9a3ffd`
- Build log: `/Users/tijs/.local/share/local-model-bench/mei-runtime/logs/build.log`
  — SHA-256 `d696b95ad7a036d56ec6a9b61fb99257fdebfe2b07da8cda410d1b910cbbba83`

Committed artifact copies (this run, distinct names; each strips only generated trailing
whitespace — one blank-ish line — so the evidence commit passes `git diff --check`):

- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-092556z-record.json`
- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-092556z-launcher.log`
- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-092556z-swift-build.log`

## Next action

Do **not** launch the 25-row battery and do **not** proceed to a successor model yet. First run a
bounded compiler/source compatibility diagnosis: reproduce the `Evaluate.swift:3398` type-check
failure in isolation and either (a) refactor that cache/store-boundary `FileHandle` diagnostic into
distinct sub-expressions, or (b) confirm the pinned vmlx-swift revision
(`44461ffdf8dca836b624b2d0d268c800dedea05e`) is compatible with the Xcode 27.0 Swift frontend and
identify the minimal compatible revision. Only re-run the native gate after that diagnosis resolves.
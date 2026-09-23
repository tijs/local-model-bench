# Bonsai2 Mei Consumer Export Build Gate — vmlx 46933d60

- Report date: 2026-09-23 22:01 CEST (UTC+02:00)
- Unit: Exact-source Mei consumer export build gate for the MLX pack
  `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` (immutable revision
  `3f926b415992eaa2ae9dd7b573706494d6bbf787`) against isolated vmlx-swift
  Bonsai commit `46933d60`.
- Status: **PASS (build only)**

## Scope / constraints honored

- No model or server launched; no benchmark run; no benchmark ports opened.
- Main Mei checkout (`/Users/tijs/projects/mei`) not touched (read-only).
- vmlx checkout (`/Users/tijs/projects/vmlx-swift-bonsai-prism`) not mutated
  and not committed (verified clean before and after build).
- CoCore not restarted; nothing published/pushed; Kiem unmodified.
- No caches/weights deleted. Only artifact written: this report.
- No competing benchmark/build process detected at start; one writer only.

## Exact inputs

| Item | Value |
|---|---|
| vmlx worktree | `/Users/tijs/projects/vmlx-swift-bonsai-prism` |
| vmlx branch | `bonsai2-prism-hadamard-slice` |
| vmlx HEAD | `46933d6012e48eb7183570226948a8cb331a5ee7` |
| vmlx pre-build status | clean (`git status --porcelain` empty, 0 lines) |
| vmlx post-build status | clean (0 lines) — unmutated |
| Mei consumer export | `/Users/tijs/projects/mei-bonsai-prism-12121099` (not a git checkout; `.build` ignored) |
| Export Package.swift dep | `.package(name: "vmlx-swift", path: "/Users/tijs/projects/vmlx-swift-bonsai-prism")` |
| Toolchain | Swift 6.4 (swiftlang-6.4.0.34.1, clang-2100.3.34.1), Xcode `/Applications/Xcode.app/Contents/Developer`, target arm64-apple-macosx27.0.0 |
| Fresh scratch path | `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-46933d60-20260924` (created new; absent before build) |

## Gates executed (required)

1. AGENTS.md inspected in both target repos:
   - `/Users/tijs/projects/vmlx-swift-bonsai-prism/AGENTS.md` (MLXPress
     non-negotiables; read-only build of this lane — no runtime claims made).
   - `/Users/tijs/projects/mei-bonsai-prism-12121099/AGENTS.md` (SwiftPM with
     explicit `DEVELOPER_DIR`, CoCore stays off, no publish/push).
2. Export `Package.swift` verified: local path dependency on
   `vmlx-swift-bonsai-prism` confirmed (exact path above; swift-nio source
   dep `2.65.0..<3.0.0`).
3. vmlx HEAD verified `46933d60…` on branch `bonsai2-prism-hadamard-slice`;
   worktree clean pre-build.
4. Disk checked pre-build: 12,425,276 KB free (~11.85 GiB) > 10 GiB floor.
5. `swift package describe --type json` (exit 0) — full JSON captured to
   `/tmp/mei-describe-46933d60.json` (stderr empty). Verified identity
   `vmlx-swift-bonsai-prism`, type `fileSystem`, path
   `/Users/tijs/projects/vmlx-swift-bonsai-prism`; product `mei` executable
   present; tools_version 6.1.
6. `swift build -c release --product mei --scratch-path <fresh scratch>`
   (exit 0, 287.95 s) — full unfiltered log captured to
   `/tmp/mei-build-46933d60.log` (72,412 lines).

## Build result

```
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build -c release \
  --product mei \
  --scratch-path /Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-46933d60-20260924
exit code: 0
Build complete! (287,95 sec)
```

Tail of build log: `MeiCore` compiled, `mei-product` linked, no errors.
Compiler emitted only informational diagnostic-URL doc lines (e.g.
`UnnecessaryEffectMarker`) before successful completion.

## Binary evidence

| Item | Value |
|---|---|
| Binary path | `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-46933d60-20260924/release/mei` |
| Size | 89,529,696 bytes (mtime 2026-09-23 22:01 CEST) |
| SHA-256 | `b3fa89a77f971c25f1f422c7300f8b6a023d77d2626e129a5163dda4871a14ef` |
| `file` | `Mach-O 64-bit executable arm64` |
| `lipo -info` | Non-fat file, architecture: arm64 |
| Scratch path size | 2.3 GB (`du -sh`) |
| Disk after build | 11,301,100 KB free (~10.78 GiB) — still above 10 GiB floor |

## SwiftPM dependency graph / provenance

- Root package: `Mei` (tools 6.1), path
  `/Users/tijs/projects/mei-bonsai-prism-12121099`.
- Direct deps (from `swift package describe --type json`):
  - `vmlx-swift-bonsai-prism` — `fileSystem`, path
    `/Users/tijs/projects/vmlx-swift-bonsai-prism` (exact source commit
    `46933d60…` verified via `git rev-parse`; local path deps carry no
    `Package.resolved` entry — confirmed 0 vmlx entries, expected).
  - `swift-nio` — `sourceControl`,
    `https://github.com/apple/swift-nio.git`, range `2.65.0..<3.0.0`;
    resolved pin (export `Package.resolved`): version `2.103.0`, revision
    `21de5f08c1a166a6dd293d0e587ad977bf8dac5d`.
- MeiCore consumes products VMLX, MLX, MLXLMCommon, MLXLLM, MLXHuggingFace,
  VMLXTokenizers, NIOCore, NIOHTTP1, NIOPosix; `mei` executable consumes
  MeiCore.

## No-server / no-port state

- No `mei`, swift-build, or benchmark/model process running after build.
- Listening sockets at completion: only `127.0.0.1:8766` (Hermes
  tailnet dashboard router) and `127.0.0.1:9119` (Hermes dashboard) — pre-existing
  auxiliary services, not benchmark/model servers. No new ports opened.
- Binary was **not launched**; no runtime, load, or generation evidence
  exists from this unit.

## Remaining gate (not covered by this unit)

- The `mei` binary is built but not launched. Model support, loader
  behavior, and benchmark readiness for `Ternary-Bonsai-2-27B-mlx-2bit` at
  `3f926b41…` are **not claimed** from a build alone. Next unit: launch the
  binary with the MLX pack and measurably verify load + inference through the
  real vMLX path (per vmlx AGENTS.md MLXPress gates: token/s, per-model
  generation config, cache topology, multi-turn, RAM footprint, no forced
  behavior).
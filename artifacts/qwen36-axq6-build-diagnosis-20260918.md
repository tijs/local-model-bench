# AXQ6 Blocker Diagnosis: vmlx-swift Evaluate.swift:3398 type-check failure under Xcode 27.0 (2026-09-18)

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**HF revision:** bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924
**Config hash:** `942fd0c767d0` (`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml`)
**Pinned sources:** Mei tag v0.5.0 source export `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`; vmlx-swift `44461ffdf8dca836b624b2d0d268c800dedea05e` (per the export's Package.resolved)
**Build path:** `/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050`
**Date:** 2026-09-18 (this tick)

## Preflight (this tick)

- No benchmark runner, server, or probe process; no listeners on any bench port (8012/8016/8017/8018/8020/8024–8027). Single-tenant window clean.
- Free disk now **62.6 GiB** — above the ~55.1 GiB pre-staging requirement (was 51.97 GiB at the last blocked check). Disk is no longer the blocker.
- Working tree: `main` ahead 80, clean; latest commits are the two AXQ6 build-failure evidence commits and the config pin reconciliation.
- `xcrun metal --version` passes (MetalToolchain installed after the first 070730Z failure). Toolchain: Xcode 27.0 build 27A266a, Swift 6.4 (swiftlang-6.4.0.34.1).

## Root cause (confirmed by isolated repro)

The launcher build fails in `SwiftCompile` at
`vmlx-swift/Libraries/MLXLMCommon/Evaluate.swift:3398:80`:

```
error: the compiler is unable to type-check this expression in reasonable time; try breaking up the expression into distinct sub-expressions
```

The hostile expression is the env-gated (`VMLX_CACHE_FETCH_TRACE == "1"`) cache/store-boundary
debug diagnostic: a single long chain of string interpolations concatenated inline inside
`FileHandle.standardError.write(Data(( ... ).utf8))`. It is dead code unless the trace env is set;
it never runs in a benchmark server launch.

**Isolated repro:** the exact expression was extracted into
`scratch-typecheck/axq6-repro.swift` (sha256 `737b842c…`) with faithful local stand-ins and
compiled with the same frontend (`swiftc -typecheck -O`). It fails with the identical
"unable to type-check… in reasonable time" error, confirming the failure is expression-level,
not module/context dependent.

**Frontend flag test:** `-Xfrontend -solver-shrink-unsolved-threshold` (the only related
hidden knob) was raised to 100000 — the expression still fails to type-check. No frontend
flag path resolves it; the standard fix (breaking the expression into sub-expressions) is
the only working route.

## Verified fix

The diagnostic was refactored into distinct sub-expressions (precompute
`capturedSnapshot`, `snapshotState`, then a `boundaryMessage` string; write once), preserving
output bytes exactly (same separators, same `\n`, same values). Evidence:

1. **Isolated repro of the refactor** (`scratch-typecheck/axq6-repro-fixed.swift`, sha256
   `0dbed7aa…`) type-checks clean in <0.2s (RC=0).
2. **Full pinned package build** with the refactor applied to the disposable SPM checkout
   of the export's vmlx (no git repo touched): `swift build -c release --scratch-path
   mei-build-qwen36-axq6-pinned-050 --package-path mei-source/mei-1518e701…` →
   **Build complete in 219.05s, 0 errors**, `release/mei` (89,227,616 bytes) produced.
   Build log: `scratch-typecheck/axq6-patched-build.log` (sha256 `daed538b…`).
3. The diff (19 insertions / 14 deletions, one function only): `scratch-typecheck/axq6-evaluate-refactor.diff` (sha256 `a636a471…`).

The disposable scratch checkout was **restored to the pristine pinned state** (git checkout
of Evaluate.swift; worktree clean, 0 untracked files) after the proof, so no silent
provenance drift can survive in the build area.

## No published compatible revision exists

- Fork `tijs/vmlx-swift`: origin/main is `e37d1d59` (2026-09-07) — **older** than the pin;
  `44461ffd` is NOT an ancestor of main; main's Evaluate.swift still contains the same
  diagnostic shape (line ~3266).
- The pin `44461ffd` is the tip of `release/prefix-capture-fixes` /
  `sync/capture-plus-upstream`. The branch tips `fecbea52` → `d4ef3e06` → `23551729`
  (2026-09-11 sync merges) **still contain the identical hostile inline expression**
  (line 3406-3411 at `23551729`).
- `git log -S 'cache/store-boundary' --all` shows only the introducing commit (`14143c61`);
  no ref anywhere refactors it.

Conclusion: the fix must be a **new commit**; it exists nowhere upstream. Application paths
(see below) are authorization-gated.

## Decision needed (user)

The AXQ6 native gate stays closed until one of these is authorized:

- **(a) Fork commit + re-pin (recommended):** authorize a minimal refactor commit on
  `tijs/vmlx-swift` (the diff above), then re-export the Mei source with the updated
  `Package.resolved`, record the new vmlx pin + config hash, and rerun the native gate.
  Requires GitHub push permission.
- **(b) Local patch build mechanism:** add a benchmark-owned, provenance-recorded patch
  step to `start_mei_server.sh` (config/runner change + tests, committed) so the pinned
  export builds with a recorded patch identity without GitHub activity.
- **(c) Compatible older toolchain:** install/select a Swift frontend that type-checks the
  pinned expression (only Xcode 27.0 is installed today).

Until then: no 25-row battery, no Bonsai/Gravity start, no leaderboard impact (0 AXQ6 rows).

## Files (this tick)

- Artifact: `artifacts/qwen36-axq6-build-diagnosis-20260918.md`
- Repro + evidence: `~/.local/share/local-model-bench/scratch-typecheck/{axq6-repro.swift, axq6-repro-fixed.swift, axq6-evaluate-refactor.diff, axq6-patched-build.log}` (benchmark-owned runtime root, outside the repo)
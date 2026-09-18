# AXQ6 Native Gate: vmlx-swift Type-Check Fix (2026-09-18)

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**Config hash:** `11c43b26cb6b` (new, post-fix config: `11c43b26cb6bffab77c28104a2ba8c0f16c750a4ba57deb1f049e886ae605f39`)
**Previous pre-gate hashes (no rows exist for any):** `703118869d87`, `942fd0c767d0`

## Root cause

The Xcode 27.0 / Swift 6.4 frontend cannot type-check the chained
string-interpolation expression inside
`FileHandle.standardError.write(Data(...))` at vmlx-swift
`Libraries/MLXLMCommon/Evaluate.swift:3397-3410` (store/cache-boundary trace,
gated by `VMLX_CACHE_FETCH_TRACE=1`):

```
error: the compiler is unable to type-check this expression in reasonable
time; try breaking up the expression into distinct sub-expressions
```

This is a **compiler/source-compatibility failure**, not a model failure and
not a harness-row failure. The pinned vmlx-swift revision
`44461ffdf8dca836b624b2d0d268c800dedea05e` (per the CLEAN Mei v0.5.0 source
export's `Package.resolved`) fails to compile under the installed toolchain.

## Fix

Split the message into distinct sub-expressions: build `boundaryMessage` as a
`let` (plus `capturedSnapshot`/`snapshotState` lets), then write once with
`Data(boundaryMessage.utf8)`. **No behavior change** — identical contents,
identical `VMLX_CACHE_FETCH_TRACE=1` gating, identical stderr target.

- Local repro (original expression): `scratch-typecheck/axq6-repro.swift`
- Local repro (fixed expression): `scratch-typecheck/axq6-repro-fixed.swift`
- First patched scratch build (loose working-tree edit, 12:38-12:44 UTC):
  `scratch-typecheck/axq6-patched-build.log` — `Build complete! (219,05 sec)`

## Why the first two fixes did not stick (durability fix)

1. **Loose working-tree edit** (12:38-12:44 UTC): the wrapper's next
   `swift build` re-provisioned the SPM scratch checkout from the pinned
   remote revision and hard-reset the edit (12:45Z rerun failed identically).
2. **Local-only commit + `Package.resolved` revision pin** (15bada58 in the
   local SPM store): SPM re-resolves against the fork URL
   (`https://github.com/tijs/vmlx-swift.git`) during provisioning, cannot
   find the local-only revision on the remote, and **rewrites
   `Package.resolved` back to 44461ffd** — same failure again (10:49Z run).
3. **Local PATH dependency (FINAL)**: the fixed export
   `mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb-vmlxfix15bada58`
   declares vmlx-swift as `.package(path: "/Users/tijs/.local/share/
   local-model-bench/vmlx-swift")`. That directory is a **full checkout of
   44461ffd including the git submodules** `Source/Cmlx/mlx` and
   `Source/Cmlx/mlx-c` (SPM mirror clone; `git archive` alone strips
   submodule content — first path-dep attempt failed with
   `mlx/c/distributed.h file not found`) plus the refactor applied to
   `Libraries/MLXLMCommon/Evaluate.swift` (tree equivalent of commit
   15bada58). SPM derives package identity from the directory basename, so
   the dir MUST be named `vmlx-swift` for the `.product(package:)`
   references to resolve. Path dependencies are not recorded in
   `Package.resolved`, so provisioning cannot re-resolve them away.

Durable fix: the refactor lives in the source the build actually consumes.
No GitHub push: fork `tijs/vmlx-swift` main is `e37d1d59…` and still
contains the same unpatched expression (checked at `Libraries/MLXLMCommon/
Evaluate.swift:3263`), so there is no upstream fix to adopt.

## Config change

`configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml`:
- `mei_commit:` `44461ffd…` → `15bada58953b5f830d1b52f40850b695b87efdf8`
- launch command `--mei-repo` → `…-vmlxfix15bada58` export
- known_gaps: added VMLX TYPE-CHECK FIX PINNED note; SOURCE/BUILD PIN
  RECONCILED note superseded (the underlying facts it describes — original
  export, dedicated build dir, never point at live ~/projects/mei — still
  hold for the fixed export).

Config hash `942fd0c767d0` → `11c43b26cb6b`. No rows exist for either hash.

## Verification

- YAML parses (`yaml.safe_load` OK).
- New hash computed from the exact committed bytes.
- Fix commit object present in the local SPM store.
- Port 8025 free; no mei/bench process active at fix time; disk ≥ 60 GiB.
- Native gate outcome (next step) recorded in its own run dir under
  `results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/` when run.
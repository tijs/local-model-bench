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

## Why the first patch did not stick (durability fix)

The initial fix was a loose edit of the SPM scratch checkout
(`mei-build-qwen36-axq6-pinned-050/checkouts/vmlx-swift/...`). The wrapper's
next `swift build` re-provisioned that checkout from the pinned remote
revision and hard-reset the edit, so the 12:45Z gate rerun failed with the
same error (`mei-runtime/logs/build.log`, this day).

Durable fix: the refactor is now a **local commit** on top of the pin,
present in SPM's own repository store, so provisioning always extracts the
fixed source:

- Commit: `15bada58953b5f830d1b52f40850b695b87efdf8`
  ("mlxlmcommon: split store-boundary trace string into sub-expressions",
  parent `44461ffdf8dca836b624b2d0d268c800dedea05e`)
- Location: local SPM store of the AXQ6 pinned build dir,
  `mei-build-qwen36-axq6-pinned-050/repositories/vmlx-swift-6e46428d`,
  ref `refs/heads/local/typecheck-44461ffd` (verified: `git cat-file -t`
  reports `commit`; commits were made in the scratch checkout and pushed to
  that local store; the scratch checkout's `.git/logs/HEAD` was read-only,
  reflog writes disabled via `-c core.logAllRefUpdates=false`)
- Pin: new source export copy
  `mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb-vmlxfix15bada58/`
  (3.2 MB copy of the v0.5.0 export; only `Package.resolved` changed:
  vmlx-swift `state.revision` = `15bada58…`). The original
  `mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` export is untouched.
- No GitHub push: fork `tijs/vmlx-swift` main is `e37d1d59…` and still
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
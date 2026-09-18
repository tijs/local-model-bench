# AXQ6 Native Gate: vmlx-swift Type-Check Fix (2026-09-18)

**Candidate (AXQ6):** AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
**Config hash:** `f0c165be1ebe` — final committed config (full sha256 `f0c165be1ebec3ed28971dd7463b43ecf8f20ded0cdb8c29fbcaed41f8da275b`)
**Previous pre-gate hashes (no rows exist for any):** `703118869d87`, `942fd0c767d0`, `11c43b26cb6b`

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
- Path-dep scratch build: `Build complete!` (BUILD_RC=0, 255s full rebuild).
- Server load (wrapper gate run mei-20260918T105928Z, config f0c165be1ebe
  via the fixed export): model loaded — `active 24401171724` bytes under the
  30 GB limit, listening on 8025, fused GDN decode active, KV dir created,
  server decoded continuously (15-50% CPU, established socket) for the full
  3600s probe budget. The probe produced NO probe.json within 3600s — the
  wrapper's `run_mei_acceptance.py` kills `probe_mei.py` at 3600s; with
  5+ generation-style stages each carrying up to 900s request timeouts on a
  24.4 GB 6-bit MoE, the per-stage budget is exhausted before completion.
  This is a slow-model budget classification (decode was continuous, no
  idle hang), consistent with the dense-27B speed-gate evidence in this
  repo. Evidence: run record `.../mei-20260918T105928Z/record.json`
  (`TimeoutExpired ... timed out after 3600 seconds`, probe_rc None).
- DIRECT probe run (server launched manually via start_mei_server.sh on the
  same pinned build/export; probe_mei.py with `--skip-cache --skip-context
  --timeout 3600`, output `.../mei-20260918T120000Z-direct/probe.json`)
  started 2026-09-18 ~12:00Z; server serving exact identity immediately;
  probe decoding continuously (18-99% CPU) — result pending in its
  probe.json. This isolates the admission evidence (identity/plain/
  stream/tool/parity) from the budget-heavy cache/context stages.
- Port/process state at each step confirmed free before launches; no
  concurrent bench writer (Qwen worker next tick 13:36 CEST was idle).
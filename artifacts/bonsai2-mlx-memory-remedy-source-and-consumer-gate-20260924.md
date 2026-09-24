# Bonsai2 MLX Memory Remedy — Source Implementation Gate, Independent Review, and Mei Consumer Build Gate (2026-09-24)

- Report date: 2026-09-24 02:06 CEST (UTC+02:00)
- Unit: Source-implementation gate for the default-off head_dim-256 SDPA admission
  remedy (hypothesis H of `bonsai2-mlx-memory-remedy-audit-20260924.md`), plus an
  independent review pass and an exact-source Mei consumer export build against the
  pinned vmlx commit `746d1c47`.
- Status: **PASS (source implementation gate; independent review pass/proceed;
  consumer build gate — build only). No GPU, NAX, numeric, runtime, model, or
  benchmark claim of any kind.**
- Author note: the parent session requested the named `umans-coder` profile, which
  was unavailable (HTTP 403); this report was authored by the configured fallback
  delegated worker, **not** the `umans-coder` profile.

## Scope / constraints honored

- Work confined to `/Users/tijs/projects/local-model-bench` (this commit adds only
  this artifact). No other repository edited.
- No benchmark, no server, no probe, no publish, no push. `results/log.jsonl`,
  `results/`, `results-mei/`, `configs/`, `runner/`, and all model caches/weights
  untouched.
- vmlx working tree `/Users/tijs/projects/vmlx-swift-bonsai-prism` not mutated and
  not committed by this unit (re-verified clean, below).
- Mei main checkout `/Users/tijs/projects/mei` untouched (read-only; the consumer
  export is a separate isolated directory).
- No secrets recorded; no invented output; every fact below is supplied by the
  parent's verification or re-verified read-only on disk during this unit.

## 1. Source implementation gate

### 1.1 Exact identities / pins (re-verified on disk during this unit)

| Thing | Exact value |
|---|---|
| vmlx worktree | `/Users/tijs/projects/vmlx-swift-bonsai-prism` |
| vmlx branch | `bonsai2-prism-hadamard-slice` |
| vmlx HEAD | `746d1c47f89db29c33ea1174e01e35fc219d5b01` (`bonsai2: exclude SDPA admission doctest from Cmlx target, pin bd=256 full kernel source`; parent commit `559b6ee6` `bonsai2: pin mlx submodule to default-off head_dim-256 full-SDPA admission experiment`; prior `46933d60`) |
| vmlx tree status | clean (`git status --porcelain` = 0 lines, pre- and post-verification) |
| Nested `Source/Cmlx/mlx` pin | `a2829e90878a7354f2668831af1409b3972a3c2f` (`bonsai2: instantiate bd=256 full/NAX SDPA steel kernels + trailing newlines`), submodule of `osaurus-ai/mlx` (vmlx `.gitmodules`); tree clean (0 lines) |
| Nested mlx original baseline | `73312d3e9ad0bd2e1bdf9a08d91e25571e255964` (`Merge pull request #6 from osaurus-ai/fix/metal-completion-handler-no-throw`) — parent of `a2829e908`, verified present as a commit |
| Prior experiment commit | `66eb47301` (`bonsai2: default-off full/prefill SDPA head_dim-256 admission experiment (VMLX_BONSAI2_SDPA_FULL_HD256=1)`) |
| `Source/Cmlx/mlx-c` pin | `7bede8f1491384bb580f87d1d510f80cbd53660d` (`qwen4_exp campaign: io plumbing for mmap file-region arrays`), submodule of `osaurus-ai/mlx-c`; tree clean |
| Host | macOS 27.0, arm64; Xcode `/Applications/Xcode.app/Contents/Developer` |

### 1.2 Patch semantics (source of truth, re-read this unit)

- `Source/Cmlx/mlx/mlx/backend/metal/scaled_dot_product_attention.h:15-37`:
  admission table — `head_dim` 64 / 80 / 128 always admitted (matches upstream);
  `head_dim == 256` admitted **only** when `full_hd256_experiment_enabled()` is true.
  The control reads `VMLX_BONSAI2_SDPA_FULL_HD256` per call and is true only for an
  exact `"1"`; absent, empty, or any other value keeps the experiment **OFF** —
  fail closed, no behavior change without the explicit env control. Off-path
  preserves the historical 64 / 80 / 128 (and vector) dispatch exactly.
- `scaled_dot_product_attention.cpp:627` and `scaled_dot_product_attention.h:20`
  document the same default-off research control.
- Full/prefill arm only: the gate opens head_dim 256 for the full/prefill fused
  path; anything outside full-head_dim-256 keeps the historical decision
  (head_dim 256 rejected -> dense fallback when the control is off).
- CPU doctest: `Source/Cmlx/mlx/mlx/backend/metal/tests/sdpa_admission_tests.cpp`
  (toggles the env in-process; wired in `tests/CMakeLists.txt:48`). It is a
  standalone test: `Package.swift:61` and `Package.swift:95` both exclude
  `mlx/mlx/backend/metal/tests` from the SwiftPM Cmlx targets — test absent from
  the SwiftPM Cmlx translation units (TU present), per parent gate.
- Source instantiations (verified in the `a2829e908` diff):
  - Regular (full) — `kernels/steel/attn/kernels/steel_attention.metal`:
    `instantiate_attn(iname, itype, 32, 16, 256, 4, 1, ...)` → bq32 / bk16, bd256.
  - NAX — `kernels/steel/attn/kernels/steel_attention_nax.metal`:
    `instantiate_attn(iname, itype, 64, 32, 256, 4, 1, ...)` → bq64 / bk32, bd256.
- Generated regular Metal artifact present (`Source/Cmlx/mlx-generated/metal/`:
  `scaled_dot_product_attention.metal`, `sdpa_vector.h`, `hadamard.h`, etc.).

### 1.3 Parent gates (supplied, re-grounded here)

| Gate | Result |
|---|---|
| SwiftPM Cmlx target | 180 sources; standalone SDPA admission test absent / TU present |
| CPU build + tests (CMake/ctest and direct doctest) | PASS — 6 cases / 1063 assertions |
| `clang++` syntax pass | PASS |
| Regular generated Metal compile + bd256 AIR names | PASS |
| Current NAX static compile (host toolchain) | FAIL — pre-existing lambda / Metal 4.0 errors |
| Original baseline (`73312d3e`) static compile (host toolchain) | FAIL — same pre-existing lambda / Metal 4.0 errors |

The NAX and baseline static compile failures are **pre-existing on the host
toolchain** (lambda / Metal 4.0 shader-language errors), reproduced on the
unpatched original baseline as well; they are not introduced by this patch.

## 2. Independent review

- Independent review of the source implementation: **pass / proceed**. The review
  made **no GPU, no NAX, no numeric fused-vs-dense parity, and no live/runtime
  claim**; it is a source-level pass only.

## 3. Consumer build gate (Mei export, exact source)

### 3.1 Inputs

| Item | Value |
|---|---|
| Consumer export | `/Users/tijs/projects/mei-bonsai-prism-12121099` (isolated; `.build` ignored; not a git checkout) |
| Main Mei | `/Users/tijs/projects/mei` — untouched (read-only) |
| Export dependency | `Package.swift:18` `.package(name: "vmlx-swift", path: "/Users/tijs/projects/vmlx-swift-bonsai-prism")` — local path dep to the exact vmlx checkout above; plus `swift-nio` `2.65.0..<3.0.0` (describe JSON) |
| `swift package describe --type json` | exit 0; identity `vmlx-swift-bonsai-prism` type `fileSystem` path `/Users/tijs/projects/vmlx-swift-bonsai-prism`; products `MeiCore`, `mei`; tools_version 6.1; JSON saved `/tmp/mei-describe-746d1c47.json`; stderr empty, saved `/tmp/mei-describe-stderr-746d1c47.log` |
| Fresh scratch | `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-746d1c47-20260924` (new; absent before build) |
| Prior generated scratch | `mei-build-bonsai2-prism-46933d60-20260924` — **removed exactly before this build** (re-verified absent this unit) |

### 3.2 Build command and result

```
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build -c release \
  --product mei \
  --scratch-path /Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-746d1c47-20260924
```
- Exit code: **0**. Wall clock: **316 s** (Swift build step per log: **287.77 s**,
  `Build complete! (287,77 sec)`).
- Full unfiltered log: `/tmp/mei-build-746d1c47.log` — **8,020,425 bytes**
  (72,663 lines). Only informational compiler diagnostics (e.g.
  `UnnecessaryEffectMarker`, `Sendable` conformance notes, needless `??` note) —
  no errors.
- Disk free (KB): before **12,977,068**; after **10,986,788** (supplied recorded
  values).

### 3.3 Binary evidence

| Item | Value |
|---|---|
| Binary path | `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-746d1c47-20260924/out/Products/Release/mei` |
| Size | 89,529,696 bytes (mtime 2026-09-24 02:03 CEST) |
| SHA-256 | `2fe43a775c8c47781043eaeb8d68dd090ce4b378ad6f35ffa0b37f3495845b28` |
| `file` | `Mach-O 64-bit executable arm64` |
| `lipo -info` | Non-fat file, architecture: arm64 |
| Scratch size | 2.3 GB (`du -sh`) |

### 3.4 Post-build state

- No `mei` / swift-build / benchmark / model process running after build.
- No new listener: only pre-existing auxiliary services remain (Hermes dashboard
  routers `127.0.0.1:8766` / `9119` / `8765`, `rapportd`, ControlCenter — none a
  benchmark/model server).
- The binary was **not launched** — no load, no generation, no cache/context,
  no memory, no benchmark rows exist from this unit.
- Weights, provenance, raw evidence, and results untouched.

## 4. Explicit unverified boundaries

- **No GPU runtime claim** — the Metal kernels were compiled (regular generated
  Metal + bd256 AIR names), not executed on GPU.
- **No NAX runtime claim** — NAX static compile fails on the host toolchain
  (pre-existing lambda / Metal 4.0 errors); NAX is source-instantiated only.
- **No numeric fused-vs-dense parity claim** — no numeric comparison of the
  fused head_dim-256 path against the dense fallback was run.
- **No model load / generation / cache / context / memory claim** — the built
  binary was never launched.
- **No benchmark rows** — `results/log.jsonl`, `results/`, `results-mei/`
  untouched; this report is evidence, not ranking data.
- **Local-only, unpushed commits** — vmlx branch commits (`746d1c47`, `559b6ee6`)
  and the nested fork pins (`a2829e908`, `7bede8f`) are local/experimental;
  nothing published or pushed by or for this unit.
- **Old-toolchain NAX static failure** — recorded as a pre-existing host-toolchain
  failure (both current NAX and original baseline fail), not a pass.

## 5. Exact next gate (not covered by this unit)

1. **Live bounded admission** — launch the fresh `mei` binary with the **exact
   staged model** only after provenance preservation is complete and verified
   (model/weights provenance recorded and pinned first).
2. Use the **fresh binary** at the exact path above (mtime 2026-09-24 02:03 CEST,
   SHA-256 `2fe43a…`) and the exact staged model revision — never a stale build or
   an un-staged model.
3. Bounded admission means resource-bounded (memory/cache caps) live evidence:
   load + generation through the real vMLX path only, with no unbounded run.
4. **No rankability claim** from admission: a bounded admission outcome is not a
   benchmark row and confers no rankability.

## 6. Generated-build cleanup boundary (exact)

- **Disposable (generated output; may be cleaned):** the SwiftPM scratch build
  `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-746d1c47-20260924`
  (2.3 GB) and the transient `/tmp/mei-build-746d1c47.log`,
  `/tmp/mei-describe-746d1c47.json`, `/tmp/mei-describe-stderr-746d1c47.log` —
  exactly as the prior generated scratch `mei-build-bonsai2-prism-46933d60-20260924`
  was removed immediately before this build. Precedent: a generated scratch must be
  removed before the next fresh build so the next binary is from a provably fresh
  scratch.
- **Not disposable (artifact of record / provenance):** the built binary at
  `…/mei-build-bonsai2-prism-746d1c47-20260924/out/Products/Release/mei` (retained
  until the next gate consumes it or supersedes it), model weights and provenance,
  raw evidence and results (`results/`, `results-mei/`, `results/log.jsonl`,
  `configs/`, `runner/`, caches), the pinned source checkouts
  (`vmlx-swift-bonsai-prism`, nested `mlx`, `mlx-c`, `mei-bonsai-prism-12121099`),
  and this artifact.
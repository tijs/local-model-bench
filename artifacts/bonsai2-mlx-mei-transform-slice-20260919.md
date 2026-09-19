# Bonsai 2 MLX / Mei-vMLX transform slice — 2026-09-19

## Scope

This bounded unit followed the parent-reviewed vMLX portability gate for
`prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` at immutable revision
`3f926b415992eaa2ae9dd7b573706494d6bbf787`. It implemented an isolated
clean-room FWHT/module and load-install seam. It did **not** download the MLX
pack, install its Python runtime, launch Mei, load a model, run a probe or
benchmark, change Mei main, enable unsafe compile, restart CoCore, or publish.

Target worktree and commit:

- Worktree: `/Users/tijs/projects/vmlx-swift-bonsai-prism`
- Branch: `bonsai2-prism-hadamard-slice`
- Parent: `78c0b454822f7795284af144e236abe6c03fdb35`
- Implementation commit: `fb0b80eba8ff613b9e4dda1dac25389246610a52`
- Worktree was independently rechecked clean after the commit; generated
  `.build/` material remains ignored and uncommitted.

## Changed paths in the isolated commit

- `Source/MLXNN/PrismBonsaiHadamard.swift`
  - blockwise normalized FWHT with explicit per-module signs;
  - `HadamardActivation`, forward packed linear, and inverse packed embedding
    modules over the repository's MLX affine quantized primitives;
  - strict plan/key-resolution helpers for the validated manifest and
    per-module `.signs` tensors.
- `Libraries/MLXLMCommon/Load.swift`
  - optional `bonsaiTransform:` load seam after sanitize and before generic
    affine quantization;
  - packed module replacement and consumption of weight/scales/biases/signs
    keys before `.noUnusedKeys` update verification.
- `Libraries/MLXLLM/PrismBonsaiPortability.swift`
  - documents the new seam while retaining explicit refusal until the
    model-level parity gate.
- `Libraries/MLXLLM/LLMModelFactory.swift`
  - retains the default-off reject and valid-manifest refusal boundary.
- `Tests/MLXLMTests/PrismBonsaiHadamardTests.swift`
  - deterministic transform/module/manifest/key-resolution tests.

## Parent-side verification

- `swift build --target MLXNN`: **exit 0**.
- `swiftc -parse` over all five changed Swift sources: **exit 0**.
- `git diff --check`: **exit 0**.
- The retained scratch harness for the committed sources was executed directly:
  **40 passed, 0 failed, exit 0**. It covers H4 transform references, round-trip
  identity, packed linear/embedding behavior, sign validation, manifest/plan
  checks, namespace resolution, key consumption planning, and flag-off/valid
  gate decisions. This is not a real model load.
- Canonical `swift test --filter PrismBonsaiHadamardTests` was attempted from
  the committed tree and stopped before test execution at the pre-existing
  pinned-HEAD compiler failure:
  `Libraries/MLXLMCommon/Evaluate.swift:3398` — the compiler cannot
  type-check the cache/store-boundary diagnostic expression in reasonable time.
  `Evaluate.swift` is byte-identical to the parent/pin and is not in the
  implementation commit.
- A temporary behavior-identical split of that unrelated expression allowed
  compilation to proceed, but the package test product then hit a separate
  local codesign failure (`MLXLMTests.xctest`: `mlx.metallib`, code object not
  signed). The temporary edit was restored from `HEAD`; the worktree is clean.
  Therefore the parent does not claim a canonical package-test pass. The
  implementation worker reported 27/27 and 24/24 under its temporary
  verification setup; the parent independently verified the 40/40 scratch
  harness instead.

## Independent review findings

The transform math and MLXNN API usage were internally coherent, and ordinary
models/flag-off behavior remain unchanged. Real model support remains unproven:

1. `LLMModelFactory` still refuses `.gateOnManifestValid`, and its `loadWeights`
   call does not yet pass a plan. The new `Load.swift` install path is therefore
   an intentionally unreachable seam until the model-level wiring/parity gate.
2. The review found hardening gaps to address before wiring: actual `.signs`
   values are not cross-checked against the manifest's sign slices; packed
   scales/biases dtype/shape validation is incomplete; `weight_names` and
   `inverse_weight_names` are not reconciled with `modules[]`; duplicate module
   entries are not rejected; and there is no committed test exercising the
   private install path plus final no-unused-key update.
3. The block-1024 convention has only deterministic local H4/self-consistency
   evidence. It has not been compared against the pinned Python runtime or
   real pack tensors.

These findings keep Kiem plan todo 25 open. No model staging or load is allowed
until a bounded hardening/wiring cycle, real target build, and later identity /
parity / streaming-tool / cache-context / memory gates pass.

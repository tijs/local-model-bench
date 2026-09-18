# Bonsai 2 MLX × Mei/vmlx — isolated portability slice, 2026-09-19

## Scope

This bounded unit follows the completed, unranked Bonsai 2 PTQ1_0 GGUF
admission leg. It did **not** download the MLX pack, install its Python
runtime, launch Mei, load a model, run a probe or benchmark, enable unsafe
compile, restart CoCore, or publish anything.

The target remains `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` at immutable
revision `3f926b415992eaa2ae9dd7b573706494d6bbf787`, with
`model_type: prism_hadamard_qwen35`.

## Implemented isolated slice

A coding worker implemented and committed the first safe vmlx seam in a
separate worktree:

- Worktree: `/Users/tijs/projects/vmlx-swift-bonsai-prism`
- Branch: `bonsai2-prism-hadamard-slice`
- Base: `44461ffdf8dca836b624b2d0d268c800dedea05e`
- Commit: `78c0b454822f7795284af144e236abe6c03fdb35`
- Changed paths:
  - `Libraries/MLXLLM/PrismBonsaiPortability.swift`
  - `Libraries/MLXLLM/LLMModelFactory.swift`
  - `Tests/MLXLMTests/PrismBonsaiPortabilityTests.swift`

The slice is deliberately **not model support**:

- `VMLX_BONSAI_PRISM_HADAMARD=1` is the local, default-off gate.
- With the gate off, a Bonsai root or nested `text_config.model_type` is
  rejected as `unsupportedModelType` before generic model construction; it
  cannot fall through to the registered `qwen3_5_text` fallback.
- With the gate on, the pack's manifest and `hadamard.json` contract are
  validated (schema/runtime/quantization/modules/block/sign/inverse-embedding
  fields). Missing or invalid data fails early with a configuration error.
- A valid manifest is still explicitly refused because the FWHT activation and
  inverse-embedding transform modules are not implemented yet. No ordinary
  `Qwen35TextModel` is substituted.
- Ordinary non-Bonsai configs retain the existing decision path. No shipped
  Mei default was changed.

## Verification

Parent-side inspection confirmed the isolated worktree is clean, the commit
contains exactly the three paths above, `git diff --check` passes, and both the
Mei main checkout and its pinned detached vmlx dependency checkout remain
untouched. No benchmark process or bench-port listener was active.

Checks actually run:

- `swiftc -parse` over the two changed Swift sources and the new test source:
  **exit 0**.
- Scratch package `/tmp/vmlx-bonsai-gate-harness`, using byte-identical copies
  of the new sources and a strict-JSON stand-in for `JSONDecoder.json5()`:
  **24 tests passed, 0 failures**.
- Real `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test
  --filter PrismBonsaiPortabilityTests` in the isolated worktree: **blocked
  before the target tests by a pre-existing pinned-HEAD compiler failure** in
  `Libraries/MLXLMCommon/Evaluate.swift:3398` (`unable to type-check this
  expression in reasonable time`). The file is byte-identical to base
  `44461ffd`; the failure is outside this slice and was not edited.

## Next bounded seam

The branch still needs the actual feature-gated transform path: clean-room
FWHT-aware packed linear and inverse-embedding modules over
`MLX.hadamardTransform`, plus the `Load.swift` weight-install/signed-key
consumption path. Only after that seam is independently reviewed and the real
vmlx target builds should the pinned MLX pack be downloaded and admitted to
identity, parity, streaming/tool, cache/context, memory, and repeated
performance gates. Until then the candidate remains unranked and unserved.

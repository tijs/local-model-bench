# Bonsai 2 MLX pack × Mei/vmlx — source audit, 2026-09-18

Read-only source audit for the Bonsai 2 MLX/Mei follow-on (parent direction in
`artifacts/bonsai2-mlx-mei-follow-on.md`, committed). No code was changed in any
repository. No model payload was downloaded, no package installed, no server
launched, no load/probe/benchmark run. Upstream pack facts were fetched
READ-ONLY over HTTPS from the HF raw URLs at the pinned revision (piped to
stdout, nothing written to disk); every Mei/vmlx fact below is a line-cited
reading of the current local checkouts.

## 1. Pinned revisions (verified locally, 2026-09-18)

| Target | Pin | Verified |
|---|---|---|
| MLX pack `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` | `3f926b415992eaa2ae9dd7b573706494d6bbf787` | HF tree API at the pin: 25 paths (2 dirs + 23 files), incl. `model.safetensors` LFS 8,595,477,990 B |
| Mei | `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` (`git rev-parse HEAD`) | `git status --short` = only pre-existing untracked `Casks/`, `tap/` (preserved, untouched) |
| vmlx-swift dependency checkout | `44461ffdf8dca836b624b2d0d268c800dedea05e` | `/Users/tijs/projects/mei/.build/checkouts/vmlx-swift`, pin matches Mei `Package.swift:19-20` (`url: "https://github.com/tijs/vmlx-swift.git"`, `revision: "44461ffd..."`) |
| local-model-bench (artifact target) | `19ec6ca989ecbe5433e87c1e1a88109c4d1cb391` (pre-commit HEAD) | only this repo is modified/staged/committed |

Rule status: Mei and the vmlx-swift checkout were treated as read-only reference
repositories — no reset/clean/edit/stage/commit/build/launch/probe/benchmark.
No CoCore, no Kiem mutation, no GitHub activity, no payload download.

## 2. Upstream claims vs local source facts

### 2.1 The loader-warning claim (README at the pin)

README.md **lines 139-141** (upstream claim, quoted verbatim):

> This pack declares `model_type: prism_hadamard_qwen35` and **requires the loader bundled in
> `runtime/`**. Ordinary MLX loaders skip the activation transform and the inverse embedding lookup, so
> they return wrong output rather than an error.

Corroborating upstream claims: README.md:62 (weight basis: "Blockwise Hadamard
rotation (block 1024, fixed ±1 signs) folded into the stored weights; the
matching transform is applied to activations at runtime"), README.md:73 ("a
runtime either applies the matching transform or refuses to load the file"),
README.md:98-104 (MLX 2-bit affine container holds scale+bias per group;
`scale = s`, `bias = -s` reproduces ternary levels exactly; group scales
"verified ... bit for bit" against the GGUF pack), `PACK-RUNTIME.md`:12
("Ordinary MLX loaders do not apply the required transforms").

**Local source facts that independently substantiate the claim's mechanism**
(vmlx-swift @ 44461ff):

- Pack `config.json` (at the pin) **line 2529-2533**: `"quantization": {"bits":
  2, "group_size": 128, "mode": "affine"}` — byte-compatible with the standard
  MLX affine 2-bit container that vmlx's generic loader already understands, so
  nothing in the *container* trips a stock loader.
- Pack runtime `runtime/runtime.py` **lines 16-28** (`fwht`) and **31-70**
  (`Packed.__call__`): the ONLY functional differences between the packed
  modules and a stock 2-bit affine Linear/Embedding are (a) a forward
  `fwht` on the input before `mx.quantized_matmul` (lines 60-61, 62-70), and
  (b) an inverse `fwht` after the dequantized embedding lookup (lines 46-59).
  `runtime/codec.py:45-49` confirms stored weights are ordinary 2-bit codes
  with `biases = -scales` — i.e., a stock affine dequant reproduces the exact
  ternary values and only the transforms are missing.
- Pack `config.json` **line 2534** `"requires_runtime": "runtime/artifact.py"`,
  **line 2535** `"hadamard_config": "hadamard.json"`, **line 2536**
  `"tensor_namespace": "mlx-vlm-qwen3_5"`, **line 2537**
  `"gdn_activation_layout": "grouped"`, **line 2543** `"base_model_type":
  "qwen3_5"`, **lines 115-2528** the `modules[]` manifest (per-module `path` /
  `block: 1024` / `embedding` / `dtype: float16`), `hadamard.json` at the pin:
  `block_size 1024`, `transform "normalized-sylvester-walsh-hadamard"`,
  sign_mode `explicit`, 401 folded `weight_names`, `inverse_weight_names =
  ["language_model.model.embed_tokens.weight"]`, 3 sign widths summing 28,672
  with values `{-1, +1}`.

### 2.2 The `PrismHadamardConfiguration` claim (PACK-RUNTIME.md:14) — NOT in this checkouts

`PACK-RUNTIME.md` **line 14** (upstream claim): "`hadamard.json` uses the
version-1 Prism contract accepted by MLX Swift's `PrismHadamardConfiguration`."

Local fact: no such type exists in the Mei-pinned vmlx-swift checkout.
Case-insensitive search of the whole checkout for `hadamard` / `prismhadamard`
/ `prism_hadamard` hits only: the MLX C++ FWHT primitive
(`Source/Cmlx/mlx/mlx/backend/metal/hadamard.{h,cpp}` and C-API surface
`Source/Cmlx/mlx-c/mlx/c/ops.{cpp,h}`), the Swift binding
`Source/MLX/Ops.swift:1577-1584` (`hadamardTransform(_:scale:stream:)`), and an
unrelated JANGTQ readiness gate `Sources/MLXPress/MLXPressModelReadiness.swift:305`
(`"hadamard-tq-matmul-contract"` — about TurboQuant streamed-expert matmul
contracts, not Prism Bonsai packs; see `MLXPressModelReadiness.swift:305-309`).
`prism_hadamard` / `hadamard_qwen` appear in **zero** Swift files in both
Libraries and Sources (verified with `grep -rc`, zero matches). The referenced
"MLX Swift" is PrismML's own fork (`README.md:50` lists
`https://github.com/PrismML-Eng/mlx-swift`), a different codebase from
`tijs/vmlx-swift` @ 44461ff — the upstream claim says nothing about this pin,
and this pin has no such type.

### 2.3 Registration status: `prism_hadamard_qwen35` is NOT registered anywhere

- LLM registry `LLMTypeRegistry` (`Libraries/MLXLLM/LLMModelFactory.swift`):
  `coreModels()` lines 24-73 (keys incl. `qwen3_5` → `Qwen35Model`, line 52;
  `qwen3_5_moe` → JANGTQ/plain dispatch, lines 53-71; `qwen3_5_text` →
  `Qwen35TextModel`, line 72), `extendedModels()` from line 76, shared instance
  = `coreModels().merging(extendedModels()).merging(additionalModels())`,
  lines 883-886. No `prism_hadamard_qwen35`.
- VLM registry `VLMTypeRegistry` (`Libraries/MLXVLM/VLMModelFactory.swift`):
  shared instance line 112-119; keys incl. `qwen2_vl`/`qwen2_5_vl`/`qwen3_vl`
  (128-130), `qwen3_5` (131), `qwen3_5_moe` (132), `qwen4_exp` (133), …
  no `prism_hadamard_qwen35`.
- Registry miss semantics are a **hard throw**, not a fallthrough to another
  model: `ModelTypeRegistry.createModel` (`Libraries/MLXLMCommon/Registries/
  ModelTypeRegistry.swift:53-61`) throws
  `ModelFactoryError.unsupportedModelType(modelType)` (line 57-59) when
  `creators[modelType]` is nil.

### 2.4 Factory ordering and fallback behavior (`MLXLMCommon/ModelFactory.swift`)

- Trampoline order: `ModelFactoryRegistry` (lines 1042-1071) registers
  **MLXVLM first** (1049-1053), **MLXLLM second** (1054-1057);
  `modelFactories()` (1067-1071) compactMaps both.
- Multi-factory iteration in the shared `load` helper (814-861): each factory
  is tried in order; `unsupportedModelType`/`unsupportedProcessorType`
  failures are recorded and the next factory is tried (834-845); when all
  factories fail, a real (non-unsupported) error **wins over** the unsupported
  error (854-857), else the unsupported error is thrown (856-857). Env
  `VMLX_MODEL_FACTORY_TRACE` prints the fall-through chain (816-820, 835-837).
- LLM factory `_load` (`LLMModelFactory.swift:1563…`): config.json decoded as
  `BaseConfiguration` (1790-1796; `modelType` required, `BaseConfiguration.swift:12,400`);
  `typeRegistry.createModel` with the root `model_type` (1848-1850); **on
  failure it retries `text_config.model_type`** (1855-1862) — this fallback is
  the wrong-model trap (see §3). Non-DecodingError rethrown as-is (1871).
- VLM factory `_load` (`VLMModelFactory.swift:430…`): decodes
  `BaseConfiguration` (445-451); `createModel(configuration:modelType:
  dispatchModelType)` (608-612); catches only `DecodingError` (613-616);
  **no `text_config` fallback** (only a `config_omni.json` override,
  lines 457-461, and jang_config metadata merge 470-589).
- Mei's entry: `Engine.load(config:)` (`Sources/MeiCore/Engine.swift:80-183`)
  calls free-function `loadModelContainer(from:using:loadConfiguration:)`
  (95-114) = `MLXLMCommon/ModelFactory.swift:515-527` → `loadModel` 582-592 →
  `loadModel` 596-… → the shared `load` iterator 814-861. Mei's loader does
  NOT consult `model_type` itself; rejection comes from the vmlx registry path.

## 3. What a real load attempt does TODAY (static prediction, NOT executed)

`prism_hadamard_qwen35` is unregistered, so a real `mei --model-dir <pack>`
load is predicted to fail loudly, never to serve silently wrong output:

1. **VLM factory first** → registry miss → `unsupportedModelType` recorded.
2. **LLM factory** → root `model_type = prism_hadamard_qwen35` → registry miss
   (`unsupportedModelType`) → **the `text_config` fallback fires**
   (`LLMModelFactory.swift:1855-1862`): the pack's `text_config.model_type =
   "qwen3_5_text"` (pack `config.json:90`) IS registered (line 72), so
   `Qwen35TextModel` gets constructed **from the pack's ROOT config data**.
   Every architecture field (`hidden_size`, `num_hidden_layers`, `vocab_size`,
   …) is `decodeIfPresent`-defaulted in
   `Qwen35TextConfiguration` (`Qwen35.swift:33-155`, e.g. defaults at
   110-114/127-130) and lives nested under `text_config` in the pack — so the
   fallback builds a **default-parameter** Qwen35TextModel (not the pack's
   5120/64-layer/248320-vocab shape). `tie_word_embeddings: false` keeps
   `lm_head` (`Qwen35.swift:1451-1453`).
3. **Weight load then hard-fails** (`loadWeights` at `Load.swift:257`, invoked
   from `LLMModelFactory.swift:2025-2034`; sanitize at `Load.swift:703`;
   standard affine quantize swap machinery ~1040-1166; final
   `model.update(parameters:verify: [.noUnusedKeys])` at `Load.swift:1173-1175`):
   the pack's tensors carry per-module `.signs` keys (written by
   `runtime/artifact.py:98-108`, read at `artifact.py:106`), the pack's
   `model.embed_tokens.{weight,scales,biases}` are 2-bit-packed (rows,
   width/16) uint32 arrays, and the default model has only 32 layers vs the
   pack's 64 — leftover `.signs` plus layers-32..63 keys plus any shape
   mismatch are not consumable parameters, and `.noUnusedKeys` verification
   rejects unknown keys (`Load.swift:136`, 1170-1175). Load ends in a thrown
   error.
4. Because the LLM factory's weight failure is a **real** error, the shared
   `load` helper prefers it over the unsupported error
   (`ModelFactory.swift:854-857`) — so the operator-seen message will be a
   weight/update failure, **not** a clean "unsupported model type". This masks
   the intended reject and is the first thing the implementation seam must fix.

Consequence: today's safe current behavior = **reject** (loud load failure at
weight application). No path exists in this pin that loads the pack and serves
output, with or without transforms. The Python-side claim in README:139-141
("return wrong output rather than an error") describes stock mlx-lm, whose
loader does not run vmlx's unused-key verification; it does not describe this
vmlx pin. Divergence is a fact, not a judgment: vmlx's verification semantics
are stricter.

## 4. Can standard affine loading honor the pack's custom modules/metadata?

**Numerics of the container: yes. Semantics of the model: no — and never will
without the transforms.** Concretely:

- The packed storage is byte-layout-identical to standard MLX affine
  bits=2/group_size=128 (`config.json:2529-2533`; `codec.py:29-30,45-49`;
  README:98-104). A stock 2-bit dequant (`mx.dequantize` /
  `QuantizedLinear`) recovers the exact ternary values (`{-s,0,+s}` via
  `bias = -s`).
- What stock affine loading cannot honor: (1) the **forward Hadamard
  activation transform** — `runtime.py:60-61` (`fwht(x, block, signs)`) before
  every packed projection matmul `runtime.py:62-70`; (2) the **inverse
  Hadamard transform on the embedding lookup** — `runtime.py:46-59`
  (dequantized `embed_tokens` rows are stored in the rotated basis and must be
  inverse-FWHT'd at forward); (3) the per-module `.signs` vectors
  (`artifact.py:106-108`, `hadamard.json` sign arrays) and the `modules[]` +
  `requires_runtime` + `hadamard_config` manifest contract
  (`artifact.py:81-85`, `PACK-RUNTIME.md:14-15`).
- In THIS vmlx pin the attempt additionally fails outright on verification
  (§3): `.signs` are unused keys under `verify: [.noUnusedKeys]`, so the pack
  can never load through the stock path even though the dequant math matches.
  A hypothetical pack stripped of `.signs` and shaped to a full 64-layer
  Qwen35 TextModel would still produce numerically-wrong output without the
  transforms — that is exactly why acceptance must be gated, not inferred.

## 5. Where the transforms would have to live (Swift side)

The pack's `modules[]` paths map 1:1 onto existing vmlx Qwen35 parameter
paths, so a load-time module swap (like the existing affine-quantize swap) can
install the transforms without touching layer forward code:

- `model.embed_tokens` → `Qwen35TextModelInner.embedTokens`
  (`Qwen35.swift:1094`, key `"embed_tokens"`; inverse-FWHT point = the
  embedding lookup inside `TextModelInner` forward, ~`Qwen35.swift:1114`/`1149`).
- `lm_head` → `Qwen35TextModel.lmHead` (`Qwen35.swift:1204`, key `"lm_head"`;
  forward-FWHT point = before `lmHead`, logits at 1224-1226 / 1255-1256).
- `model.layers.N.self_attn.{q,k,v,o}_proj` → `Qwen35Attention`
  (`Qwen35.swift:770-773`; FWHT point = inside each projection call).
- `model.layers.N.linear_attn.{in_proj_qkv,in_proj_z,out_proj}` →
  `Qwen35GatedDeltaNet` (`Qwen35.swift:198-208`; pack leaves
  `in_proj_a`/`in_proj_b`/`conv1d`/`norm` unquantized — matches README:87
  "26.2M params remain in higher precision").
- `model.layers.N.mlp.{gate,up,down}_proj` → dense `Qwen3NextMLP` mounted as
  `mlp` in `Qwen35DecoderLayer` (`Qwen35.swift:908-…`, mlp at ~930).
- `model.norm` (RMSNorm, unquantized) and all norm layers: untouched.

The FWHT primitive is already exposed to Swift:
`hadamardTransform(_:scale:stream:)`, `Source/MLX/Ops.swift:1577-1584`
(binding of the MWC FWHT in `Source/Cmlx`). The rotation/sign handling
(`x * signs` before/after the normalized transform, fp32 staging) is exactly
`runtime.py:16-28` and has no existing Swift equivalent in this pin.

## 6. Smallest isolated implementation seam + fallback/rollback boundary (NOT implemented)

Three seams, listed so the implementer can pick the smallest that satisfies
"feature-gated, never silently wrong". No code was written.

1. **Registry/dispatch seam** (`MLXLLM`): add a `prism_hadamard_qwen35` entry
   to `LLMTypeRegistry` (`LLMModelFactory.swift:24-73` or
   `additionalModels()`, merged at 883-886) via a peek-dispatcher, following
   the existing "peek `weight_format`" precedents (`qwen3_5_moe`,
   `LLMModelFactory.swift:53-71`; `minimax_m2`, 114-131), gated on
   `requires_runtime == "runtime/artifact.py"` +
   `schema_version`/`hadamard_config` presence. **Mandatory companion gate**:
   exclude `prism_hadamard_qwen35` from the `text_config` fallback
   (`LLMModelFactory.swift:1851-1872`) so the pack can never quietly become a
   default-parameter `Qwen35TextModel` (§3 trap). VLM side, when vision is in
   scope: new key in `VLMTypeRegistry` (`VLMModelFactory.swift:112-119`) —
   current VLM `_load` has no text fallback (608-616), so the VLM side is a
   pure registry addition.
2. **Weight/transform-install seam** (`MLXLMCommon/Load.swift`): a
   feature-flagged branch in `loadWeights` (`Load.swift:257`; hook after
   sanitize, 703, before the affine quantize swap ~1040-1166): read
   `modules[]` + per-module `.signs` + `hadamard.json`, swap in Hadamard-aware
   modules (forward-FWHT packed linear; inverse-FWHT packed embedding),
   consume/remove the `.signs` keys so the final
   `model.update(verify: [.noUnusedKeys])` (`Load.swift:1173-1175`) passes,
   and suppress/adapt the standard affine QuantizedLinear swap for packed
   paths. Validation mirror of the bundled runtime: schema_version=2,
   model_type exact, block ∈ {512,1024,2048,4096}, signs ±1, module path
   resolvable (`runtime/artifact.py:81-85,104-108`; `vision_artifact.py:23-28`).
3. **Transform modules seam** (new, in `MLXLLM`): `HadamardActivation` +
   packed linear/embedding modules implementing `runtime.py:16-70`
   semantics on `hadamardTransform` (`Source/MLX/Ops.swift:1577`).

**Fallback/rollback boundary (explicit):** the feature flag lives in the
Mei/vmlx load path only, **default OFF**, with no change to shipped Mei
defaults (per the hard rule in `bonsai2-mlx-mei-follow-on.md:108-110`). When
OFF: current behavior is unchanged — hard reject at weight application
(§3). When ON, every validation failure above (manifest, signs, shape, module
resolution, schema) aborts the load with a `configurationDecodingError`-class
error — never a partial model, never unverified forward. Rollback = flag OFF +
re-verify the §3 reject path still rejects. No new Mei `ServerConfig` surface
is required to gate; **no x shipment default changes**.

Mei-side static predictions for the pack (line-cited, unexecuted):
`ModelOptimizationProfile.detect` resolves it to **generic** — only
`qwen3_5_moe`/`qwen3_5_moe_text` map to ornith (`ModelOptimizationProfile.swift:92-97`);
generic prefill step 64 (`19-21`). `needsDiskKVTier` would be **TRUE** because
`collectedModelTypes` collects ALL nested `model_type`s
(`ModelOptimizationProfile.swift:159-171, 225-241`) and the pack carries
`text_config.model_type = "qwen3_5_text"` (`config.json:90`) and
`vision_config.model_type = "qwen3_5"` (`config.json:2552`), both members of
`diskKVRequiredModelTypes` (`ModelOptimizationProfile.swift:135-137`) — so
`ServerConfig.swift:342-347` would auto-assign a disposable KV dir before the
load fails anyway (`kvCacheDir` default `""`, `ServerConfig.swift:69`;
`cacheReuse` default true, line 53). Cache tier wiring if load ever succeeds
would be paged+disk as configured at `Engine.swift:123-139` (vmlx
`CacheCoordinatorConfig` defaults `usePagedCache=false`,
`enableDiskCache=false`, `CacheCoordinatorConfig.swift:103-116`, both
overridden by Mei).

## 7. Required future gates (definition of done for the follow-on)

All against the pinned pack revision and pinned Mei/vmlx revisions; each gate
must produce committed, reproducible evidence. None ran in this unit.

1. **Exact identity/load** — served model id; config hash pinned; `schema_version 2`,
   `model_type prism_hadamard_qwen35`, `requires_runtime` honored; load
   succeeds only under the feature flag; flag-off re-verifies the §3 reject.
2. **Deterministic text parity vs the bundled runtime** — reference outputs
   generated with the pinned Python runtime (`artifact.load_model` /
   `vision_artifact.load_vl_model` per `PACK-RUNTIME.md:6-12`, in a later unit
   that installs the pinned `runtime/requirements.txt`) compared
   token-for-token at greedy temp-0 against the Swift path; logits checked
   where the runtime exposes them (`artifact.py:122-143` reload-validation
   pattern).
3. **Plain + streaming generation** — non-stream and SSE stream, identical
   content, deterministic sampling config.
4. **Native non-streaming AND streaming tool calls** — vmlx tool parsing via
   the existing path (`Engine.swift` chatRun paths; tool format for
   `qwen3_5`-lineage), both response modes.
5. **Growing-cache reuse** — paged + disk tiers per `Engine.swift:123-139`
   (vmlx `CacheCoordinatorConfig`), multi-turn transcripts, cached-token
   counts recorded; `gdn_activation_layout: grouped` respected per
   `PACK-RUNTIME.md:14`.
6. **Context boundary** — `mei --context-cap` vs pack
   `max_position_embeddings: 262144` (`config.json:89`), over-cap rejection
   (`EngineError.overContextCap`, `Engine.swift:18`).
7. **Active memory** — `Memory.snapshot` reports (`Engine.swift:196-207`),
   active/cache/peak vs the pack's ~8.6 GB footprint + KV.
8. **Three repeats: throughput / TTFT / end-to-end** — 3× each per the
   benchmark methodology, rows kept SEPARATE and UNRANKED until gates pass.
9. **Teardown** — server stop, temp KV dirs (`ServerConfig.swift:345-346`),
   allocator/cache state, transcripts archived per `local-model-bench/AGENTS.md`.

Rollback boundary (§6) is re-verified after every implementation step: flag
OFF must reproduce the current hard reject.

## 8. Verification ledger (what actually ran in this unit)

- Read-only git checks: `git rev-parse HEAD` / `git status --short` /
  `git log --oneline -3` on local-model-bench (clean, HEAD as §1), mei
  (`950e8c2…`, untracked `Casks/` + `tap/` unchanged), vmlx-swift checkout
  (`44461ff…`).
- Read-only source searches/reads: vmlx registries, factory `_load`s, weight
  path, Qwen35 config/model, Mei Engine/ServerConfig/ModelOptimizationProfile;
  `grep -rc prism_hadamard|hadamard_qwen` = 0 matches; whole-checkout
  case-insensitive `hadamard` scan (no `PrismHadamardConfiguration`).
- Read-only HTTPS fetches (stdout pipes, nothing saved to disk, no payload):
  README.md (lines cited), `config.json` (2,565 lines), `runtime/artifact.py`,
  `runtime/runtime.py`, `runtime/codec.py`, `runtime/vision_artifact.py`,
  `runtime/requirements.txt`, `hadamard.json` (parsed: block 1024, 401 folded
  names, inverse=[embed_tokens], 28,672 ±1 signs), `PACK-RUNTIME.md`, HF tree
  API at the pin (25 paths).
- **Explicitly NOT run in this unit:** no local model load, no probe, no
  benchmark, no server, no payload download, no install, no build of
  Mei/vmlx, no CoCore, no Kiem mutation, no publish/push.

## Source URLs (all at the pinned revision)

- Pack tree: `https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit`
- Pin commit: `…/commit/3f926b415992eaa2ae9dd7b573706494d6bbf787`
- Raw files: `…/raw/3f926b415992eaa2ae9dd7b573706494d6bbf787/{README.md,config.json,PACK-RUNTIME.md,hadamard.json,runtime/artifact.py,runtime/runtime.py,runtime/codec.py,runtime/vision_artifact.py}`
- Local checkouts (read-only): `/Users/tijs/projects/mei` @ `950e8c2…`;
  `/Users/tijs/projects/mei/.build/checkouts/vmlx-swift` @ `44461ffd…`
  (Mei `Package.swift:19-20`).
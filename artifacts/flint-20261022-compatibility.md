# Flint 40B-A2.5B × Mei: loadability and quant compatibility — 2026-10-22

**Verdict:** source-level Flint support is **absent in the audited Mei/vMLX pin**. Prefer the standard `mlx-community/flint-mixed-3-4bit` affine bundle for a **first, feature-gated integration attempt**, not as an already-loadable model. Its optimistic staging estimate leaves only **9.141067 GiB** free (the handoff's approximately 9.15 GiB), below the unchanged **10 GiB** floor. The smaller JANGH2 bundle has a different packed-key/quantization contract and is **not compatible with this pin without a new pack path**. No weights have been downloaded, staged, loaded, served, or benchmarked for this audit.

This is a documentation-only, metadata/source audit, not an integration, admission result, or ranking. The user still wants to try Flint despite the space concern; that intent is preserved without waiving the resource gate or claiming a successful load.

## 1. Exact reference boundary and pins

| Component | Immutable reference / verification |
|---|---|
| Benchmark repository base | `local-model-bench@57ca14ffb0585f92583e12afb4aba0956128054b`; primary `main` worktree was clean at dispatch and initial readback. This artifact is authored in a separate worktree/branch. |
| Mei source audited | `tijs/mei@6b632ebea3b2b843085ad4f37a0e75b31df3e4d7`, matching the locally recorded `origin/main`. Source was read with `git show <exact-commit>:<path>`, not assumed from the primary working tree. |
| Mei checkout caveat | `/Users/tijs/projects/mei` actually had HEAD `ffe9eede34a072c99829d1509af3cb7235b16038`, 14 commits behind that `origin/main`, with existing untracked research files. The pre-existing `/Users/tijs/projects/mei-flint-20261022` was separately verified at `6b632ebea3b2b843085ad4f37a0e75b31df3e4d7`. Neither checkout was edited by this task. |
| vMLX dependency audited | `tijs/vmlx-swift@633fe166630ef04310aea7d5a1795555ab32970d`; verified both the Mei reference's `Package.resolved:211–218` and the actual detached, clean `/Users/tijs/projects/mei/.build/checkouts/vmlx-swift` HEAD before source inspection.[30] |
| Base-model metadata | `RecursiveSI/flint@2a247be0c0aec895ccb0ac7ca92229ec6df37288`; resolved through Hub metadata, then reread at that immutable revision.[23] |
| External Python reference | `Blaizzy/mlx-vlm` **v0.7.10** is a reference for future architecture/parser work, not the Mei runtime. The community card says Flint is supported in mlx-vlm 0.7.10+ (`README.md:30–59`); that claim is not Swift compatibility or a local verification.[2] |

The pinned dependency's `AGENTS.md:6–28` restricts its active modification lane to the Gemma 4 QAT correctness checkpoint. This audit does not edit or stage Mei, vMLX, their dependency graph, or their build checkouts.[41]

## 2. Candidate selection and quant compatibility matrix

**Exact identities and LFS totals** (not rounded card sizes, tensor-only payload totals, all-file totals, or RAM requirements):

| Candidate | Immutable HF revision | Exact sum of LFS object bytes |
|---|---|---:|
| **Preferred first integration:** `mlx-community/flint-mixed-3-4bit` | `b1c305855ae7c3464813815be4dbd544b22c36aa` | **17,848,619,410** — four safetensors shards plus `tokenizer.json`.[1] |
| **Not the first Mei path:** `OsaurusAI/Flint-40B-A2.5B-JANGH2` | `8bfb25587388c6a235e58338a6c926da000bded9` | **13,204,590,640** — four safetensors shards plus `tokenizer.json`.[8] |
| **Official, not first resource-fit:** `RecursiveSI/flint-int4` | `3b93f9053b530488405ae9fca51d4900d6ce21f0` | **22,580,201,966** — five safetensors shards, `tokenizer.json`, and an LFS logo asset.[16] |

| Candidate | Source-backed format / contract | Reported quality and memory evidence | Verdict against the pinned Mei/vMLX source |
|---|---|---|---|
| Community mixed 3/4-bit | Standard MLX affine mixed quantization: global **4-bit, group 64**, **141 routed-expert projection overrides at 3-bit, group 64**, plus **8-bit, group-64 embedding**. Parsed from `config.json:130–701`; the `quantization_config` block at `config.json:702–1273` mirrors that plan. Index keys use ordinary `.weight` / `.scales` / `.biases`, not JANGH keys. The pinned decoder defaults an omitted mode to affine (`Libraries/MLXLMCommon/BaseConfiguration.swift:14–64`).[4][6][45] | **Community-reported, not independently verified on M1 Max/Mei:** 6/6 toy coding checks and approximately **19.5 GB peak** on **M5 Max 64 GB**. The card explicitly calls this a small check, not SWE-bench/Terminal-Bench, and says no real 24 GB Mac was tested (`README.md:20–28,63–73,105–126`).[2] | **Preferred integration candidate, not loadable as-is under the pin.** Familiar affine packaging removes the *custom JANGH pack* problem, not the missing Flint architecture, tensor-shape/sanitization, kernel, tokenizer, parser, cache, or memory proofs. Staging is still below the normal disk reserve. |
| JANGH2 | Custom `jang_config.json` **`format="jangtq2"`**, **`profile="JANGH2"`**, Hadamard-32 codebook experts; mixed routed widths **98 projections at 2-bit, 39 at 3-bit, 4 at 4-bit**. The config and index expose **`.tq2_packed` / `.tq2_scales`** for 141 projections each. Non-expert quantization is affine 8-bit, group 64 (`jang_config.json:1–16,121–123`; config/index parsed at the pin).[13][11][14] | **Vendor-reported, not reproduced here:** **89.5% top-1 agreement versus BF16**, on **96 held-out sessions / 253,155 positions**; this is teacher-forced agreement, not a canonical agent benchmark. Card runtime requirement: **Osaurus 0.25.25+** (`README.md:28–46,49–71,99–105`).[9] | **Not compatible with this pin without a new pack path; do not call it loadable.** No `tq2_packed` / `tq2_scales` support was found in the audited source. Existing JANGTQ modules/streaming code expect `.tq_packed` / `.tq_norms`; the audited routed-width dispatcher explicitly accepts 2/4, not this mixed 2/3/4 pack. See §3. Its smaller bytes do not establish Mei support. |
| Official INT4 | Official MLX group-64 affine INT4 projections/experts, INT8 embeddings (`README.md:14–18`; `config.json:80–102,128–131`).[17][19] | No local M1 Max/Mei footprint or full benchmark exists for this artifact. Its card's approximately 22.6 GB is an on-disk figure, not a complete memory budget.[17] | **Not the first resource-fit choice for 32 GiB.** Larger than the preferred quant, still lacks the Flint implementation in this pin, and leaves only 4.734437 GiB by the same optimistic LFS subtraction. No loadability or 32 GiB residency claim. |

### Shared architecture that an implementation must actually honor

The preferred quant declares **`model_type="flint"`**, **`architectures=["FlintForCausalLM"]`**, **49 layers**, **256 experts / top-6**, **35 sliding + 14 full-attention layers**, and **sliding window 513**. The first two layers are dense, followed by 47 MoE layers; the 141 projection overrides cover those 47 layers' gate/up/down projections. These are parsed config/card facts, not runtime-tested topology (`config.json:2–4,24–79,103–127,1284–1292`; base `README.md:34–54`).[4][24]

The base documents 39.8B total / approximately 2.5B active parameters, shared experts, QK RMSNorm, learned attention sinks, and RoPE only on sliding layers; its nominal **262,144-token** context is not a locally admitted context cap. A generic MoE class or a renamed sibling `model_type` is not evidence that these semantics match (`README.md:20–24,34–54,98–102`).[24]

Do not compare community toy-check retention against JANGH2's BF16 agreement as if they used the same baseline, evaluator, hardware, or serving path. Neither is a local canonical benchmark result.[2][9]

## 3. Exact Mei/vMLX registry and pack audit

Source paths below are relative to the named repository and tied to §1's commits; numbered links resolve to those immutable files.

| Audit point | Exact source evidence | Finding / status |
|---|---|---|
| Mei load entry point | Mei `Sources/MeiCore/Engine.swift:102–138` calls `loadModelContainer(from:using:loadConfiguration:)` on the local bundle directory.[31] | Mei delegates loading to vMLX; this entry point does not add a Flint creator or an explicit Flint parser configuration. |
| Registry lookup | vMLX `Libraries/MLXLLM/LLMModelFactory.swift:19–25,890–894,1452–1464,1940–1956`; `Libraries/MLXLMCommon/Registries/ModelTypeRegistry.swift:49–61` selects `creators[modelType]`, otherwise throws `unsupportedModelType`.[32][42] | **No Flint registration/class found.** The source-level absence is a compatibility blocker, not an observed failed live load. No error message from an unperformed load is claimed. |
| Negative-search scope | Read-only `git grep` at the exact Mei/vMLX commits: no case-insensitive literal `flint`, `tq2_packed`, or `tq2_scales` matches across **53 Mei / 1,185 vMLX tracked Swift files**. Broader `Libraries`, `Sources`, and `Source` searches likewise returned exit 1 / zero matching lines. | Covers the exact tracked sources, including LLM/VLM registries; not every future revision, external binary, or Osaurus release. Reproduce with the commands below. |
| Public model-type extension | vMLX `Libraries/MLXLMCommon/Registries/ModelTypeRegistry.swift:14–38` exposes public actor initializers and both `registerModelType` overloads; `Libraries/MLXLLM/LLMModelFactory.swift:890–894,1452–1464` exposes `LLMTypeRegistry.shared` and public factory construction.[42][32] | A **proposed Mei-side, default-off feature-gated implementation/registration** can target these APIs before loading, without editing the dependency just to register a type. Complete architecture/API feasibility still needs code, focused tests, consumer build, and live load. Registration alone supplies no architecture implementation. |
| Public factory extension / ordering | vMLX `Libraries/MLXLMCommon/ModelFactory.swift:829–874,1037–1085` exposes `ModelFactoryTrampoline`, `ModelFactoryRegistry.shared.addTrampoline`, and `modelFactories()`. Defaults enumerate VLM then LLM; added trampolines append; loading returns the first successful factory.[33] | An app-level custom factory is another proposed extension point, **not automatic priority replacement** and not established Flint compatibility. Preserve default/flag-off behavior and prove actual factory selection in any future integration. |
| Existing JANGTQ packed names | vMLX `Libraries/MLXLMCommon/JANGTQDenseLinear.swift:44–75` registers `tq_packed` and `tq_norms`; `Libraries/MLXLMCommon/JANGTQStreamingExperts.swift:233–249` filters exactly those suffixes, including stacked `switch_mlp` keys.[35][36] | JANGH2's `tq2_packed` / `tq2_scales` do not match that contract. A name-only substitution would not prove rotation, scales, codebook, or bit packing parity. |
| Existing routed-width dispatch | vMLX `Libraries/MLXLLM/LLMModelFactory.swift:640–706`, specifically `671–678`, documents the DSV4 JANGTQ dispatcher convention: `validRoutedBits = [2, 4]`; 3-bit converter packing is explicitly not shipped there.[32] | Existing JANGTQ support for other families does **not** validate JANGH2's mixed 2/3/4 Hadamard-32 pack. A new, exact-format path plus numerical/streaming proof is required, in addition to Flint itself. |
| Ordinary mixed-affine plumbing | vMLX `Libraries/MLXLLM/LLMModelFactory.swift:2117–2134` forwards per-layer quantization; `Libraries/MLXLMCommon/Load.swift:1113–1137` resolves a module's own group size, bits and mode.[32][46] | Positive **source-level plumbing evidence only** for choosing the standard quant first. It does not prove this model's dimensions, module keys, 3-bit execution, sanitization, or real checkpoint load. |

Reproducible negative-search method (read-only; **exit 1 means no matches**, not a command failure to hide):

```bash
git -C /Users/tijs/projects/mei grep -n -i -F flint \
  6b632ebea3b2b843085ad4f37a0e75b31df3e4d7 -- '*.swift'
git -C /Users/tijs/projects/mei/.build/checkouts/vmlx-swift grep -n -i -F flint \
  633fe166630ef04310aea7d5a1795555ab32970d -- '*.swift'
# Repeat each query with tq2_packed and tq2_scales.
# git ls-tree -r --name-only <commit>, filtered by .swift, gives 53 / 1185.
```

## 4. Tool, reasoning and sampling compatibility

| Contract | Source / resolution | Integration verdict |
|---|---|---|
| Tool parser precedence | vMLX `Libraries/MLXLLM/LLMModelFactory.swift:2002–2035`: **caller-supplied `ModelConfiguration.toolCallFormat` first**, then JANG `chat.tool_calling.parser`, then capability/template-aware resolution, then model-type inference. `flint` is absent from `ToolCallFormat.infer` (`Libraries/MLXLMCommon/Tool/ToolCallFormat.swift:347–543`). The template fallback in `Libraries/MLXLMCommon/JangLoader.swift:522–589` recognizes MiniCPM5/XML-function/bare-JSON forms; its JSON rule excludes `<arg_key>`, and it has no GLM arg-key inference branch.[32][38][37] | Do not assume generic inference will choose a Flint GLM parser. JANGH2 declares `tool_parser="glm47"`, but parser metadata does not fix its incompatible pack. |
| Flint tool grammar | Preferred bundle `chat_template.jinja:8–24,38–53` specifies `<tool_call>name<arg_key>k</arg_key><arg_value>v</arg_value></tool_call>` and observation replies; JANGH2 card `README.md:107–119` names this GLM-4.7 format. vMLX `Libraries/MLXLMCommon/Tool/Parsers/GLM4ToolCallParser.swift:5–29,49–134` implements the corresponding envelope and schema-aware values; `ToolCallFormat.swift:262–263` maps `.glm4` to it.[3][9][39] | **Proposed explicit `.glm4` configuration**, followed by model-free and live buffered/streaming tool tests, including string/numeric/JSON values, multiple calls, and tool-result history. Matching syntax is not tested end-to-end compatibility. |
| Mei can supply explicit configuration | vMLX `Libraries/MLXLMCommon/ModelConfiguration.swift:153–173` accepts `toolCallFormat` and `reasoningParserName`; `Libraries/MLXLMCommon/ModelFactory.swift:529–547` offers the directory overload with both `configuration: ModelConfiguration` and `loadConfiguration: LoadConfiguration`.[34][33] | A future Mei call can pass `ModelConfiguration(directory: ..., toolCallFormat: .glm4)` through that overload while retaining load controls. Current audited `Engine.load` uses the overload without those parser overrides; **nothing has been wired or applied here**. |
| Thinking is model-generated | Bundle `chat_template.jinja:38–40,59–61` preserves historical reasoning but ends the generation prompt at `<\|assistant\|>`, without prefilling `<think>`. The card says Flint writes `<think>…</think>` itself, has **no reasoning toggle or effort levels**, and decides per turn (`README.md:107–118`).[3][9] | No forced think opener/closer, synthetic effort setting, or sibling thinking toggle is justified. Validate both turns that reason and plain answers, preserving reasoning in history. |
| Reasoning parser semantics | vMLX `Libraries/MLXLMCommon/ReasoningParser.swift:1072–1086` resolves raw `think_xml` with **`startInReasoning=true`**; `1199–1247` makes `forPrompt` start outside reasoning when a nonempty prompt tail contains neither tag, but absent/empty tail retains the stamp default. `Libraries/MLXLMCommon/JangLoader.swift:393–442` also detects literal think tags in a template and can choose `qwen3`; `LLMModelFactory.swift:2056–2095` respects an explicit reasoning override before this fallback.[40][37][32] | **`think_xml` is only a possible explicit parser override after validating the exact parser call path and prompt-tail semantics.** Do not describe the raw stamp as “starts in content.” Automatic `qwen3` selection from template text is also not Flint correctness proof. Test no-reasoning answers, split markers, tools, history, and visible/reasoning channel separation before adoption. |
| Sampling defaults | Exact preferred bundle `generation_config.json:10–13`: **`do_sample=true`, temperature 1.0, top_p 0.95, top_k 20**. vMLX reads that file and attaches `generationDefaults` (`Libraries/MLXLLM/LLMModelFactory.swift:1974–1980,2153–2162`).[5][32] | These are **bundle defaults, not applied benchmark settings**. No Flint config or request profile has been created. Future work must inspect effective request payloads in every suite rather than assuming server/bundle defaults win. |

## 5. Captured host state and unchanged disk gate

**Parent-captured preflight, supplied with this task:** M1 Max, **32 GiB** unified memory; free disk **27,015,396 KiB**; free + inactive RAM **15.298 GiB**; no target benchmark/server process or listener on the benchmark ports (`8012/8016/8017/8018/8020/8024/8025/8026/8027`). This is a dated observation, **not** a fresh launch authorization or a continuously true state; other source/build work can change it. Free + inactive RAM is not the GPU working-set limit or a verified model-residency budget.

The benchmark's pinned `runner/bench_common.py:69–76` sets `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 10.0`, explicitly keeping staging/download accounting separate. The existing Flint Kiem plan `b1c17085-5904-455b-9222-e59b1599562f`, lines 20–25 at audit time, additionally requires **at least 10 GiB remaining after staging**. Neither gate is waived by this artifact.[44]

Using **KiB = 1,024 bytes** and **GiB = 1,073,741,824 bytes**, captured free disk is **27,663,765,504 bytes**. These are **optimistic LFS-only** estimates, before non-LFS bundle files, filesystem overhead, scratch, build, runtime or cache allocations:

| Candidate | LFS bytes to stage | Free bytes after subtraction | Free GiB | Normal reserve verdict |
|---|---:|---:|---:|---|
| Preferred community mixed quant | 17,848,619,410 | **9,815,146,094** | **9.141067** | **Below 10 GiB** by at least **922,272,146 bytes**, plus unaccounted overhead. |
| JANGH2 | 13,204,590,640 | 14,459,174,864 | 13.466156 | LFS-only disk arithmetic clears 10 GiB; **runtime/pack compatibility does not**. Not selected as a disk-driven substitute. |
| Official INT4 | 22,580,201,966 | 5,083,563,538 | 4.734437 | Below reserve; not first resource-fit. |

The community card's approximately 19.5 GB M5 Max peak is a vendor/community measurement, not a bound for M1 Max, Swift/Mei, first-load materialization, physical footprint, long-context KV, or the benchmark workload. No safe-residency, speed, or full-context claim follows from either the LFS size or the host's physical RAM.[2]

**Current gate:** preserve the preferred candidate and the user's intent to try it; keep download/staging/load/serve/benchmark **pending**. Recheck exact disk, memory, process ownership and ports before any later action; establish the full staging/scratch budget and satisfy the standing floor, or obtain an explicit policy decision outside this task. Do not silently lower the floor, delete unrelated files/caches, alter a sibling lane, or begin a partial download.

## 6. Status / next-proof matrix

| Gate | Status at this audit | What is still required (not executed here) |
|---|---|---|
| Immutable candidate and format selection | **Metadata verified; community affine quant preferred provisionally.** | Preserve separate exact identities/provenance for every quant; do not merge their evidence. |
| Flint source support in the Mei pin | **Absent.** | Proposed default-off Mei-side implementation/registry extension; architecture/config/quantization/sanitization and parser tests; exact consumer dependency/build verification. |
| JANGH2 support in this pin | **Not compatible without new pack support, plus the missing architecture.** | Separate exact Hadamard-32 mixed-width implementation and parity/admission work if later authorized. It is not the first Mei path. |
| Disk reserve for preferred snapshot | **Fails captured LFS-only post-staging estimate.** | Fresh accounting that leaves at least 10 GiB, without unauthorized deletion or policy changes. |
| Model weights / verified staged payload | **Pending; none downloaded or staged by this audit.** | Exact revision, complete files/index, bytes/digests, alignment and provenance verification after permission/resource gates. |
| Runtime build, model load and generation | **Pending; not performed.** | Reviewed/committed implementation, tested consumer build and correct runtime resources, then one bounded real load/plain generation with footprint and speed evidence. |
| Serving, native tools, reasoning and multi-turn | **Pending; not performed.** | Exact identity; buffered/streaming text and tools; reasoning separation/history; cache/context boundary and teardown checks. |
| Canonical benchmark config / rows / ranking | **Pending; no new config, result row or leaderboard change.** | Separately authorized committed config, effective sampler audit, unchanged canonical gates and complete suite evidence. No full benchmark or suitability verdict yet. |

## 7. Discovery correction

The base repository's metadata reports **2026-10-21T14:24:03Z** as its last modification, inside the Oct 22 scan's seven-day window. The retained scan report, `/Users/tijs/.hermes/cron/output/qwen-moe-discovery/2026-10-22.md:5–7,11–18,26`, does not list Flint and explicitly records HTTP 429 / fallback searches, empty searches and incomplete coverage. This is a **discovery miss, not an earlier rejection**.[23][43]

Do not backdate today's exact quant selection: the selected community revision's metadata reports **2026-10-22T11:47:07Z**, after the **08:00 CEST** scan. That distinction does not erase the missed in-window base release. The report read for this audit has SHA-256 `83f39c6a9cf5bcca3da4a1efb8d6521f6ba899c7ce0bd42a1d89e2b86613fa20`.[1][43]

## 8. Methods, limitations and primary links

- Retrieved Hub revision metadata (`?blobs=true`) and only allowlisted text/config/template/index files; summed every `siblings[].lfs.size` programmatically and asserted the three expected totals. **No tensor shards, full tokenizer payload, model download command, conversion, model server or benchmark was run.** LFS totals include the tokenizer and, for official INT4, a logo; they are not shard-payload-only sizes.
- Parsed JSON to verify layer counts, every per-module bit/group override, index key suffixes and shard names. The standard plan has 141 q3 projection overrides plus one q8 embedding override; JANGH2 has 98/39/4 routed projection widths and 141 of each `tq2_*` key. **Metadata was not checked against actual tensor headers or numerical outputs.**
- Audited pinned Git objects and recorded source `file:line` evidence rather than treating a moving branch or a successful package claim as compatibility. Source searches and public APIs establish a proposed route only; no Swift build/tests, kernel execution, live load, admission probe, M1 Max footprint, or benchmark score is claimed.
- Kept this task to a single documentation artifact. No Mei/vMLX edits, benchmark/config/result changes, CoCore action, cleanup, public push or GitHub API activity is part of it. Existing Kiem plans were read, not edited.

Primary entry points (use the pinned revisions above for evidence):

- Base: <https://huggingface.co/RecursiveSI/flint>
- Preferred standard quant: <https://huggingface.co/mlx-community/flint-mixed-3-4bit>
- JANGH2: <https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2>
- Official INT4: <https://huggingface.co/RecursiveSI/flint-int4>
- Python implementation reference: <https://github.com/Blaizzy/mlx-vlm/tree/v0.7.10> — reference-only; its code was not fetched or executed by this audit. The version/support attribution comes from the pinned community card, not an independent mlx-vlm verification.[2]

## Sources

[1] https://huggingface.co/api/models/mlx-community/flint-mixed-3-4bit/revision/b1c305855ae7c3464813815be4dbd544b22c36aa?blobs=true
[2] https://huggingface.co/mlx-community/flint-mixed-3-4bit/raw/b1c305855ae7c3464813815be4dbd544b22c36aa/README.md
[3] https://huggingface.co/mlx-community/flint-mixed-3-4bit/raw/b1c305855ae7c3464813815be4dbd544b22c36aa/chat_template.jinja
[4] https://huggingface.co/mlx-community/flint-mixed-3-4bit/raw/b1c305855ae7c3464813815be4dbd544b22c36aa/config.json
[5] https://huggingface.co/mlx-community/flint-mixed-3-4bit/raw/b1c305855ae7c3464813815be4dbd544b22c36aa/generation_config.json
[6] https://huggingface.co/mlx-community/flint-mixed-3-4bit/raw/b1c305855ae7c3464813815be4dbd544b22c36aa/model.safetensors.index.json
[8] https://huggingface.co/api/models/OsaurusAI/Flint-40B-A2.5B-JANGH2/revision/8bfb25587388c6a235e58338a6c926da000bded9?blobs=true
[9] https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2/raw/8bfb25587388c6a235e58338a6c926da000bded9/README.md
[11] https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2/raw/8bfb25587388c6a235e58338a6c926da000bded9/config.json
[13] https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2/raw/8bfb25587388c6a235e58338a6c926da000bded9/jang_config.json
[14] https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2/raw/8bfb25587388c6a235e58338a6c926da000bded9/model.safetensors.index.json
[16] https://huggingface.co/api/models/RecursiveSI/flint-int4/revision/3b93f9053b530488405ae9fca51d4900d6ce21f0?blobs=true
[17] https://huggingface.co/RecursiveSI/flint-int4/raw/3b93f9053b530488405ae9fca51d4900d6ce21f0/README.md
[19] https://huggingface.co/RecursiveSI/flint-int4/raw/3b93f9053b530488405ae9fca51d4900d6ce21f0/config.json
[23] https://huggingface.co/api/models/RecursiveSI/flint/revision/2a247be0c0aec895ccb0ac7ca92229ec6df37288?blobs=true
[24] https://huggingface.co/RecursiveSI/flint/raw/2a247be0c0aec895ccb0ac7ca92229ec6df37288/README.md
[30] https://github.com/tijs/mei/blob/6b632ebea3b2b843085ad4f37a0e75b31df3e4d7/Package.resolved
[31] https://github.com/tijs/mei/blob/6b632ebea3b2b843085ad4f37a0e75b31df3e4d7/Sources/MeiCore/Engine.swift
[32] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLLM/LLMModelFactory.swift
[33] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/ModelFactory.swift
[34] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/ModelConfiguration.swift
[35] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/JANGTQDenseLinear.swift
[36] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/JANGTQStreamingExperts.swift
[37] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/JangLoader.swift
[38] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/Tool/ToolCallFormat.swift
[39] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/Tool/Parsers/GLM4ToolCallParser.swift
[40] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/ReasoningParser.swift
[41] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/AGENTS.md
[42] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/Registries/ModelTypeRegistry.swift
[43] file:///Users/tijs/.hermes/cron/output/qwen-moe-discovery/2026-10-22.md
[44] https://github.com/tijs/local-model-bench/blob/57ca14ffb0585f92583e12afb4aba0956128054b/runner/bench_common.py
[45] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/BaseConfiguration.swift
[46] https://github.com/tijs/vmlx-swift/blob/633fe166630ef04310aea7d5a1795555ab32970d/Libraries/MLXLMCommon/Load.swift

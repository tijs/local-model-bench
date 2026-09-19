# Bonsai-2 (Ternary-Bonsai-2-27B-mlx-2bit) exact-65,536 OOM diagnosis — 2026-09-19

**Verdict (bounded unit):** the exact-context-cap (65,536-token) result is a **model/runtime
memory-capacity blocker on this 32 GiB Apple-GPU device**, not a loader, protocol, or harness
failure. The candidate stays **gated / unranked**. No source change and no full rerun are
recommended in this unit; the only credible future step is a scratch aligned-repack +
capacity-boundary probe, with the pinned model untouched.

**Sections keep three evidence classes strictly separate:** measured facts (raw artifacts),
source-derived inference (labeled), and hypotheses (labeled). No exact per-token memory formula
is claimed — source-derived arithmetic appears only where labeled.

---

## 1. Scope and boundary

- Target repo: `/Users/tijs/projects/local-model-bench`, clean at `e06017e`
  (verified `git status --short` empty before this note).
- Gate source overlay used by the run: `vmlx-swift-bonsai-prism@6a81ca32656fc2dc824c589f88e7d5541158c224`
  (record.json:37); the temporary compiler-only Evaluate.swift overlay was restored in the source
  checkout (record.json:38-43).
- Pinned model files untouched: revision `3f926b415992eaa2ae9dd7b573706494d6bbf787`,
  sha256 `130de5925082c168b7866b2e91b52e44abbafc99017e3ca352b77b5b55a269ed` (record.json:7-8).
- No ranking or full-suite benchmark rows exist: record.json:25 `"ranking": "unranked; no
  benchmark rows appended"`, record.json:26 `"result": "partial_gate_blocked"`.

## 2. Measured facts (raw evidence)

Evidence root:
`/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-6a81-20260919T073150Z-partial-gate-oom/`
(`server.log`, `probe.json`, `record.json`, `mei-help.txt`).

### Device and memory budget

- Device: `applegpu_g13s`, **34,359,738,368 B** GPU memory (probe.json:103-104, server.log:10).
- Memory limit in effect: **24,051,816,857 B**; cache limit 32,641,751,449 B;
  recommended working set 26,800,603,136 B (probe.json:107-117, server.log:11).
  Derived: limit = 0.70×device, cacheLimit = 0.95×device (arithmetic from the two measured
  numbers); the limit sits **2,748,786,279 B below** the loader's own recommended working set.
- Memory after load: active 7,616,367,636 B, cache 0, peak 0 (server.log:11, probe.json:108-109).
  Measured active growth at later points: 8,448,465,948 B after the 828-token growing-turn
  (probe.json:16), 10,565,569,564 B after the 6,212-token repeat prefill (probe.json:57).
  Buffer-pool (`cache`) and peak values: 12,662,498,740 B / 13,615,435,372 B at 828 tokens
  (probe.json:17-18), 6,045,782,240 B / 13,615,435,372 B at 6,212 tokens (probe.json:58-59).

### Load path

- 1 of 1 shard unaligned; **1,253 tensors / 6,834,034,688 B realigned into RAM** at load
  (server.log:2, server.log:5 — `realigned 1253 unaligned tensor(s) (6834034688 bytes)`; the
  loader's own warning at server.log:2 says realignment "costs memory ... and can exhaust the
  GPU allocator outright").
- 402 packed 2-bit modules installed from 1,608 checkpoint keys (server.log:6); load completed
  and the server started listening on 127.0.0.1:8027 (server.log:9, server.log:12).
- Safe settings that ran: `VMLX_BONSAI_PRISM_HADAMARD=1`, `VMLX_ENABLE_UNSAFE_COMPILE=0`,
  `compiled-decode=false`, prefill step 1,024, disk-backed KV cache dir
  `mei-runtime-bonsai2-prism-6a81-direct-retry/kv-cache` (record.json:28-36, server.log:1,8,12).

### The failing boundary

- Exact-cap probe: 65,536-token prompt via `/v1/completions`, max_tokens 1
  (runner/probe_mei.py:374-391). Chunked prefill advanced in 1,024-token steps through
  **35,840/65,536** (server.log:55-90, last completed step at server.log:90) then the Metal
  command buffer failed:
  `MLX/ErrorHandler.swift:343: Fatal error: [METAL] Command buffer execution failed:
  Insufficient Memory ... eval.cpp:51` (server.log:91). Client saw
  `RemoteDisconnected: Remote end closed connection without response` (probe.json:90-94).
- The server process exited on the OOM; therefore the subsequent 65,537-token over-cap
  rejection probe could not run: `URLError: <urlopen error [Errno 61] Connection refused>`
  (probe.json:95-99). Over-cap rejection is **not independently verified** in this run.

### Everything else passed

Probe statuses (record.json:11-24, probe.json): 10 of 12 probe slots `passed`
— `mei_status`, `models_identity`, `plain_completion`, `tool_nonstreaming`,
`tool_streaming`, `parity_stream_vs_nonstream`, `cache_repeat_1`, `cache_repeat_2`,
`cache_growing_turn1`, `cache_growing_turn2_reuses_slot`; only `context_exact_cap` failed,
and only because the server died before it could be tried. Cache reuse worked: 6,207/6,212
cached tokens at 18,447 tok/s prefill vs 96.9 tok/s fresh (probe.json:69-88); 823/851 cached in
the growing-turn slot (server.log:42-54, probe.json:29-49). Native tool calling validated both
streaming and non-streaming with correct `add_numbers(15, 27)` calls (probe.json:187-290).

## 3. Source-derived inference (labeled)

- **Architecture split:** config.json (pinned model dir) `model_type = prism_hadamard_qwen35`,
  nested `text_config.model_type = qwen3_5_text`, `num_hidden_layers = 64`,
  `layer_types = {linear_attention: 48, full_attention: 16}`, `full_attention_interval = 4`,
  `num_key_value_heads = 4`, `head_dim = 256`. Source: `isLinear =
  (layerIdx + 1) % fullAttentionInterval != 0` → 48 GatedDeltaNet (linear-attention) layers and
  16 full-attention layers (vmlx-swift-bonsai-prism `Libraries/MLXLLM/Models/Qwen35.swift:919-926`).
  This matches the served topology tags `layers=64 kvLayers=16 mambaLayers=48 companion=ssm
  restore=disk-backed` (server.log:8), which `topologyTags` emits from the recorded cache-layer
  counts (ModelContainer.swift:118-143).
- **Which cache each layer gets (the key wiring):** `Qwen35.newCache`
  (Qwen35.swift:1397-1419) gives every linear layer a `MambaCache()` unconditionally — the
  comment (1402-1403) states Mamba layers "ignore the bound by design (their hidden state is
  fixed-size)" — and gives attention slots a `RotatingKVCache` only when `maxKVWindowSize`
  or `maxKVSize` is set, else `KVCacheSimple`. `MambaCache` is an `ArraysCache` with 2
  fixed slots (conv state + SSM state) (KVCache.swift:1729-1739). Consequence: the 48
  linear-attention layers are **not** bounded by `--max-kv-window` or `--kv-bits` controls.
- **Attention-ring arithmetic (config-derived, labeled):** fp16 KV ring for the 16 full-attention
  layers with 4 KV heads × head_dim 256 × (K+V): ≈ 4.0 GiB at 65,536 tokens, ≈ 2.25 GiB at
  36,864, ≈ 0.38 GiB at 6,212. The machine-measured active growth between 828 and 6,212 tokens
  was ~2.1 GB — far larger than the ~0.38 GiB ring at 6,212 — so the ring is **not** the dominant
  growth term; the dominant term is prefill workspace over the growing prefix
  (see Hypotheses).
- **Realignment cost:** the 6,834,034,688 B realigned at load are allocator-owned RAM copies of
  unaligned payload (server.log:2,5 + `mei/tools/align_safetensors.py:1-30` motivation — the
  align tool's docstring documents this realignment behavior and its own measured payload
  identity check; the helper is a header-padding repack, payload bytes bit-identical,
  payload sha256-verified). Removing them would drop load-time allocator pressure by up to
  ~6.36 GiB (derived from the measured byte count) — a real lever for the boundary, but **not a
  cure**: it does not remove the measured per-token working-set growth.
- **Probe ordering (harness):** runner/probe_mei.py executes
  `models_identity` (187) → `mei_status` (201) → `plain_completion` (221) →
  `tool_nonstreaming` (253) → `tool_streaming` (259) → `parity_stream_vs_nonstream` (291) →
  `cache_repeat_1/2` (305) → `cache_growing_turn1` (340) → `cache_growing_turn2_reuses_slot`
  (359) → `context_exact_cap` (391) → `context_over_cap_rejected` (409). The context pair runs
  last, so the OOM killed only the tail of the battery, not the admission surface.

## 4. Hypotheses (labeled; not resolved in this unit)

- The OOM driver is the **per-chunk prefill working set over the growing prefix**: the 16
  full-attention layers scan the full ring per 1,024-token chunk (attention-score material for
  ~24 heads × 1,024 queries × growing key count per layer pass, plus GatedDeltaNet scan
  temporaries), and MLX retains freed buffers in the pool (measured 12.6 GiB pool after the
  828-token turn). Together they push the cumulative working set past the 24.05 GB allocator
  limit somewhere in the 35,840→36,864-token window.
- The exact byte-per-token mix (ring vs workspace vs pool retention vs GDN state) is **not**
  decomposed here; no formula is claimed.

## 5. Why the usual knobs do not credibly make exact 65,536 fit here

- **Raising `--memory-limit-bytes`:** the limit already is 0.70× of the same physical 34.36 GB
  (derived), 2.75 GB below the loader's recommended working set; raising it only re-partitions
  the same physical memory and cannot add capacity that the device does not have. The failure
  is a physical-capacity boundary ~55% into the target context, not a too-low arbitrary cap.
- **`VMLX_ENABLE_UNSAFE_COMPILE=1` / `--compiled-decode true`:** compile knobs govern the decode
  path (mei-help.txt:74-79; server.log:1 ran `compiled-decode false`). The OOM fired inside
  `pp stage=prefill` (server.log:55-91), not decode, so they do not lower the failing working
  set; unsafe compile additionally trades numerical safety for graph leniency and is not a
  memory lever for prefill.
- **`--max-kv-window N`:** source (Qwen35.swift:1405-1416) applies it only to the 16
  attention slots as a `RotatingKVCache` ring; the 48 linear layers ignore it by design.
  The ring at cap is ≤ ~4 GiB (derived) — a minority of the exhausted budget — and the control
  is explicitly correctness-bounded (mei-help.txt:80-82), i.e. it changes attention semantics
  versus the plain/parity contract the gate measures. It cannot bound the dominant term.
- **`--kv-bits 4/8`:** quantized KV touches attention KV only (topology `quantizedKVLayers`;
  this run ran fp16, server.log:12 `kv-bits none`, mei-help.txt:33-35). Even at 4-bit the
  ceiling on savings is the ring bytes (~4 GiB fp16 → ~2 GiB), while measured growth blocks
  prefill that far outpaces the ring; no credible path to 65,536.
- **Smaller `--prefill-step-size`:** changes the transient per-chunk workspace, not the
  cumulative working-set requirement. The run advanced 35 full 1,024-chunks and died on the
  36th — the failure is on cumulative growth, so re-chunking at best moves the boundary a
  little and does not make 65,536 fit.
- **The one credible lever — aligned repack (future, scratch only):** removing the 6.36 GiB
  realigned live allocation (server.log:2,5; `mei/tools/align_safetensors.py` header-padding
  repack with payload sha256 identity, file lines 1-30) could materially extend the boundary.
  Whether it crosses 65,536 is exactly what a future capacity-boundary probe on a **scratch
  repack** would measure. It does not cure per-token growth and is not a source change.

## 6. Admission status (kept separate from the context boundary)

The functional admission surface is intact and stands on its own:
identity, plain completion, streaming parity, native tools (both modes), and cache
reuse/prefix-slot growth — 10 passed probe slots (record.json:11-24). The failed
`context_exact_cap` and the un-runnable `context_over_cap_rejected` are a single
context-boundary pair, caused by the model/runtime capacity limit; they carry **no**
implication for any passed boundary. The candidate is **exact-cap-blocked, unranked**, and no
ranking/full-suite rows exist (record.json:25-26), so no leaderboard/appendix entry is affected.

## 7. Next action (explicit)

1. **Keep the candidate gated/unranked.** Do not append rows, do not rank, do not treat the
   over-cap rejection as verified.
2. **Queue any real long-context remedy as a separate future research item** (e.g. an
   architecture-level bounded-window/quantized-state path for the 48 linear-attention layers,
   or a larger-device validation) — out of scope for this unit.
3. **At most** a future scratch aligned-repack + capacity-boundary probe (model files pinned
   and untouched; repack into a scratch directory; measure where prefill now fails) to quantify
   the realignment contribution to the boundary.
4. No source change and no full rerun in this bounded unit.

## 8. Evidence index

| Fact | Raw evidence (exact path:lines) |
|---|---|
| OOM at 35,840→36,864 window, fatal Metal "Insufficient Memory" | `.../prism-6a81-20260919T073150Z-partial-gate-oom/server.log:55-91` |
| Device 34,359,738,368 B; limit 24,051,816,857 B; after-load active 7,616,367,636 B | `server.log:10-11`; `.../probe.json:100-122,107-118` |
| Realignment 1,253 tensors / 6,834,034,688 B; 1/1 shard unaligned warning | `server.log:2,5` |
| Topology `layers=64 kvLayers=16 mambaLayers=48 companion=ssm restore=disk-backed` | `server.log:8`; source `ModelContainer.swift:118-143` |
| 48 linear / 16 full layers, `full_attention_interval=4`, KV heads 4, head_dim 256 | pinned `config.json` `text_config`; source `Libraries/MLXLLM/Models/Qwen35.swift:919-926` |
| Linear layers get unbounded `MambaCache`; attention only honors max-kv-window | `Qwen35.swift:1397-1419`; `KVCache.swift:1729-1739` |
| Probe order (context pair last) | `runner/probe_mei.py:187,201,221,253,259,291,305,340,359,391,409` |
| all-non-context probes passed; over-cap un-runnable after server exit | `probe.json:90-99` + statuses; `record.json:11-24` |
| Unranked, no benchmark rows | `record.json:25-26` |
| Safe settings | `record.json:28-36`; `mei-help.txt` (kv-bits 33-35, memory 51-55, max-kv-window 80-82, prefill 30-32) |
| Aligned-repack option (payload-identity, header-padding) | `/Users/tijs/projects/mei/tools/align_safetensors.py:1-30` (docstring + verification), warning at `server.log:2` |
| Gate source commit, overlay restored | `record.json:37-43` |

*Note: `server.log` and `probe.json` line numbers refer to the raw files as read on 2026-09-19;
`Qwen35.swift` / `ModelContainer.swift` / `KVCache.swift` lines refer to
`vmlx-swift-bonsai-prism@6a81ca32656fc2dc824c589f88e7d5541158c224`; `probe_mei.py` lines refer to
`local-model-bench@e06017e`.*
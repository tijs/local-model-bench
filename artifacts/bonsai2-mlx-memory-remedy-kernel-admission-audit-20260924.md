# Bonsai2 MLX — Steel full-attention kernel-admission CPU/source audit (2026-09-24)

**Status: CPU/source audit only, following the 2026-09-24 runtime kernel-admission
failure.** This artifact documents why the live kernel was refused by the Metal device
and derives one candidate tile shape that fits the hardware maximum. It is **not a
fix claim**: the candidate is a *derived candidate*, not a working tile, and nothing
here was implemented, built, run, or measured. This document is evidence for the next
unit of work, not benchmark/ranking evidence.

Fact discipline used throughout: **measured** (recorded by the live gate or verified
on disk this unit) vs **derived** (source arithmetic, computed in this audit) vs
**unverified** (hypothesis, explicitly labeled).

## 1. Scope, pins, and clean read-only state

- Audit window: 2026-09-24 (CEST, UTC+02:00). Read-only work only, in
  `/Users/tijs/projects/local-model-bench`; the vmlx tree was referenced read-only.
- vmlx pin (measured, re-verified this unit):
  `/Users/tijs/projects/vmlx-swift-bonsai-prism` HEAD
  `746d1c47f89db29c33ea1174e01e35fc219d5b01` (branch `bonsai2-prism-hadamard-slice`),
  `git status --porcelain` **clean** before/after this audit.
- Nested MLX pin (measured, re-verified this unit): `Source/Cmlx/mlx` submodule
  `a2829e90878a7354f2668831af1409b3972a3c2f` (v0.31.1-19-ga2829e908); companion
  `Source/Cmlx/mlx-c` submodule `7bede8f1491384bb580f87d1d510f80cbd53660d`.
- Source/build unit: `local-model-bench` HEAD `5e03c0d`; the failing binary was the
  fresh Mei consumer build `mei-build-bonsai2-prism-746d1c47-20260924`
  (SHA-256 `2fe43a77…5845b28`), built against vmlx `746d1c47`.
- **Nothing changed anywhere.** No implementation, no build, no GPU run, no model
  load, no benchmark rows, no ranking, no Mei `main` change, no public action, and
  no write to vmlx/mlx/Mei/configs/runner/model caches/`results/`/`log.jsonl`
  occurred in this audit. The only write is this artifact.

## 2. Measured failure (recorded by the live admission gate)

- Live gate: `artifacts/bonsai2-mlx-memory-remedy-live-gate-20260924.md`
  (evidence dir `results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-746d1c47-20260924T001206Z-live-admission/`,
  `server.log`).
- Refused kernel (measured, exact name from `server.log`):
  `steel_attention_float32_bq32_bk16_bd256_wm4_wn1_maskfloat32_align_Q_n_align_K_n_has_mask_n_do_causal_t_has_sinks_n`,
  at first plain request (57 tokens, `pp stage=prefill completed=0 total=57`), released
  as: `Threadgroup memory size (53760) exceeds the maximum threadgroup memory allowed
  (32768)`, host GPU `applegpu_g13s`; process exited Trace/BPT trap
  (`MLX/ErrorHandler.swift:343`, `transforms.cpp:73`).
- So **measured max threadgroup memory on this device = 32,768 B**, and the **measured
  demand of the bq32/bk16/bd256/wm4/wn1 instantiation = 53,760 B**. This is a
  kernel-admission (Metal pipeline-load) refusal, not a long-context OOM; prefill was
  at `completed=0`.
- Note (measured): the refusal occurred at pipeline load, so this run did reach kernel
  acquisition — the shape compiled/registered but Metal refused to load it into the
  device.

## 3. Derived source arithmetic (this audit; consistent with the measured 53,760 B)

Threadgroup allocation, `Source/Cmlx/mlx/mlx/backend/metal/kernels/steel/attn/kernels/steel_attention.h`
lines 111-124 (read-only, verified at mlx a2829e908):

```
111  constexpr short padQ = 16 / sizeof(T);   // padK, padV likewise (112-113)
115  constexpr short LDQ_tgp = BD + padQ;     // 116: LDK_tgp = BK + padK
117  constexpr short LDV_tgp = BD + padV;
119  constexpr short tgp_mem_0 = (BK + padK) * (BD);
120  constexpr short tgp_mem_1 = BK * (BD + padV);
121  constexpr short tgp_mem_s = tgp_mem_0 > tgp_mem_1 ? tgp_mem_0 : tgp_mem_1;
123  threadgroup T Q_smem[BQ * (BD + padQ)];
124  threadgroup T KV_smem[tgp_mem_s];
```

Derived byte formula for this float32 path (T = float, `sizeof(T)` = 4, so
padQ = padK = padV = 4):

```
bytes = 4 * BQ * (BD + 4) + 4 * max((BK + 4) * BD, BK * (BD + 4))
```

| Shape (bq, bk, bd, wm, wn) | Q_smem | KV_smem (max) | Total (derived) | vs 32,768 B |
|---|---|---|---|---|
| 32, 16, 256, 4, 1 (live) | 4·32·260 = 33,280 B | 4·max(20·256, 16·260) = 20,480 B | **53,760 B** | **exceeds by 20,992 B** |
| 16, 8, 256, 2, 1 (candidate) | 4·16·260 = 16,640 B | 4·max(12·256, 8·260) = 12,288 B | **28,928 B** | fits, 3,840 B headroom |

Consistency check (derived vs measured): the formula reproduces the recorded 53,760 B
exactly for the bq32 instantiation, with no other threadgroup allocations, confirming
the two buffers are the whole footprint.

What dispatch produced the live shape — `scaled_dot_product_attention.cpp`
(read-only, verified at mlx a2829e908):

- lines 195-200: `wm = 4; wn = 1; bd = q.shape(-1); bq = 32; bk = bd < 128 ? 32 : 16;`
  → for head_dim 256: bd=256, bk=16, bq=32, wm=4, wn=1 — exactly the refused kernel name.
- lines 324-325: `grid_dims = MTL::Size(NQ, H, B); group_dims = MTL::Size(32, wm, wn)`.

**Why bq=32 cannot fit even with a smaller bk (derived):** the Q smem term
`4 · BQ · (BD+4)` is independent of bk, wm, and wn. At the model-mandated bd = 256
(head_dim is fixed by the model config; bd cannot shrink without changing attention
semantics), bq=32 alone costs 33,280 B — already above the 32,768 B maximum before any
KV smem is counted. No bk or warp-split choice helps; bq itself must drop. (At
bd=256 even the theoretically minimal bk contributes `4·(bk+4)·256 ≥ 4,096 B`.)

## 4. Why the candidate (bq=16, bk=8, bd=256, wm=2, wn=1) at 28,928 B is derived-legal

- Fits: 28,928 B ≤ 32,768 B (3,840 B headroom) — derived, steel_attention.h:111-124.
- Existing divisibility/static-assert assumptions hold (derived, steel_attention.h:
  169-184): with `kFragSize = 8`, `kNWarps = WM·WN = 2`,
  `static_assert(BQ ≥ kNWarps·8 && BQ % (kNWarps·8) == 0)` → BQ=16 satisfies
  (16 ≥ 16, 16 % 16 == 0), and `static_assert(TQ == 1)` with
  `TQ = BQ / (kNWarps·8) = 1` ✓. `TK = BK/8 = 1` ✓, `TD = BD/8 = 32` ✓.
- Existing tail/alignment machinery is shape-generic (derived,
  `scaled_dot_product_attention.cpp:210-214`, 273-298): `align_Q = (qL % bq) == 0`,
  `align_K = (kL % bk) == 0`, and unaligned tails are handled through
  `NQ_aligned`/`qL_rem`/`kL_rem` params plus `loader_*.load_safe` — a smaller bq/bk
  only changes which instantiation (align_Q_n/align_K_n) is selected, e.g. 57 tokens
  with bq=16 → `align_Q_n` (57 % 16 = 9), exactly the machinery the live run already
  exercised for bq=32 (57 % 32 = 25).
- Loader threadgroup sizes: `BlockLoaderT tgp_size = WM·WN·32` (steel_attention.h:
  131-157) = 64 threads for wm=2/wn=1, divisor of BQ=16 rows and BD=256 cols.
- Smaller launch: `NQ = ceil(qL/bq)` (scaled_dot_product_attention.cpp:273) grows the
  grid (more, smaller tiles); that is a performance consideration, not a legality one.

**Verdict: the candidate is derived-consistent with the existing kernel, loader,
and dispatcher contracts, and fits the hardware maximum — nothing more is claimed.**

## 5. NAX is not an alternate route on this path (derived)

`scaled_dot_product_attention.cpp:178-179`:

```
178  if (metal::is_nax_available() && q.shape(3) != 80 &&
179      (env::enable_tf32() || q.dtype() != float32)) {
```

For this plain-float32 path with TF32 not enabled, the last conjunct is false, so the
NAX full-attention arm is unreachable **on any device** for this dtype/settings —
gen-13 `is_nax_available()` is moot here (whether gen-13 supports NAX at all is
separate and **unverified**, and irrelevant to this path). Note also
`q.shape(3) != 80` is satisfied (256), so the dtype/tf32 condition is the only guard
in the way; enabling TF32 or a non-float32 dtype would be a semantic change, not a
remedy.

## 6. Smallest future source change (hypothesis, not executed)

- The minimal, isolated change is a **default-off dispatch choice** in
  `scaled_dot_product_attention.cpp` lines 195-200 — e.g. selecting
  (bq=16, bk=8, wm=2, wn=1) for the head_dim-256 case under an experiment flag —
  gated so the shipped default tiles are untouched.
- Kernel/loader/MMA changes are **not justified yet**: steel_attention.h's static
  asserts and the generic tail/mask/causal machinery already accept the candidate
  shape; the only line-level edits would live in the dispatcher tile defaults.
- No-JIT instantiation is **optional and only if needed**: the
  `MLX_METAL_JIT` build path (`CMakeLists.txt:38-40`, `make_jit_source(steel/attn/kernels/steel_attention)`
  at line 84; `jit_kernels.cpp:1079`) JIT-compiles the shape on demand, while the
  no-JIT flavor (`CMakeLists.txt:99-101`; `nojit_kernels.cpp:397`) requires the exact
  kernel name + function-constants hash to be preloaded. Only in a no-JIT consumer
  build would registration of the new shape be required.

## 7. Risks (unverified until exercised — the candidate is not a working tile)

- **JIT/compile:** a never-before-instantiated shape compiles at first prefill
  (one-time latency), or fails kernel lookup in a no-JIT build if not registered.
- **Tail/mask correctness:** smaller bq/bk change which align_Q/align_K instantiation
  and tail-tile behavior (`load_safe`, `qL_rem`/`kL_rem`) is exercised; causal and
  additive-mask paths (steel_attention.h:238-321, 324+) must still produce identical
  outputs; nothing here validates that.
- **Slower tiles:** bq16/bk8/wm2 tiles increase the number of threadgroups per token
  and reduce MMA work per tile vs bq32/bk16/wm4 — an expected throughput regression,
  unquantified.
- **No numeric/perf/live evidence:** no fused-vs-dense parity, no throughput, no live
  run exists for any 256-head-dim tile. All behavioral claims are hypotheses.

## 8. Next gates (unchanged plan, now concrete)

1. **Static/CPU validation** — model-free checks of the dispatch change (isolated,
   default-off), including re-review of the derived 28,928 B arithmetic and
   divisibility asserts on the exact pinned sources.
2. **Fresh consumer build** — new throwaway checkout at these exact pins (vmlx
   `746d1c47` / mlx `a2829e908`), patched locally, rebuilt from scratch; never reuse
   the crashed `mei-build-bonsai2-prism-746d1c47-20260924` binary.
3. **Disk gate** — restore free disk to **>= 10 GiB** (measured 9.7 GiB after the last
   attempt; no retry while below the line).
4. **Bounded live admission** — only then, still non-rankable: one isolated admission
   with exact provenance, compared against the recorded blocker; success requires the
   new kernel to load and produce output consistent with a reference path.

## 9. Explicit non-changes statement

No implementation, build, GPU run, model load, benchmark rows, ranking, Mei `main`
change, or public action occurred in this audit. No kernel/loader/MMA source was
edited; vmlx and Mei trees are untouched and clean; no files were staged or committed.
The proposed tile is a **derived candidate**, not a working tile — no claim is made
that it loads, compiles, or produces correct numerics until gates 1-4 produce evidence.
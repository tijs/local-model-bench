# Bonsai 2 MLX / Mei follow-on direction, 2026-09-18

> **SCOPE UPDATE 2026-09-24 — active scope of this note.** Per explicit user
> direction, further research for the **Gravity** arm and the **Bonsai 2 GGUF
> (PTQ1_0)** follow-on is **DISCARDED**; those scopes are closed
> (`configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml` and
> `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml` are retired
> `orchestration.viable: retired`, 2026-09-24). The **only active target** is
> the Bonsai 2 27B MLX pack on Mei/vmlx — exactly
> `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` @
> `3f926b415992eaa2ae9dd7b573706494d6bbf787` (section 2 below). Section 1
> (bounded GGUF baseline policy) and section 4 step 1 (baseline-queue-first)
> are **CLOSED / SUPERSEDED** and are retained below as historical policy only;
> all other facts, claims, and URLs in this note are unchanged historical
> content.

Priority change (parent direction, 2026-09-18): the Bonsai 2 27B GGUF/llama.cpp
leg is a BOUNDED baseline comparison only — do not spend disproportionate time
on it. Once the currently queued baseline legs (including Bonsai 2) are
terminal, the MAIN goal is configuring and optimizing the MLX Bonsai 2 pack on
Mei/vmlx. This note makes that durable. Kiem: benchmark plan
`7f5c67e7-b564-4df3-8209-14f7443b56e2` (new open todo), Mei plan
`32c2e458-a97f-4733-8003-ade438f1c01c` (new open portability todo).

Nothing ran in this unit: no model weights, no Prism/MLX binaries, no server,
no probe, no benchmark, no cache cleanup. All upstream facts below were
verified READ-ONLY against the HuggingFace API and the raw README AT the pinned
revision on 2026-09-18 (no download of the model payload). **Local measurements:
NONE yet.**

## 1. ~~Bounded GGUF / llama.cpp baseline policy (the queued PTQ1_0 leg)~~ — CLOSED / SUPERSEDED 2026-09-24

> **CLOSED 2026-09-24:** the Bonsai 2 GGUF (PTQ1_0) baseline leg and the
> Gravity follow-on are DISCARDED by user direction — no runs, no expansion,
> and no further research under this policy. The policy text below is retained
> verbatim as a historical record of what was previously authorized; it is not
> current direction.

The queued PrismML Bonsai 2 GGUF candidate
(`configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`, committed f1d450d) stays
a bounded baseline comparison, NOT an MLX-evidence leg:

- Run the exact queued PTQ1_0 artifact (prism-ml/Ternary-Bonsai-2-27B-gguf @
  `6ed5e12bf84b7a63069882c91dd9e9218647d17b`, file
  Ternary-Bonsai-2-27B-PTQ1_0.gguf, 5,946,648,928 bytes, sha256
  53107f53…) on the pinned PrismML llama.cpp fork (`llama.cpp-prism` engine,
  tag prism-b10687-5d80cff / commit 5d80cff0…) ONLY AFTER the AXQ6 leg
  (`7f5c67e7` todo 20) is terminal, independently reviewed, and committed.
- Gate before any baseline rows: native identity (exact served model),
  plain + streaming generation, native non-streaming/streaming tool calls,
  growing-conversation cache reuse, and context boundary, on the pinned fork
  binary — plus a SMALL TIME-BOXED canary.
- Do NOT automatically expand this leg to a full 25-row battery. Expansion is
  allowed only when the gate/canary gives a DOCUMENTED reason; otherwise stop
  at the bounded baseline.
- Keep this leg's `llama.cpp-prism` rows SEPARATE and UNRANKED — never merged
  with stock `llama.cpp` rows, never merged with the MLX follow-on's rows.
- The GGUF leg is a baseline comparison only; it is NOT evidence for the MLX
  pack (different format, runtime, quant family, and loader path).

Source: the committed config + model card +
`https://github.com/PrismML-Eng/Bonsai-demo` (runtime/serving source of truth,
upstream claim), all as recorded in the config's `settings/` and `known_gaps`
at f1d450d.

## 2. Primary ACTIVE follow-on MLX target (the only active target; no GGUF baseline prerequisite)

> **ACTIVE 2026-09-24:** this is the only active target in this note. Exactly
> `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` @
> `3f926b415992eaa2ae9dd7b573706494d6bbf787`, on Mei/vmlx. The GGUF baselines
> (section 1) and section 4 step 1 no longer gate or precede this work.

- Repo: `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit`
  (https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit)
- Immutable revision: `3f926b415992eaa2ae9dd7b573706494d6bbf787`
  (https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit/commit/3f926b415992eaa2ae9dd7b573706494d6bbf787)
  — verified 2026-09-18: HF API `sha` == this revision (also the repo's current
  HEAD at check time), tree at the pin lists 23 files.
- Root artifact: `model.safetensors` = **8,595,477,990 bytes** (HF tree API at
  the pin, LFS)
- `model_type`: **prism_hadamard_qwen35** (HF tags + README at the pin)
- License: **Apache-2.0** (HF metadata + README frontmatter)
- Base model: **Qwen/Qwen3.8-27B** (https://huggingface.co/Qwen/Qwen3.8-27B;
  HF `base_model` metadata)
- Pack layout: root `config.json`, `tokenizer.json`, `tokenizer_config.json`
  AND a bundled `runtime/` package (`LICENSE`, `requirements.txt`,
  `artifact.py`, `codec.py`, `runtime.py`, `vision_artifact.py`) — verified via
  the HF tree API at the pin. The README Quickstart installs
  `runtime/requirements.txt` and imports the bundled runtime directly.
- README at the pin: `library_name: mlx`, `pipeline_tag: text-generation`,
  tags include `ternary`, `2-bit`, `mlx`, `metal`, `hybrid-attention`,
  `prismml`, `bonsai`; the pack advertises text and vision (mlx-vlm) usage.

All of the above are UPSTREAM CLAIMS verified read-only against HF metadata at
the pin; NOT local measurements.

## 3. Upstream README fact: stock MLX loaders return WRONG output

The pack's README at the pinned revision states (upstream claim, quoted):

> This pack declares `model_type: prism_hadamard_qwen35` and **requires the
> loader bundled in `runtime/`**. Ordinary MLX loaders skip the activation
> transform and the inverse embedding lookup, so they return wrong output
> rather than an error.

Consequence for Mei/vmlx: **compatibility with `prism_hadamard_qwen35` must be
source-audited and implemented/gated, never assumed.** Mei/vmlx does not
presently claim support for this model type in any repo evidence; there is NO
local load, gate, or benchmark row for the MLX pack in this repository. Do not
claim Mei already supports `prism_hadamard_qwen35`, and do not copy the
bundled upstream runtime code — use a clean-room/source-backed portability
review (Mei plan todo, below).

## 4. Staged follow-on sequence (MLX pack on Mei/vmlx)

1. ~~**Baseline first:** finish and review the current serialized baseline queue
   (AXQ6 -> bounded Bonsai 2 PTQ1_0 GGUF -> Gravity RL Q4_K_M -> gated BF16
   Gravity Base, as applicable). The MLX follow-on depends on terminal/reviewed
   baseline legs.~~ **SUPERSEDED 2026-09-24:** the GGUF baseline legs (Bonsai 2
   PTQ1_0 GGUF, Gravity RL Q4_K_M, gated BF16 Gravity Base) are DISCARDED and
   their scopes closed (configs retired 2026-09-24); the MLX follow-on NO
   LONGER depends on any GGUF baseline leg — proceed directly with the MLX pack
   target in section 2.
2. **Isolated Mei/vmlx loader/transform compatibility work** — source audit of
   the activation transform + inverse embedding lookup requirement; implement
   and gate behind a feature flag in an isolated worktree, with a fallback.
3. Exact identity/load against the pinned revision.
4. Plain + streaming generation.
5. Native non-streaming AND streaming tool calls.
6. Growing-conversation cache reuse.
7. Context boundary.
8. Active memory.
9. Deterministic output / parity.
10. Three-repeat throughput / TTFT / end-to-end measurements.
11. Fallback/rollback.

Hard rules: do NOT change shipped Mei defaults, do NOT enable unsafe
compile/CoCore, keep the candidate unranked until gate + bounded evidence
under current methodology exist, and keep the GGUF leg's rows separate.

## Source URLs

- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit
- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit/commit/3f926b415992eaa2ae9dd7b573706494d6bbf787
- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-mlx-2bit/raw/3f926b415992eaa2ae9dd7b573706494d6bbf787/README.md
- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf (GGUF baselines)
- https://github.com/PrismML-Eng/Bonsai-demo (README-declared source of truth
  for running/serving the pack — upstream claim)
- https://huggingface.co/Qwen/Qwen3.8-27B (base model)
- Kiem plans: `7f5c67e7-b564-4df3-8209-14f7443b56e2` (benchmark),
  `32c2e458-a97f-4733-8003-ade438f1c01c` (Mei)

## Verification status

- UPSTREAM claims (format/repo/size/model_type/license/base/tags/README
  loader warning): verified read-only against HuggingFace API + raw README at
  the pinned revision, 2026-09-18. The exact README sentence about ordinary
  MLX loaders returning wrong output was read verbatim from the pinned
  revision's README.md.
- LOCAL measurements: **none** — no download, no load, no gate, no benchmark.

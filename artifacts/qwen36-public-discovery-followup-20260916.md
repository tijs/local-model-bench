# Qwen3.6 track — public-discovery follow-up, 2026-09-16

CPU-only discovery follow-up to `qwen36-public-discovery-audit-20260916.md`,
based on the parent orchestrator's verified local facts and a read-only
Hugging Face metadata scan (GET-only API, no weights downloaded). **No code was
implemented, no model/server/probe was launched or stopped, no benchmark ran,
no download/install happened, no cache was deleted, no results/config/
selection/runner/task/check/leaderboard change occurred, and no Kiem, Mei
checkout, GitHub action, push, or CoCore side effect happened.** The only
repository write is this artifact, committed as one scoped report-only commit.
Source labels: **Measured** = verified local facts this tick (parent-verified
at dispatch and/or re-checked read-only here); **Public metadata** = Hugging
Face API/card records (card claims are recorded precisely but are NOT
benchmark evidence); **Decision** = this report's judgment.

Report date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench`.

## Verified (Measured)

- Checkout: HEAD `d0c7c154251754cd43c44d5ba4da485664f36e12` (d0c7c15), branch
  `main`, ahead 38, working tree clean; no benchmark/model process and no
  listener on benchmark ports 8012, 8016, 8017, 8018, 8020, 8024–8027.
- `results/log.jsonl` unchanged: **4,064 total rows, 916 Qwen3.6 rows**;
  latest Qwen3.6 row `2026-09-14T09:40:08Z` → no run since the prior audit.
  Raw inventory: **45 Qwen3.6 groups, 18 complete zero-harness groups**.
  OptiQ remains **coding-only** (20 rows under config hash `31a7f0b6a256`:
  14/15 + 3/5; no `sanity`/`hermes_ops` rows) → not eligible.
- OptiQ fresh-KV acceptance config hash **`6011477d1711`**, identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, port 8024 — **no result rows and
  no config snapshot yet**. ManniX gate remains exploratory only; **no rows**.
- Free disk: **27,307,180,032 bytes ≈ 25.435... GiB** (df can drift by MB),
  below runner `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GB. With the 20 GiB
  post-download floor, no candidate is stageable unless its selected file is
  ≤ about 5.8 GB; every serious 27–32B candidate below is much larger.
- Current Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`; Kiem
  reconciliation is owned by the parent and a candidate todo is a
  parent/Kiem decision.

## Changed

- Created and committed **exactly one artifact**:
  `artifacts/qwen36-public-discovery-followup-20260916.md` (this file).
  No other file staged; `git diff --check` clean; no amend/bundle of unrelated
  changes. Commit SHA: see commit message/handoff.

## Public candidate scan (Public metadata + Decision)

Seven-day window 2026-09-09T08:00Z – 2026-09-16T08:07Z; HF API search returned
100 records, sorted by lastModified. Exact immutable revisions and
artifact/tree sizes read from the HF tree endpoint at that revision. Sizes are
public metadata; performance/quality card claims are **public claims only**:

1. **GhannsLt layer-wise hybrid** @ `caa7ca96ddb3c78798b0f0555a663755b29d57b6`
   — base `Qwen/Qwen3.6-35B-A3B`; single `Qwen3.6-35B-A3B-MTP-Q3_Hybrid.gguf`
   = 17,226,172,384 B (~16.04 GiB), tree 17,226,176,379 B, 46 downloads.
   README claims layer-wise BF16/Q8/Q6 retention + Q3 experts, native
   llama.cpp (claims only). **Interesting but not stageable** under the disk
   floor: leaves ~9.4 GiB free, far below 20 GiB.
2. **Myric APEX** @ `7659f23aa9b2ae3a53265befb27100380840727c` — base
   `Qwen/Qwen3.6-35B-A3B`; options APEX-i-mini-v2 14,374,397,472 B (~13.39
   GiB), APEX-i-compact-v2 17,378,059,808 B (~16.19 GiB), APEX-i-quality-v2
   23,526,483,488 B (~21.91 GiB); tree has 11 model/metadata files totaling
   110,711,819,881 B. README claims torch-imatrix + llama.cpp compatibility
   and cites sibling Qwen3.5 evals (claims only). Even the smallest leaves
   ~12 GiB FREE — below the 20 GiB floor. **No stage.**
3. **aquaduck UD-Q4_K_M** @ `1bb7ca3cb1911131f575c6b50860f3219fca46a5` — base
   `qwen/qwen3.6-35b-a3b`; full GGUF 22,663,387,424 B (~21.11 GiB); two layer
   shards (11,080,838,240 / 11,604,978,912 B) are packaging-only, not complete
   stock llama.cpp models; tree 45,349,219,360 B. Card says it repackages
   Unsloth Q4_K_M → duplicate quant/packaging, not a new quality hypothesis,
   and too large. **Rejected.**
4. **timtimtimtimtim MXFP4** @ `fe4518ddf3dc5a10bfa444c924eead0dffeb59fb` —
   based on ggml-org Qwen3.6 GGUF; selected model 19,041,835,008 B (~17.74
   GiB); public tag mxfp4/llama.cpp; **no active M1-compatible/runtime proof**.
   **No stage.**
5. **gatilin pruned-v2** @ `002e350971039934ea984115a39a9d31ea7114fc` — base
   `Qwen/Qwen3.6-35B-A3B`; model 16,269,908,320 B plus bundled macOS
   llama-server dylibs (tree 16,297,475,596 B). Changes/prunes the model and
   bundles host binaries → not a clean quantization comparison. **Rejected.**
6. **AutomatosX AX variants** @ `53dce608c8566b138010b51e7746bd69ce6b754b`
   (OptiQ-4bit-MTP, tree 26,327,318,777 B) and
   `bca1959a7f71e9ea768fa20200b31ca1d97afcd4` (AXQ-4bit-MTP, tree
   22,118,786,497 B) — model/MTP repacks of already-audited AX/OptiQ lines;
   no new native Mei proof; too large. Existing AXQ 4/6-bit and OptiQ facts
   remain in Kiem/artifacts.
7. **d9beuD oQ variants** @ `ba59b89188b99348e8fb8d057a705b527158a7f2`
   (oQ4e 21,635,996,979 B — exact revision already audited) plus new sibling
   bit levels: already-known oQ family, no new engine proof, too large.
8. **Derivative/engine-specific/unsupported entries** (scan only, none
   downloaded): LuffyTheFox/Hermes/Genesis derivatives (base is uncensored
   HauhauCS, not pure Qwen base), symrex uncensored dequantized derivatives,
   RomanOneAndFun distilled derivative, Tileward-Inc (~629 KB of evaluation
   files only, no model weight), AMD Quark UINT4-G32-GGUF (no model blob in
   tree), NInfer/CoreAI/Transformers/AWQ/NVFP4-specific entries (no current
   Mei or stock llama.cpp lane on this Mac).

Newest scan records also include TheDrainFlorist VQ revisions (already audited
in `artifacts/qwen36-vq-public-candidate-audit-20260916.md`), AutomatosX, and
RotorQuant (already audited). **Conclusion: no candidate is safely stageable
now.** The most interesting unqueued hypothesis is a pure-base,
scheme-aware llama.cpp artifact (Ghanns layer-wise Q3 hybrid or Myric APEX);
adding a todo for it is a **parent/Kiem decision** — reported here as
**deferred / no todo** (current tree/Kiem state shows no deduplicated todo
already in place from this report's side).

## Blocked (Decision)

- The disk gate blocks **both admitted acceptance legs** (OptiQ fresh-KV on
  8024; ManniX Qwen3.6-27B-A3B-Coder-MTP-GGUF CD-IQ4_K_M on llama.cpp 8017 —
  each a 25-row gate) and **every newly inspected candidate**. No
  runtime-boundary investigation is justified at this disk state; do not stage,
  download, or probe anything until free disk ≥ 30 GiB with a single-writer
  preflight.
- No ranking/full-coverage claim is made or implied by this report; the raw
  inventory (45 groups / 18 complete zero-harness) is inventory state, not a
  verdict on any candidate.

## Next

- Keep **OptiQ fresh-KV 25-row acceptance** as the next run gate: port 8024,
  exact identity `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, config hash
  `6011477d1711`, exact 25-row shape (2+8+5+3+4+3), safe controls (no
  `--model-profile`, no unsafe compile), distinct acceptance KV path, then
  teardown and zero-harness review of the resulting rows.
- **ManniX** remains a separate admitted gate (llama.cpp 8017, CD-IQ4_K_M,
  25-row shape), same disk precondition.
- Both require **free disk ≥ 30 GiB** and a single-writer preflight. Do not
  close the Qwen3.6 track.
- Optional deferred thread (no todo): pure-base scheme-aware llama.cpp
  hypothesis (Ghanns/Myric) re-check at next scan once disk headroom exists.

## Side-effect statement and checks

- No model run, download, install, cache deletion, results/log.jsonl or
  leaderboard/chart change, config/runner/task/check/fixture change, Kiem
  mutation, sibling-repo (Mei) change, push, or GitHub activity. No tests run —
  this report-only change needs no suite run.
- Checks performed: `git status --porcelain=v1` / `git rev-parse HEAD` /
  branch name (clean, d0c7c15, main); artifact directory listing (name free,
  no collision); prior audit artifact read for style/state continuity;
  `git diff --check` clean before commit.
- Files created: **this artifact only**, committed as one scoped report-only
  commit.
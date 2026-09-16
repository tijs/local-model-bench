# Qwen3.6 track — public MLX-MTP discovery audit, 2026-09-16

CPU-only, report-only continuation of the Qwen3.6 research loop. Read-only
Hugging Face metadata/tree GETs (never weights), read-only local checks, and
one scoped commit. **No code was implemented, no model/server/probe was
launched or stopped, no benchmark ran, no weights were downloaded, no tooling
was installed, no cache was deleted, no results/log.jsonl, LEADERBOARD.md,
selection-manifest, config, runner/task/check/fixture change occurred, and no
Kiem, Mei checkout (`/Users/tijs/projects/mei`), GitHub action, push, publish,
unsafe compiled decode, or CoCore side effect happened.** The only repository
write is this artifact, committed as exactly one path.

Source labels: **Measured** = verified local facts this tick (re-checked by
this audit, read-only); **Public metadata** = Hugging Face API/card records
(tree endpoints at pinned revisions re-read this tick; card claims are
recorded precisely but are NOT benchmark evidence); **Decision** = this
report's judgment.

Report date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench`, branch `main`.

## Measured local state

- Checkout: HEAD `1d1678b52a929a1adfdd3ef54a38db006fc3e6a4` (1d1678b), branch
  `main`, ahead 39 of `origin/main` (rev-list `0 39`), working tree clean
  (`git status --short --branch` → `## main...origin/main [ahead 39]` only).
  Last commit: `artifacts: record Qwen3.6 public-discovery follow-up (2026-09-16)`.
- Processes/listeners: no benchmark/model process; no listener on ports 8012,
  8016, 8017, 8018, 8020, 8024–8027 (`ps` grep, `netstat -an` grep, `lsof -nP
  -iTCP -sTCP:LISTEN`; re-checked before writing and after committing).
- Free disk (`df -k`, 1 KiB blocks): **26,658,804 KiB available =
  27,298,615,296 decimal bytes ≈ 27.3 GB ≈ 25.42 GiB**. Runner launch gate
  `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` (Measured:
  `runner/bench_common.py:78`) FAILS. With the 20 GiB post-download floor
  (21,474,836,480 B), the largest stageable selected file would be
  ~5,823,778,816 B (~5.82 GB / 5.42 GiB); every candidate below is larger.
- Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2` — confirmed read-only in
  `configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml` and prior artifacts;
  **unmutated**. No Kiem todo was added by this scan (parent/Kiem decision:
  defer).

## Current result/eligibility inventory (Measured, read-only re-parse of `results/log.jsonl`)

- **4,064 total rows; 916 Qwen3.6 rows.** `harness_error` is stored as a string
  (`"False"`/`"True"`): 905 `"False"`, **11 `"True"`** among Qwen3.6 rows.
- Grouping by `(config_hash, runner_git_sha)`: **45 Qwen3.6 groups; 18 complete
  groups** = all six suites (`kiem_mini, hearth_mini, kipclip_mini,
  hearth_full, sanity, hermes_ops`) with zero `harness_error` rows. (By
  `config_hash` alone: 24 groups / 16 complete.) Inventory state, not a verdict
  on any candidate; coding-only fragments and canary evidence are **not**
  ranking evidence.
- Latest Qwen3.6 row remains **2026-09-14T09:40:08Z** — no run since.
- OptiQ is **coding-only, not eligible**: only config hash `31a7f0b6a256`, two
  fragments — 15 rows (14/15) at runner `b5b7f49bcb62` (hearth_full,
  hearth_mini, kiem_mini, kipclip_mini) and 5 rows (3/5) at runner
  `f713b29fc5c7` (kiem_mini only). No `sanity`/`hermes_ops` rows.
- OptiQ fresh-KV acceptance hash **`6011477d1711`** (identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, port 8024): **0 result rows, no
  results/configs snapshot**. Config `configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml`
  (Measured, read-only) confirms: exact 25-row shape 2+8+5+3+4+3 over the four
  current-methodology coding suites; safe controls (no `--model-profile`,
  `VMLX_ENABLE_UNSAFE_COMPILE=0`, `--compiled-decode false --load-mmap false`);
  distinct acceptance KV path `mei-runtime/kv-qwen36-optiq-acceptance`.
- Selection manifest `results/qwen36-mei-selection.json` (Measured, read-only):
  engine `mei`, family `Qwen3.6-35B-A3B`, **three fragments, all config hash
  `cea524483faf`**, runners `de1d34279681` / `e5e8e82cdeb9` / `6a6d9f534804` —
  matches the parent's chart dry-run input. The corresponding log group
  (25 rows, 22 pass, 1 `harness_error` row at runner `e5e8e82cdeb9`,
  hearth_mini-feature) is a partial stock selection, not a full-coverage /
  engine-comparative set.
- **No log row references** `t0rr3sp3dr0`, `lmstudio-community`,
  `Qwen3.6-35B-A3B-MTP-4bit`, or `CoderX-MTP`; no config references them
  (configs scan: only an unrelated historical mention of a `lmstudio-community
  8-bit MLX repo` comment in `configs/Devstral-Small-2507/mlx.yaml`). No HF
  cache entry exists for any of them (Measured: `~/.cache/huggingface/hub/`
  contains only the pre-existing OptiQ-4bit, mlx-community 4bit/4bit-DWQ,
  EigenLabs MLX-mixed-4bit, and the already-gated
  `models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF` @ snapshot
  `75a75137…`, 16 GB — note: **that cached repo is `Coder-MTP` (no "X"),
  a different repo than the new `CoderX-MTP` scan target**).

## Public metadata and classifications (Public metadata + Decision)

Sources: `https://huggingface.co/api/models/{repo}/tree/{rev}?recursive=true`
GETs at pinned revisions, re-verified this tick; card READMEs read as public
claims only.

### 1. `t0rr3sp3dr0` Qwen3.6-35B-A3B MLX-MTP ladder (all lastModified 2026-09-16)

Repos `t0rr3sp3dr0/Qwen3.6-35B-A3B-MLX-MTP-<quant>`; verified tree sizes at
pinned revisions:

| quant | pinned revision | files | tree bytes | `mtp/weights.safetensors` |
|---|---|---|---|---|
| 4bit | `be977a28e835d12ead90665cfdf3041bf2cc0b5e` | 19 | 22,130,772,679 | 487,189,455 |
| 5bit | `0815d9399eb326141c777f4d6cccfddb1a37a15b` | 20 | 26,606,062,271 | 591,719,631 |
| 6bit | `7ca2c09ddc1194992ed26553611ea32107bf0ee6` | 21 | 31,081,352,593 | 696,249,801 |
| 8bit | `2336b86c821ffd91b0bf6d1849c4ebd3de8eed9f` | 23 | 40,031,932,404 | 905,310,156 |
| mxfp4 | `d86fa86be9d7daff2b9cabec35d2419ddd9c5b58` | 19 | 21,011,844,932 | 461,055,511 |
| mxfp8 | `e5f4001735c4744f5152fe46e8f19d0c05c9821e` | 22 | 38,913,004,994 | 879,176,220 |
| nvfp4 | `beebc526e6d1ce930db6d5e51bc4baa600693689` | 19 | 22,130,667,911 | 487,188,070 |
| bf16 | `1bdedccec8d07d616403ca88afae460bc99b8fb6` | 28 | 73,616,087,014 | 1,689,283,820 |

(8bit/mxfp8/bf16 sidecar sizes were additionally measured this tick; the bf16
repo's HEAD has since moved to `8cfdedf6c34a879b72c68dee2f9503209c8b6e2b`
(2026-09-16T09:23:33Z, +1,078 B total) — pinned revision above remains valid.)

4bit layout (Measured via tree): four main safetensors
(`model-00001..00004.safetensors`) plus `mtp/weights.safetensors`, index,
config/tokenizer/template/metadata (`mtplx_runtime.json`, README, LICENSE,
.gitattributes, chat_template, preprocessor/video_preprocessor configs).
Card README (Public claim) declares `base_model
mlx-community/Qwen3.6-35B-A3B-MTP-4bit`; **no Mei/vmlx compatibility proof**.

**Classification: interesting but unstageable/unproven MLX-MTP candidate
family.** Disk arithmetic (Measured): downloading the 4bit package
(22,130,772,679 B ≈ 20.61 GiB) would leave 27,298,615,296 − 22,130,772,679 =
**5,167,842,617 B ≈ 5.2 GB (4.81 GiB)** before scratch — far below the 20 GiB
post-download floor; every other variant is larger (mxfp4 leaves ~6.2 GB,
bf16 needs ~68.6 GiB). **Decision: no stage, no probe, no runtime-boundary
investigation at this disk state; no new Kiem todo** — existing acceptance
gates and the disk gate take precedence. Card claims are not benchmark
evidence.

### 2. `lmstudio-community/Qwen3.6-35B-A3B-MLX-4bit` @ `0c4a20a6437ae5985ddc9eb1a3f122ee6c151c3b`

17 files, tree **20,429,178,731 B (~19.03 GiB)**. Card (Public claim): base
`Qwen/Qwen3.6-35B-A3B`, MLX quantization by the LM Studio team using
`mlx_vlm`. **Classification: full uniform MLX 4-bit / repack-like duplicate
candidate — not a new scheme hypothesis.** No tensor identity is claimed
(local equality is unproven). Unstageable: would leave
27,298,615,296 − 20,429,178,731 = 6,869,436,565 B ≈ 6.87 GB, below the 20 GiB
floor. **No stage; no new todo.**

### 3. `mlx-community/Qwen3.6-35B-A3B-MTP-4bit` @ `0295b81421bf4d0fccca9a7c0fcfb1418dda3516`

8 files, tree **494,688,099 B (~472 MiB)**. README (Public claim) explicitly
states it contains **MTP drafter weights and is NOT a standalone
chat/text-generation model** — intended as a draft model alongside a
compatible target. **Classification: accessory/sidecar, not a standalone
benchmark candidate**; nothing to gate in the current acceptance lanes.

### 4. `ManniX-ITA/Qwen3.6-27B-A3B-CoderX-MTP-GGUF` @ `c291d85d9c63a1260c93657792639da0bd6a37c1`

Selected `Qwen3.6-27B-A3B-CoderX-Q4_K_M.gguf` = **16,057,050,592 B (~14.95
GiB)** (tree 44 files, 347,147,071,441 B). Card (Public claim): distinct
code-specialist expert-prune with imatrix and embedded MTP — claims only, not
benchmark evidence. No local cache (see cache note above) and **no current
llama.cpp acceptance config/rows** for this repo. Unstageable: would leave
27,298,615,296 − 16,057,050,592 = 11,241,564,704 B ≈ 11.24 GB, below the 20
GiB floor. **Classification: deferred / no new todo**; it does **not** displace
the existing ManniX Coder `CD-IQ4_K_M` llama.cpp acceptance gate (port 8017).

## Disk arithmetic / decision (Measured + Decision)

- Free disk 27,298,615,296 B (27.3 GB / 25.42 GiB) < 30 GB launch gate.
- Stageable-file ceiling before the 20 GiB post-download floor: ~5.82 GB.
  Candidates: 4bit ladder 20.61 GiB (leaves 5.2 GB), mxfp4 19.57 GiB, lmstudio
  MLX-4bit 19.03 GiB (leaves 6.87 GB), ManniX CoderX Q4_K_M 14.95 GiB (leaves
  11.24 GB), and all other ladder variants larger. **Every serious candidate
  fails the floor.** No staging, no probing, no download.
- **Decision: no runtime-boundary investigation is justified at this disk
  state, and no new Kiem todo is added** — existing acceptance gates and the
  disk gate take precedence. Candidates are recorded for a later, disk-free
  re-evaluation only.

## Chart/tests checks (Measured this tick — parent-run, no repo diff)

- Parent chart dry-run on `results/qwen36-mei-selection.json`: wrote only
  `suite_heatmap.png`, `runtime_breakdown.png`, `failure_taxonomy.png` (to
  /tmp; not present in /tmp at this audit's check — ephemeral); `quality_vs_runtime`
  and `engine_delta` were skipped because the selection is partial. This is a
  dry-run/measurement check, not new benchmark data.
- Focused chart tests: **42 OK**; full runner tests: **332 OK** (parent-run).
  Both left **no repo diff** — working tree clean at dispatch and re-confirmed
  clean after this commit.

## Blocked / next gate (Decision)

- **Next run gate remains the existing-cache OptiQ fresh-KV 25-row
  acceptance** — config hash `6011477d1711`, identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, port 8024, exact 25-row shape
  2+8+5+3+4+3, safe controls (no model-profile / no unsafe compile), distinct
  acceptance KV path — **not any newly scanned candidate**. Blocked until free
  disk ≥ 30 GB and the single-writer preflight passes.
- The **ManniX Coder CD-IQ4_K_M llama.cpp acceptance (port 8017, 25 rows)
  remains a separate gate**; the new CoderX-MTP repo does not displace it.
- No candidate staged/probed; no ranking/full-coverage claim made.

## No-side-effect statement

CPU-only; no code implemented; no server launched/stopped/probed; no benchmark
run; no weights downloaded; no tooling installed; no cache deleted;
`results/log.jsonl`, `results/LEADERBOARD.md`, selection manifests, configs,
runner/tasks/checks/fixtures untouched; Kiem plan
`7f5c67e7-b564-4df3-8209-14f7443b56e2` unmutated; `/Users/tijs/projects/mei`
untouched; no unsafe compiled decode; CoCore not restarted; no publish/push or
GitHub activity. Only repo change: this artifact, committed as exactly one
path. `git diff --check` clean; staged list == [this file]; post-commit
re-check: clean tree, no processes/listeners, disk unchanged.
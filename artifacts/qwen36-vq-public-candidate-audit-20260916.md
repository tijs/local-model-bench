# Qwen3.6 VQ track — public-candidate audit of TheDrainFlorist prebuilt MLX rows, 2026-09-16

Dated, **private CPU-only audit** of four newly discovered prebuilt
TheDrainFlorist `Qwen3.6-35B-A3B-VQ-*` MLX candidates on the Hugging Face Hub.
This is a **public-metadata + local read-only audit only** — it is NOT a native
Mei gate, NOT a benchmark leg, and NOT an acceptance run. No model was run, no
download was made, no install happened, no cache or KV path was touched, no
results/ row, LEADERBOARD, config, Kiem state, sibling repo, or public state
was modified (explicit no-side-effects statement in §6).

Audit date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (the only repo touched). All source data
is labeled below as **Public metadata** (Hugging Face API/card data, recorded
verbatim — imported, not benchmark-measured) or **Measured** (local read-only
checks); **Decision** is this audit's judgment. Card claims are recorded
precisely but are explicitly NOT benchmark facts (no run verifies them here).

## 1. Repository baseline (Measured)

- HEAD `27bddea32291e3cfcc45fc151ee0446a95b5d321` (`artifacts: Qwen3.6 decision
  audit 2026-09-16 — temporal wording corrected …`), clean `main`
  (`git status --porcelain=v1 -b` = `## main...origin/main [ahead 35]`), clean
  before and after this audit's checks.
- No other worker, benchmark run, or model server was active during this tick
  (supplied dispatch context); this audit performed no launch, stop, or probe.

## 2. Candidate set (Public metadata — Hub API/card records, exact immutable revisions)

Four TheDrainFlorist VQ (vector-quantization) prebuilt MLX rows, complete tree
sizes (bytes and GiB, 1 GiB = 2^30 B — conversions re-derived locally and
verified ✓):

| repo id | pinned revision | files | size (bytes) | size (GiB) |
|---|---|---|---:|---:|
| `TheDrainFlorist/Qwen3.6-35B-A3B-VQ-3.4bpw` | `ecb3aa8bb51238e1e8338aa6a6d589e55ea9fc0e` | 16 | 14,827,125,426 | 13.8088366259 |
| `TheDrainFlorist/Qwen3.6-35B-A3B-VQ-3.8bpw` | `c16275c3347e1048c1c98478efa28c783cd0120c` | 16 | 16,846,291,308 | 15.6893313937 |
| `TheDrainFlorist/Qwen3.6-35B-A3B-VQ-4.6bpw` | `ec53a6aead757b8e163253af2e39d7a14746716e` | 18 | 20,110,814,948 | 18.7296559550 |
| `TheDrainFlorist/Qwen3.6-35B-A3B-VQ-5.4bpw` | `34c27d1261fc1140f93ed76b9fa17222cd457f21` | 16 | 23,885,349,114 | 22.2449648324 |

The 3.8bpw revision's Hub file records list **four shard records** (bytes /
SHA-256), recorded verbatim:

1. `7,090,457,932` / `e92b475d3f8d3650645e9f80687a80f4235792323123bf3cc20694f0646cb713`
2. `7,318,039,928` / `e48500e67ccf5c0e084f7a41e31ea020f609f82da47f53ccb9362bc6f00c9684`
3. `1,524,021,243` / `f201ce0a18c0dd6194cdf12879f352962f2338a7d880435caca30f587bbae770`
4. `893,179,585`  / `a2bbd7a8c1b760b1866ce84db8452a23ad12df4904598f5f74c0c14ab6afb603`

(Shard bytes sum to 16,825,698,688; the remainder of the 16,846,291,308 tree is
the non-shard files — config/tokenizer/model.py etc. Shards are records, not a
standalone tree total.)

## 3. 3.8bpw card claims (Public metadata — card record, NOT benchmark facts)

The 3.8bpw row's public card claims, recorded precisely and treated as
**unverified claims** (no run backs them here):

- `library_name`: **mlx**.
- Tags include `qwen3_5_moe`, `vector-quantization`, `qwen3.6`.
- Base model: **`Qwen/Qwen3.6-35B-A3B`**. License: **Apache-2.0**.
- Size: **15.7 GiB** (card figure; note the complete pinned tree per Hub API is
  16,846,291,308 B ≈ 15.69 GiB — close but not identical; the card claim is
  recorded, not adjudicated).
- Runs with **stock `mlx-lm` / no patches** using the **bundled `model.py` VQ
  runtime**.
- Optional MTP/exo path is **sequential** — an extra, separate execution mode,
  and is **not a Mei compatibility claim**.

These claims say nothing about Mei interoperability, the 25-row acceptance
shape, KV semantics under Mei's runtime, or safe-control behavior; none were
tested and none are asserted here.

## 4. Local/disk facts (Measured — read-only checks)

- All four candidate cache roots under
  `~/.cache/huggingface/hub/models--TheDrainFlorist--...` were **absent**
  (read-only glob check: zero matches; the hub directory itself exists).
  Nothing is staged, pinned, or dereferenced for any of the four rows.
- Free disk at audit time: **23,609,184,256 bytes = 21.9877662659 GiB**
  (read-only `df` on the Data volume; re-read at report-writing time on the same
  volume showed 23,053,060 KiB ≈ the same state — normal ±MB drift).
- Consequence (arithmetic, verified): downloading only the **smallest** package
  (3.8bpw, 16,846,291,308 B) would leave
  **6,762,892,948 bytes = 6.2984348722 GiB** free — **below the discovery
  20 GiB post-download floor and far below the runner 30 GB launch gate**
  (`MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0`), before any scratch/overhead space.
- **No download is authorized**, and none was performed.

## 5. Decision

- These VQ candidates are **interesting public metadata** (prebuilt MLX, stock
  mlx-lm runtime, Apache-2.0, exact immutable revisions now recorded) but they
  are **not safely stageable** (disk floor violated by even the smallest row),
  **not proven Mei-compatible** (no run, no native gate), and therefore **not
  worth a runtime-boundary investigation on this tick** — staging alone would
  breach the discovery floor, and no gate could even start.
- **No Kiem todo was added and no existing report was modified.** Current Kiem
  state already carries the deferred ManniX item and the explicit **open OptiQ
  acceptance todo 15**; this audit adds nothing to it.
- The CPU-only audit still **selects one future existing-cache OptiQ acceptance
  leg** as the next run-worthy item — it remains **blocked until free disk
  ≥ 30 GiB AND all exact identity / safe-control / 25-row / teardown gates
  pass**. These VQ rows do not displace that selection.

## 6. Side-effect statement (explicit)

This tick performed **no model run, no download, no install, no cache deletion,
no result-row change, no leaderboard change, no Kiem mutation, and no public
side effect** of any kind. The only write was this artifact, committed as a
single report-only commit (§1 baseline → this file), scoped to
`artifacts/qwen36-vq-public-candidate-audit-20260916.md`.
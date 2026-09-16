# Qwen3.6 track — decision audit tick, 2026-09-16 12:38 CEST

CPU-only decision-audit tick for the Qwen3.6 benchmark research worker (Kiem
plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`; open todos 13 daily discovery
audit / 15 fresh-KV OptiQ acceptance / 17 ManniX CD-IQ4_K_M acceptance).
Read-only with respect to every model/server/result surface: **no model,
server, or probe was launched, stopped, or built; no weights downloaded; no
tooling installed; no cache deleted; results/log.jsonl, LEADERBOARD.md,
selection manifests, configs, runner/tasks/checks/fixtures untouched; Kiem
unmutated; /Users/tijs/projects/mei untouched; CoCore not restarted; no push
or publish.** The only repository write is this artifact, committed as exactly
one path.

Source labels: **Measured** = verified local facts this tick (re-checked
read-only); **Public metadata** = Hugging Face API records (card claims are
public claims, NOT benchmark evidence); **Decision** = this report's judgment.

## Measured local state

- Checkout: HEAD `5f88743e…` (latest commit `artifacts: record Qwen3.6 public
  MLX-MTP discovery audit (2026-09-16)`), branch `main`, ahead 40 of
  `origin/main`; `git status --short --branch --untracked-files=all` shows only
  `## main...origin/main [ahead 40]` — clean at start and re-confirmed clean
  just before this commit. No concurrent or pre-existing change detected;
  nothing reset/stashed/cleaned/overwritten.
- Processes/listeners: no llama-server/mei/omlx/vllm/run_bench process
  (`ps` grep) and no listener on benchmark ports 8012, 8016, 8017, 8018, 8020,
  8024–8027 (`lsof -nP -iTCP -sTCP:LISTEN`). Only Hermes gateway/dashboard,
  tailnet router, browser-harness daemon.
- Free disk (`df -k /`): **26,662,660 KiB = 27,302,563,840 B ≈ 27.30 GB ≈
  25.43 GiB**. Runner launch gate `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0`
  (Measured: `runner/bench_common.py:78`, with the 2026-08-25 truncation-blob
  incident note) **FAILS**. The 20 GiB post-download floor
  (21,474,836,480 B) is above current free space, so the largest stageable
  single file before the floor would be ~5,827,727,360 B (~5.83 GB); every
  complete 27–32B candidate measured so far is ≥ ~14 GB.
- Cron/writer evidence (Measured, read-only): active Hermes cron jobs include
  `Qwen3.6 benchmark research worker` (ba2552668fdf — the job dispatching this
  tick) and `Daily 27–32B MoE model discovery` (5ea0ef15ba8d), both scoped to
  this checkout; plus unrelated Kiri/Kipclip/Marktplaats jobs. No other writer
  process running; no Kiem mutation attempted.

## Result/eligibility inventory (Measured, read-only re-parse of results/log.jsonl)

- **4,064 total rows; 916 Qwen3.6 rows.** `harness_error` is a string:
  905 `"False"`, 11 `"True"` among Qwen3.6 rows.
- Grouping by (model, inference_engine, quant, config_hash, runner_git_sha):
  **45 Qwen3.6 groups; 18 complete groups** = all six suites
  (`kiem_mini, hearth_mini, kipclip_mini, hearth_full, sanity, hermes_ops`)
  with zero `harness_error` rows. Inventory state, not a ranking verdict.
- Latest Qwen3.6 row: **2026-09-14T09:40:08Z** — no run since.
- OptiQ (`mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, mei) remains
  **coding-only: 20 rows under config hash `31a7f0b6a256`** — 15 at runner
  `b5b7f49bcb62` (hearth_full 3, hearth_mini 3, kiem_mini 5, kipclip_mini 4)
  and 5 at runner `f713b29fc5c7` (kiem_mini only); no `sanity`/`hermes_ops`
  rows → not leaderboard-eligible (round-2 rule: all three axes present;
  eligibility outranks evidence, `runner/build_leaderboard.py`).
- Stock selection manifest `results/qwen36-mei-selection.json` (Measured,
  read-only): engine `mei`, family `Qwen3.6-35B-A3B`, three fragments, all
  config hash `cea524483faf`, runners `de1d34279681 / e5e8e82cdeb9 /
  6a6d9f534804` — the chart dry-run input; the log group (25 rows, 22 pass,
  1 `harness_error` at runner `e5e8e82cdeb9`) is a partial stock selection,
  not full coverage. Chart behavior (Measured, `runner/build_summary_charts.py`
  read): headline charts consume only full-eligible groups; partial selections
  are explicitly labeled "(partial)"; engine_delta skipped when a family lacks
  both engines.

## Fresh-KV OptiQ acceptance state (Measured + Decision)

- Config `configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml` (committed at 27ffe2c,
  `last_updated 2026-09-16`): recomputed **config_hash = sha256(file)[:12] =
  6011477d1711** — matches the plan todo 15 target exactly.
- Identity/controls (read-only config check): identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`; port 8024; exact 25-row shape
  2+8+5+3+4+3 over the four current-methodology coding suites; safe controls —
  NO `--model-profile`, `VMLX_ENABLE_UNSAFE_COMPILE=0`,
  `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0`, `BENCH_NO_FUSED_GATE_UP=1`,
  `MLX_SAFETENSORS_MMAP=0`, `--compiled-decode false --load-mmap false`;
  `--memory-limit-bytes 30000000000`; temperature 0.6, prefill 512, context
  65536; pinned snapshot `70a3aa32c7feef511182bf16aa332f37e8d82014`.
- KV path (Measured): acceptance dir
  `mei-runtime/kv-qwen36-optiq-acceptance` is **absent** (server creates it at
  load; pre-run clear today is a no-op); gated evidence dir
  `mei-runtime/kv-qwen36-optiq-safe` present and untouched. Snapshot state
  (Measured): HF cache snapshot
  `~/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit/snapshots/70a3aa32…`
  is **complete — 17 files, dereferenced ≈ 24,115,232 KiB (~24.1 GB incl.
  sidecars; config `model_bytes` 22,155,958,660 for the 15 weight/config
  entries)**, 5/5 safetensors shards + `kv_config.json` + `optiq/` present →
  the acceptance run is an **existing-cache** leg, no download needed.
- Snapshot inventory (Measured): `results/configs/` has 150 entries;
  **no `6011477d1711.yaml`** (config never ran — correct), while
  `31a7f0b6a256.yaml` (the coding-only leg) is present. **0 result rows** carry
  config hash `6011477d1711`.

## ManniX gate state (Measured)

- Staged blob intact: `models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF`
  snapshot `75a75137…` → blob `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22`,
  **16,702,973,408 B** — matches the gate record (admitted to a future
  benchmark gate; probes passed, 5/6 canary with one explicit max-tokens
  truncation, 2253bad artifact). **0 ManniX log rows**; no port-8017 listener;
  the 25-row llama.cpp acceptance (todo 17) remains gated on ≥ 30 GB free disk.

## Public metadata check (Public metadata + Decision)

- One read-only HF API search (`/api/models?search=Qwen3.6`, 40 newest, sorted
  by lastModified) covering everything since the last scan cut
  (2026-09-16T08:07Z): the only new entries are fine-tunes/distills/derivatives
  — Sophea v1/v1.1, albedo/wondercat family, LuffyTheFox/burningfeet Genesis
  uncensored repacks, RomanOneAndFun distilled, symrex dequantized variants,
  power612, pitcany `mtp-q4`, CohenQu cpt — none a pure-base prebuilt quant for
  the Mei/llama.cpp lanes. No new entry changes the decision: every candidate
  lane is disk-bound regardless (stageable-file ceiling ~5.83 GB vs all
  complete candidates ≥ ~14 GB). Per the tick mandate, no deep metadata
  inspection was performed because nothing can materially change the decision
  at this disk state.

## Tests (Measured this tick)

- Focused chart/leaderboard tests (`test_build_summary_charts` +
  `test_plot_leaderboard`): **45 OK** (was 42 at the prior audit; +3 from the
  moved chart logic). Full runner suite (`unittest discover -s runner/tests`):
  **332 OK**. Both run with `PYTHONDONTWRITEBYTECODE=1`; working tree
  re-verified clean afterwards — no repo diff.

## Decision / next gate / blocker (Decision)

- **Next gate remains the existing-cache OptiQ fresh-KV 25-row acceptance** —
  config hash `6011477d1711`, identity `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`,
  port 8024, exact 25 rows (2+8+5+3+4+3), safe controls (no profile / no
  unsafe compile), distinct acceptance KV path, then teardown and zero-harness
  review. The cache is complete, so this leg needs no download.
- **No runtime-boundary investigation is justified** at this disk state; the
  track is **not closed** — coverage inventory (18 complete groups) and the
  two admitted acceptance legs (OptiQ 8024, ManniX 8017) plus the deferred
  scheme-aware llama.cpp hypothesis (Ghanns/Myric) all remain open.
- **Blocker: free disk 27.30 GB / 25.43 GiB < the 30.0 GB runner launch gate**
  (`runner/bench_common.py:78`). Re-run when free disk ≥ 30 GB with a
  single-writer preflight; do not close the track.

## No-side-effect statement

CPU-only; no code implemented; no server launched/stopped/probed; no benchmark
run; no weights downloaded; no tooling installed; no cache deleted;
`results/log.jsonl`, `results/LEADERBOARD.md`, selection manifests, configs,
runner/tasks/checks/fixtures untouched; Kiem plan `7f5c67e7-…` unmutated;
`/Users/tijs/projects/mei` untouched; no unsafe compiled decode; CoCore not
restarted; no push/publish. Only repo change: this artifact, committed as
exactly one path; `git diff --check` clean; post-commit re-check: clean tree,
no processes/listeners on benchmark ports, disk unchanged.
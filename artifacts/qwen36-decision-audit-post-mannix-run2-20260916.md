# Qwen3.6 track — decision audit POST-ManniX run2 interruption, 2026-09-16

CPU-only reconciliation of the Qwen3.6 track after the SECOND interrupted
ManniX leg (18/25, run2). **No model/server/probe was launched or stopped, no
benchmark ran, no download/install/cache deletion happened, no results/ or
leaderboard file was touched, no Kiem mutation, no Mei checkout, no push, no
GitHub activity, no CoCore action.** The only repository write is this
artifact, committed as one scoped report-only commit.

This artifact SUPERSEDES the pre-run2 CPU-only audit
`artifacts/qwen36-decision-audit-20260916.md` (baseline HEAD 27ffe2c1,
pre-ManniX-legs, "next gate stays existing-cache OptiQ 25-row acceptance") and
the tick `artifacts/qwen36-decision-audit-tick-20260916-1238.md` — both
predate the ManniX run legs, the run2 interruption, and the OptiQ payload
retirement, so they are now historical and must NOT be treated as current
state. Nothing in them is deleted; they stay as append-only history.

Source labels: **Measured** = verified live this tick (local read-only checks,
tests, git, disk, processes); **Carried** = previously measured/recorded facts
re-stated from durable artifacts, re-verified read-only where cheap;
**Public metadata** = Hugging Face API/card records (card claims are recorded
precisely but are NOT benchmark facts); **Decision** = this audit's judgment.

Audit date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (only repo touched).

## 1. Checkout state (Measured)

- HEAD `0acad60b843e7bacea58eea7f218a09f35cbce7c` (`configs: ManniX CD-IQ4_K_M
  — reconcile prose to interrupted 18/25 leg run2 (hash 71b86463d35f, runner
  a018d59cefab)`); `main`, **ahead 48** of origin, behind 0; working tree
  clean (`git status --porcelain=v1` empty) before and after all checks.
- Evidence commits re-verified in history: `5426550` (results+artifacts:
  preserved the 18/25 run2 evidence — 18 log.jsonl rows, snapshot
  `results/configs/71b86463d35f.yaml`, 8 transcripts, marker + copied server
  log) and `0acad60` (config-only prose reconciliation). `e0cce63`/`0ef264f`/
  `390a755`/`a018d59` carry the earlier 13/25 leg evidence and its prose
  reconciliations.
- `git fsck` exit 0 (only routine dangling objects; no corruption).

## 2. Result inventory — `results/log.jsonl` (Measured)

Re-parsed in full this tick (read-only; results are append-only and nothing
was edited):

- **4095 total rows** (file 4,559,786 B, mtime 2026-09-16 17:36 +0200);
  **947 Qwen3.6 rows**; **31 ManniX rows**.
- **ManniX group A — leg 1 (13/25):** config hash `02c0f591926b`, runner SHA
  `91c123cb02a0` → **13 rows = 11 pass / 2 fail / 0 harness errors**:
  `sanity` 2, `hermes_ops` 8, `kiem_mini` 3.
- **ManniX group B — leg 2 (18/25, run2):** config hash `71b86463d35f`,
  runner SHA `a018d59cefab` → **18 rows = 14 pass / 4 fail / 0 harness
  errors**: `sanity` 2, `hermes_ops` 8, `kiem_mini` 5, `hearth_mini` 3.
- **Full 25-row shape (runner default battery since 2026-08-25):** sanity 2 +
  hermes_ops 8 + kiem_mini 5 + hearth_mini 3 + kipclip_mini 4 + hearth_full 3
  = 25. **Never produced anywhere:** `kipclip_mini` (4 rows) and
  `hearth_full` (3 rows) — 7 rows missing; the run2 leg ended with the last
  present row `hearth_mini-testwrite` at 2026-09-16T15:36:09Z.
- **Neither leg is complete or rank-eligible.** 13/25 and 18/25 are
  interrupted partial legs and must not be called complete anywhere.

## 3. Live config vs immutable pre-run snapshot (Measured)

- **Live config** `configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml`:
  sha256 measured this tick =
  `f4e4206eab5ca287bb11447fa3231e91b88f2bf6ceb8553508a6c83c597e39b3` →
  prefix **`f4e4206eab5c`**.
- **Immutable pre-run snapshot** `results/configs/71b86463d35f.yaml`: sha256
  = `71b86463d35f693c3469f00858cc30c8aab3eeb35b23b59cdd08ec172389ee45`.
- `cmp` (Measured): the two files **differ at char 505, line 8** — the run2
  snapshot is the pre-run byte content; the live file carries post-run prose
  reconciliation committed in `0acad60` (header comment + `known_gaps`
  additions acknowledging both partial legs).
- **Hash history (Carried + Measured):** pre-run leg1 snapshot
  `02c0f591926b` → pre-run leg2 snapshot `71b86463d35f` → post-reconciliation
  live hash `f4e4206eab5c`. Two runs; the current prose changed the hash
  AFTER both runs. **No benchmark was or will be run against the edited
  prose** — the next run stamps its own fresh pre-run hash and snapshot.

## 4. Archived run2 evidence and failure classification (Carried, artifacts verified this tick)

- Marker: `artifacts/qwen36-mannix-cd-iq4km-interrupted-run2-20260916.md`
  (committed in `5426550`). Server log copy:
  `artifacts/qwen36-mannix-cd-iq4km-interrupted-run2-20260916-server.log`
  (280,999 B, present).
- Server-log tail verified this tick: log ends at 95:26 with
  `operator(): operator(): cleaning up before exit...` immediately after
  `stop: cancel task, id_task = 176256` — cleanup ordered mid-generation.
  **No runner exit code or shutdown cause is recorded in any durable
  artifact; the interruption cause is NOT proven and must not be inferred.**
- Run2 failure classification (all 4 model/task-level, 0 harness errors,
  per marker + rows): `hermes_ops-multi-step-chain` — finish_reason=length
  truncation at the config's `hermes_ops_max_tokens: 16384` cap;
  `kiem_mini-debug` — held-out Swift compile failure (unhandled `try`);
  `kiem_mini-parse-note` — held-out Swift type failure
  (`String.SubSequence`→`String`); `kiem_mini-testwrite` — mutation grade 1
  of 3 mutants survived. Leg1's 2 failures (same truncation pattern +
  `kiem_mini-feature` Rust check failure) are recorded in
  `artifacts/qwen36-mannix-cd-iq4km-interrupted-20260916.md`. All require
  the repo's zero-harness review before any completion claim.

## 5. Leaderboard / chart eligibility (Measured + Decision)

- `results/LEADERBOARD.md` (last generated 2026-09-14 11:40, 226,900 B,
  mtime unchanged): **zero ManniX / CD-IQ4 mentions** — no leaderboard entry
  exists; correct, because no ManniX group is complete.
- Chart eligibility (runner/build_summary_charts.py, lines 336-337): a group
  charts in headline heatmaps only as `complete and zero_harness_errors`;
  both ManniX groups are incomplete (13/25, 18/25) → excluded.
- **Partial rows must not be rebuilt into headline outputs:** regenerating
  LEADERBOARD.md or SUMMARY.md now would rewrite results/ from partial,
  unranked rows — results/ are append-only evidence and the leaderboard stays
  as last generated until a complete eligible group exists. No regeneration
  was performed this tick.
- Chart/plot focused tests re-run this tick (Measured):
  `uv run --locked --no-sync python -m unittest runner.tests.test_build_summary_charts runner.tests.test_plot_leaderboard`
  → **Ran 45 tests in 1.627s — OK**. Full runner suite re-run: see §7.

## 6. Public metadata scan (Public metadata + Decision)

Latest public-discovery artifacts inspected (Carried from this-tick reads):
`qwen36-public-discovery-audit-20260916.md`,
`qwen36-public-discovery-followup-20260916.md` (scan window through
2026-09-16T08:07Z), `qwen36-vq-public-candidate-audit-20260916.md`,
`qwen36-public-discovery-mtp-audit-20260916.md`,
`qwen36-future-source-revision-check-20260915.md`. Findings:

- All newly surfaced Qwen3.6 packages are **derivatives/fine-tunes or
  unstageable** on the current resource picture: RomanOneAndFun distilled
  derivative (0 downloads, non-pure base — rejected); GhannsLt layer-wise
  hybrid GGUF 17.2 GB (~9.4 GiB left after download — below the 20 GiB
  floor); Myric APEX; TheDrainFlorist VQ-3.8; AutomatosX AXQ-4bit; d9beuD
  oQ4e; treeish oQ3e; majentik RotorQuant; amd Quark UINT4 — all previously
  audited, all leave disk below the post-download floor.
- **No prebuilt candidate changes the disk/resource decision.** No new
  candidate was invented, staged, or runtime-boundary tested this tick.

## 7. Disk / memory / cache / process / port state (Measured)

- **Disk free (df -k, this tick):** 50,749,308 KiB = 51,967,291,392 B =
  **48.398312 GiB = 51.967291 decimal GB** — above the runner's
  `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GB gate (runner/bench_common.py:78)
  and far above the 20 GiB staging floor. (Parent-dispatch figure ~50,750,336
  KiB / 48.4065 GiB; ±1 MB drift is normal.)
- **Memory:** `hw.memsize` = 34,359,738,368 B = **32 GiB** (Measured).
- **Processes (Measured):** no `llama-server`, `run_bench`, `bench_common`,
  `mei`, `vmlx` process (ps scan empty).
- **Ports (Measured, lsof):** 8017, 8082, 8080 all **free**; the sole
  `:5000` LISTEN is macOS ControlCenter (unrelated).
- **ManniX staged model (Measured this tick):** blob
  `…/models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF/blobs/6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22`
  = **16,702,973,408 B** (stat), full sha256 re-computed live this tick =
  `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22` —
  byte-identical to the config-pinned value; snapshot symlink
  `snapshots/75a75137d610ed037a09b46c29ca1d37fd000f2e/Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`
  → same blob. Staged; do not re-download.
- **HF hub cache (Measured):** exactly 4 model dirs — EigenLabs
  mixed-4bit, ManniX-ITA GGUF, mlx-community 4bit, mlx-community 4bit-DWQ.
  **`models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit` is ABSENT** — the
  OptiQ payload cache was explicitly retired and must NOT be re-staged unless
  reopened; its historical 20 rows (hash `31a7f0b6a256`, two coding-only
  fragments) and evidence stay. Mei-runtime KV dirs
  `kv-qwen36-optiq-canary` / `kv-qwen36-optiq-safe` remain (historical
  cache evidence; the safe dir is intentionally preserved).

## 8. Kiem open todo state (Carried, read-only this tick via `~/bin/kiem todos`)

Plan `7f5c67e7-b564-4df3-8209-14f7443b56e2` — **two open todos**:

- **Todo 13** — daily discovery: on each daily discovery report, consume at
  most one safely staged, deduplicated candidate todo after single-writer,
  disk, memory, provenance, and teardown gates pass.
- **Todo 17** — ManniX full acceptance (current wording): one full
  current-methodology `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF` acceptance
  leg only after free disk ≥ 30 GiB before launch and > 20 GiB staging floor,
  CD-IQ4_K_M blob+sha verified, a committed reproducible config pinning
  served identity `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M` on
  llama.cpp port 8017, and single-writer preflight passes; one server; ctx
  65536 / parallel 1 / n-gpu-layers 99 / flash-attn on / jinja / reasoning on
  / cache-prompt; no unsafe compiled-decode setting; 25 task rows; append-only
  preservation, zero-harness review, teardown, all benchmark ports/processes
  free before any next model.

No Kiem mutation performed this tick.

## 9. Tests (Measured)

- Focused chart/plot: **45 tests OK** (1.627s, this tick).
- Full runner suite (`python -m unittest discover -s runner/tests`): **332
  tests OK** (this tick; 67-75s run, matches prior audits' 332-OK).

## 10. Decision

- **Do NOT close the Qwen3.6 track.** The 13/25 and 18/25 ManniX legs are
  interrupted partials, not completions; the arm stays `viable: full` /
  unranked in the live config, and the track's ranked-selection work is
  unfinished.
- **Do NOT run OptiQ again.** The OptiQ payload cache is retired; its 20
  rows are coding-only and ineligible, and no re-staging happens unless the
  cache is explicitly reopened by the parent.
- **No mixed46 runtime-boundary investigation in this unit.** (mixed46 rows
  remain historical inventory only; nothing in this audit authorizes probing
  the EigenLabs mixed-4bit arm.) No new candidate is staged (§6).
- **The only next gate is ONE fresh complete current-methodology ManniX
  llama.cpp acceptance run**, launched only once the single-writer preflight
  passes. Preconditions and exact controls:

| Gate element | Exact value (from live config, Kiem todo 17, runner) |
|---|---|
| Served identity | `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M` (runner appends its own `bench-<config-hash>` identity alias; exact-identity gate, H2/H5) |
| Port | 8017 (8020-family sibling ports must also stay free) |
| Config hash | **current live hash `f4e4206eab5c`** (= new pre-run snapshot name `results/configs/f4e4206eab5c.yaml`; prose committed in `0acad60`, no run against edited text so far) |
| Runner SHA | a **fresh clean working-tree HEAD** at run time (not `91c123cb02a0`, not `a018d59cefab` as "complete" — all rows carry the runner SHA of the run's clean commit) |
| Row budget | **25 rows = 2 + 8 + 5 + 3 + 4 + 3** (sanity 2, hermes_ops 8, kiem_mini 5, hearth_mini 3, kipclip_mini 4, hearth_full 3); a speed-gated 10-row run is partial and requires the coding-only rerun path |
| Pinned artifact | revision `75a75137d610ed037a09b46c29ca1d37fd000f2e`, file `Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`, 16,702,973,408 B, sha256 `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22` |
| Launch controls (live config) | `runner/.dspark-head/build/bin/llama-server` (ggml-org mainline build a302733, AppleClang 21.0.0 arm64) `--model <snapshot path> --host 127.0.0.1 --port 8017 --ctx-size 65536 --parallel 1 --n-gpu-layers 99 --flash-attn on --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --jinja --reasoning on --cache-prompt --timeout 1800` |
| Compiled decode | **NO unsafe compiled decode**: plain mainline llama.cpp decode; no VMLX unsafe-compile env/flag exists on this arm (independent of any Mei concept) |
| Resource budget | free disk ≥ 30 GB before launch (measured 48.4 GiB now) and > 20 GiB floor through the run; exactly one server; 32 GiB memory (present); existing staged model blob (no re-download, no `--hf-repo`) |
| Evidence | append-only 25 rows, pre-run config snapshot, raw transcripts, runner SHA, server log, failure classifications with zero-harness review of BOTH legs' 6 model-level failures |
| Teardown | `unload_all.sh` discipline; verify no llama/mei listener on benchmark ports; no successor model until all benchmark ports/processes are free |

- The prior 13/25 and 18/25 legs remain partial evidence: **never call them
  complete**, never merge their rows into a completion claim, never rebuild
  leaderboards/charts from them (§5).

## 11. Side-effect statement and checks performed this tick

- No results/ change (no log.jsonl row added or edited, no
  LEADERBOARD.md/SUMMARY.md regeneration), no config/selection/runner/task/
  check change, no Kiem mutation, no push, no GitHub activity, no CoCore
  action, no sibling repo touched, no download/install/cache deletion.
- Read-only checks: AGENTS.md; `git status`/`git fsck`; full `results/log.jsonl`
  re-parse (4095 / 947 / 31 with per-group splits); live-config + snapshot
  sha256 + `cmp`; run2 marker + server-log tail; leaderboard/chart eligibility
  code; both test suites (§9); `df -k`, `sysctl hw.memsize`; `ps`/`lsof`
  (8017/8082/8080/5000); staged blob `stat` + full sha256 (55 s); HF hub cache
  listing; OptiQ cache absence check; `~/bin/kiem todos`.
- Files created: **this artifact only**
  (`artifacts/qwen36-decision-audit-post-mannix-run2-20260916.md`), committed
  as one report-only commit. `git diff --check` clean before commit; no other
  path staged.
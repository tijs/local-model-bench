# Qwen3.6 track — decision audit POST-ManniX-complete, 2026-09-16

CPU-only reconciliation of the Qwen3.6 track after the **completed** ManniX
llama.cpp acceptance leg (25-row full battery). **No model/server/probe was
launched or stopped, no benchmark ran, no weights were downloaded (only tiny
public metadata files), no tooling installed, no cache deleted, no
results/log.jsonl, LEADERBOARD.md or SUMMARY.md edit, no config/runner/task/
check/fixture change, no Kiem mutation, no Mei checkout
(`/Users/tijs/projects/mei`) touch, no push, no GitHub activity, no CoCore
action, no credentials exposed.** The only repository write is this artifact,
committed as one scoped report-only commit.

This artifact **SUPERSEDES** the pre-completion audits
`artifacts/qwen36-decision-audit-20260916.md`,
`artifacts/qwen36-decision-audit-tick-20260916-1238.md`, and
`artifacts/qwen36-decision-audit-post-mannix-run2-20260916.md` as the current
decision state. They remain as append-only history; nothing is deleted.

Source labels: **Measured** = verified live this tick (local read-only checks,
tests, git, disk, processes, full log.jsonl re-parse); **Carried** =
previously recorded facts re-verified read-only where cheap; **Public
metadata** = Hugging Face API/card records at pinned revisions (card claims
are recorded precisely but are NOT benchmark facts); **Decision** = this
audit's judgment.

Audit date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (only repo touched).

## 1. Checkout state (Measured)

- HEAD `8e4eacbbee4a90dda5c53f57d4849c4f982a0e16` (`results: record complete
  ManniX Qwen3.6 acceptance leg`, 2026-09-16 21:37 +0200); `main`, **ahead 50**
  of origin, behind 0; working tree clean (`git status --porcelain=v1` empty)
  before and after every check, including after both test suites.
- Parent commits of interest: `711e537c4dc4` (pre-run decision audit, full SHA
  `711e537c4dc43c8f6444387431d4a08defc585d0` = the **runner_git_sha** stamped
  on all 25 completion-leg rows — the run executed on that clean commit);
  `8e4eacb` committed the leg's results on top.
- `git fsck` not re-run (routine history unchanged since `8e4eacb`; no
  corruption suspicion).

## 2. Result inventory — `results/log.jsonl` (Measured, independently re-parsed this tick)

4,120 total rows (file 4,591,611 B, mtime 2026-09-16 21:30 +0200). 56
ManniX/Qwen3.6-27B rows in exactly 3 groups by (model, engine, quant,
config_hash, runner_git_sha) — all engine `llama.cpp`, quant family
`GGUF Q4_K_M (ManniX-ITA community CD-IQ4_K_M k-quant, single-file, 16.7 GB)`,
config path `configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml`,
served identity `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M`:

| group | config_hash | runner_git_sha | rows | pass | within_budget | harness_err |
|---|---|---:|---:|---:|---:|---:|
| leg 1 (interrupted) | 02c0f591926b | 91c123cb02a0 | 13 | 11 | 11 | 0 |
| leg 2 (interrupted) | 71b86463d35f | a018d59cefab | 18 | 14 | 15 | 0 |
| **leg 3 (complete)** | **f4e4206eab5c** | **711e537c4dc4** | **25** | **21** | **22** | **0** |

**Complete leg (f4e4206eab5c / 711e537c4dc4) — independently recomputed this
tick: 25 rows = 21 pass / 4 fail / 0 harness errors / 22 within_budget.**
Per-suite (recomputed from rows, matches the leaderboard by-suite table):
`sanity 2/2`, `hermes_ops 7/8`, `kiem_mini 3/5`, `hearth_mini 3/3`,
`kipclip_mini 4/4`, `hearth_full 2/3` — exactly the 2+8+5+3+4+3 = 25 battery
shape (runner constants `FULL_HERMES_OPS_TASKS = 8`, `FULL_CODING_TASKS = 15`
at `runner/build_leaderboard.py:39-40`; full battery = sanity + full hermes_ops
+ 15 coding rows).

Leg-3 failures (all model/task-level, run_error/grade records, 0 harness
errors):
- `hermes_ops-multi-step-chain` — `finish_reason=length` truncation at the
  config's `hermes_ops_max_tokens: 16384` cap (same pattern as both prior legs;
  a cap artifact, not quality grading);
- `kiem_mini-parse-note` — held-out Swift type failure;
- `kiem_mini-testwrite` — mutation-test grade (partial mutant survival);
- `hearth_full-feature` — held-out check failure.

Legs 1 and 2 remain interrupted partials (13/25, 18/25): **never call them
complete, never merge them into a completion claim.** Their rows carry the
legacy `02c0f591926b`/`71b86463d35f` hashes and their own runner SHAs.

## 3. Live config vs immutable pre-run snapshot (Measured)

- Live `configs/Qwen3.6-27B-A3B-Coder-MTP-GGUF/gguf-cd-iq4km.yaml` sha256 =
  `f4e4206eab5ca287bb11447fa3231e91b88f2bf6ceb8553508a6c83c597e39b3`.
- Pre-run snapshot `results/configs/f4e4206eab5c.yaml` sha256 = identical;
  `cmp` **byte-identical** — unlike the run2-era live-vs-snapshot drift
  (71b86463d35f vs live f4e4206eab5c, prose-only), the completion leg's live
  config and snapshot agree exactly. No post-run prose edit changed the hash.
- Snapshots present for all three legs (`02c0f591926b.yaml`,
  `71b86463d35f.yaml`, `f4e4206eab5c.yaml` in `results/configs/`).

## 4. Raw evidence presence for the complete leg (Measured)

- 15 transcripts committed with the leg (`results/transcripts/`): kiem_mini 5,
  hearth_mini 3, kipclip_mini 4, hearth_full 3 — all present (find count 15
  newer than 19:00, 26 ManniX transcript files total incl. prior legs).
- 10 prompt-result JSONs (`results/prompt_results/...`) for the 8 hermes_ops +
  2 sanity rows — all present, **0 missing** (checked this tick).
- **Gap (Measured): no server log or run-marker artifact for the complete leg
  exists in `artifacts/`** (latest is run2's
  `qwen36-mannix-cd-iq4km-interrupted-run2-20260916-server.log`, 18:46). The
  completion commit (8e4eacb) carried rows/snapshot/transcripts/chart only.
  Evidence for the leg is therefore rows+transcripts+snapshot+leaderboard, not
  a preserved server log. The next gate MUST archive the server log (see §9.
  evidence requirement) — a re-run of the same leg would be worse than fixing
  this in the next leg.

## 5. Leaderboard / chart eligibility and focused/full test behavior (Measured + Decision)

- `results/LEADERBOARD.md` and `results/score_chart.png` regenerated at
  2026-09-16 21:30 in `8e4eacb` — the complete leg IS present and ranked:
  **#3 "Best overall"** (usefulness gate PASS (88%, 8) = 7/8 hermes_ops;
  coding 80% (15); score 0.829), inventory row `tasks 23` (25 − 2 sanity),
  `pass rate 83 %` (19/23 non-sanity), `slow passes 2` (hearth_mini-feature +
  kiem_mini-feature: pass=True with within_budget=False), `avg tok/s 40.6`,
  `avg TTFT 7.95 s`, `avg coding turns 6.5`, `tool errors 9`, `peak RSS 21.4
  GB`, total runtime 4826 s. All values reconcile with the row-level re-parse
  (§2) — no drift.
- Eligibility rule (Measured, `runner/build_summary_charts.py:320-337`
  `_row_group_eligible`): complete (sanity present + full 8 hermes_ops + full
  15 coding tasks) AND zero harness errors. The f4e4206eab5c group passes →
  charts/leaderboard inclusion correct. Legs 1/2 fail completeness → correctly
  shown as inventory rows only, each flagged `*config since changed*` on the
  old-hash rows (their hashes predate the final prose).
- Focused test behavior (Measured this tick):
  `uv run --locked --no-sync python -m unittest runner.tests.test_build_summary_charts runner.tests.test_plot_leaderboard`
  → **Ran 45 tests in 1.560s — OK** (chart builders write only to temp dirs;
  tree stayed clean).
- Full runner suite (Measured this tick):
  `uv run --locked python -m unittest discover -s runner/tests` → **Ran 332
  tests in 68.259s — OK**; tree clean after (results/ mtimes unchanged at
  21:30).
- No regeneration performed by this audit (results/ are append-only evidence;
  LEADERBOARD/SUMMARY stay as last generated from the complete leg).

## 6. Public metadata audit — AutomatosX AXQ MTP repos at pinned revisions (Public metadata, read-only)

GET-only HF API tree + small metadata files (README, axquant_runtime.json,
axquant_omlx_compat.json, config.json, generation_config.json) fetched this
tick at the immutable revisions; **no weight blob was fetched** (largest
metadata file 139,529 B):

**AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP @
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24`** — 22 files, tree
**23,120,765,421 B** (matches the 07:00-discovery figure; safetensors
23,099,321,635 B: 4 shards + `mtp.safetensors` 1,689,283,776 B +
`vision.safetensors` 893,179,624 B + index). Card claims: base
`Qwen/Qwen3.6-35B-A3B` @ `995ad96eacd98c81ed38be0c5b274b04031597b0`, apache-2.0,
`library_name: mlx`, AXQuant 1.2.0 v2, measured BPW 5.1401 (4-bit 93.52% /
8-bit 1.47% / bf16 5.01%; group sizes 32/64), config `model_type
qwen3_5_moe` / `Qwen3_5MoeForConditionalGeneration` (same arch family as the
Mei-served mlx-community 4bit and EigenLabs mixed-4bit arms). **Compatibility:
MLX-LM level B (standard text inference only); AX Engine native execution NOT
established (no validated native manifest); MTP Tier-2 speed NOT certified
(agent ~0.95× / 0.80×); vision NOT certified (mlx-vlm smoke failed on
df-macstudio-m2 — sidecar/layout mismatch).** Tier-1 cert is on host
`df-macbookpro-m5` for a different hub commit (`a549387d…`), not this pinned
revision; no Mei/vmlx claim or probe exists.

**AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP @
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`** — 23 files, tree
**26,985,603,183 B** (5 shards; same mtp/vision sidecars). Card claims:
measured BPW 6.0001 (layout 4-bit 68.69% / 6-bit 24.35% / 8-bit 1.95% / bf16
5.01% — the "6bit" name is a storage-budget class, not uniform 6-bit), same
base/arch/quantizer; same compatibility status (MLX-LM level B, no native
manifest, MTP Tier 2 uncertified — agent ~1.09× / 0.88×, vision uncertified);
Tier-1 cert on the same external host at hub commit `7b9ff47a…`. First time
this 6-bit revision is audited (no earlier artifact covers it).

Classification (Decision): both are **prebuilt MLX-LM-level-B text candidates
with self-declared "convertible" support tier — plausible Mei-serving
candidates in principle (qwen3_5_moe affine layout), but with zero local
presence, no Mei/vmlx compatibility proof, uncertified MTP/vision, and card
claims only (never benchmark facts).** They are the authorized next queue
items — see §8-§9.

## 7. Disk / memory / processes / ports / cache (Measured)

- Free disk this tick: `shutil.disk_usage` = **51,883,159,552 B = 48.32 GiB =
  51.88 decimal GB** (`df -k` 50,667,148 KiB avail; ~0.09 GB drift vs run2
  audit — normal).
- Launch gate (Measured, `runner/run_bench.py:545-546`):
  `free_gb = shutil.disk_usage(REPO).free / (1024**3)` must be ≥
  `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` **GiB** at launch.
- **AXQ staging arithmetic (Measured, Decision):** staging the 4-bit package
  leaves 51,883,159,552 − 23,120,765,421 = **28,762,394,131 B = 26.79 GiB < 30
  GiB gate → launch refused**; staging the 6-bit leaves 24,897,556,369 B =
  **23.19 GiB < 30 GiB → refused**. Required pre-staging free disk for the
  4-bit leg ≈ 30 GiB + 21.53 GiB ≈ **51.5 GiB (55.3 decimal GB)**; current
  48.32 GiB is short by ≈ 3.2 GiB. **Neither AXQ leg can launch on the current
  disk even fully staged.** The 20 GiB post-staging floor (as used by discovery
  audits) is met for both; the 30 GiB prelaunch gate is NOT.
- Memory: `hw.memsize` = 34,359,738,368 B = **32 GiB** (unchanged; AXQ 4-bit
  ~21-23 GiB resident + KV is tight-but-plausible — preflight item, not a
  blocker).
- Processes (Measured): no `llama-server`, `run_bench`, `mei`, `vmlx`,
  `omlx` process. One **orphaned HF-metadata fetcher** (PID 37099, started
  22:52 by a prior session, writing ≤5 MB metadata files to
  `/tmp/hermes-qwen-discovery-20260916/`) — unrelated to the benchmark, left
  untouched (it writes /tmp only; no repo effect; task forbids stopping
  probes/models, and this is neither).
- Ports (Measured, lsof): no listener on 8017 / 8082 / 8080 / 8024-family.
  LISTENs are macOS `ControlCenter` (5000, 7000), `rapportd` (49152) and
  Hermes local-tool ports (8765, 8766, 9119) — none benchmark-owned.
- HF hub cache (Measured): exactly 4 model dirs (EigenLabs mixed-4bit,
  ManniX-ITA GGUF, mlx-community 4bit, mlx-community 4bit-DWQ). **No
  AutomatosX/AXQ cache or staging exists anywhere** → there is no existing
  cache to run an acceptance leg from. OptiQ cache stays retired/absent.

## 8. Kiem state (Carried, read-only this tick)

- Plan `2c419bd1` item 5 (**Queued**): Gravity-30B-A5B-Base @
  `ee52d6f6ff6572ed72851dbaac5a79ef982a74a4` — consume **only after the
  serialized AX-Qwen3.6 4-bit then 6-bit legs are terminal and committed**, and
  only with a compatible pinned quant/repack or a resource-gate change; ≥30 GiB
  prelaunch / ≥20 GiB post-staging, memory, exact identity, plain+streaming
  generation, native tools, 25-row current-methodology coverage, provenance,
  teardown; never concurrent with another model. **(Unchanged; matches the
  authorized serialized queue.)**
- Plan `7f5c67e7`: todo 13 (daily discovery consume — one staged candidate per
  report) and todo 18 (DwarfStar/ds4 research — read-only profile/microbench
  only, blocked pending the ManniX teardown/single-writer gate) remain open.
  **Todo 17 (ManniX full acceptance) is no longer open** — consumed by the
  completed leg; the ManniX result note `1c1db849` (2026-09-16T19:38:39Z)
  records it.
- No Kiem mutation performed this tick. No AXQ leg todo exists in Kiem (the
  AXQ queue is parent-authorized per this delegation; Gravity's todo references
  it).

## 9. Decision (Decision)

- **Do NOT close the Qwen3.6 track.** ManniX acceptance is complete and ranked
  (#3), but the authorized serialized queue (AXQ 4-bit → AXQ 6-bit → gated
  Gravity @ ee52d6f6) is unfinished. Track stays `viable: full` / open.
- **An existing-cache acceptance run is NOT justified.** The only complete
  current-methodology cache is the just-finished ManniX GGUF (already run);
  modulo that, no AXQ cache or staging exists, the mlx-community 4bit arm is
  already benchmarked, EigenLabs mixed-4bit is retired paper-only inventory
  (no probe), and OptiQ is retired. Nothing cached maps to the next queue
  item.
- **No runtime-boundary investigation is justified this tick.** (a) Both AXQ
  packages are absent locally and their staging would still fail the 30 GiB
  launch gate on current disk (26.79 / 23.19 GiB post-staging); (b)
  Mei/vmlx compatibility of the AXQ packs is unproven (level-B mlx-lm claim
  only, no native manifest, MTP/vision uncertified — any investigation would
  be speculative with no resource headroom); (c) the authorized queue defines
  AXQ as staged benchmark legs, not probes; (d) mixed46 stays historical
  inventory only.
- **Do NOT authorize Whittle/Nemotron arms, calibrated conversion, OptiQ
  re-staging, or any new candidate staging.** No download, install, cache
  deletion, or conversion occurred or is authorized by this audit.
- The two interrupted ManniX legs remain partial evidence (§2); never rebuild
  headline outputs from them.

### Explicit next gate — AXQ 4-bit Mei acceptance leg (UNLAUNCHED; nothing run this tick)

The only authorized next run when its preconditions hold, in order: **AXQ
4-bit leg → AXQ 6-bit leg → gated Gravity slot @
`ee52d6f6ff6572ed72851dbaac5a79ef982a74a4`**.

| Gate element | Exact value |
|---|---|
| Served identity | `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` at immutable revision `d880b11584ae6ee1e18a1e86f082a8397cf2ce24` (exact-identity gate; Mei serves the staged dir's ID; runner appends `bench-<config-hash>` alias as in other mei configs) |
| Expected rows | **25 = sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3 + kipclip_mini 4 + hearth_full 3** (current-methodology battery; a speed-gated 10-row run is partial and requires the coding-only rerun path) |
| Resource budget | Pre-staging free disk ≥ **51.5 GiB (≈55.3 decimal GB)** so that ≥ 30 GiB free remains at launch (gate measured in GiB at `run_bench.py:545`); currently 48.32 GiB — **NOT met, do not start staging yet**; 32 GiB memory; one server at a time; no concurrent model; the ManniX GGUF blob (16.7 GB) may remain but total disk must be re-measured at run time |
| Safe settings | Mei baseline controls per existing mei configs: **no unsafe compiled decode** (`VMLX_ENABLE_UNSAFE_COMPILE=0`, no `--model-profile`), plain + streaming generation probes, native tools, ctx 65536 / parallel 1 / temp & sampling fields matching current methodology, port **8024** (8020-family siblings free), distinct KV path (no reuse of retired OptiQ KV dirs). **MTP is NOT to be claimed** — stock Mei/MLX stack ignores sidecars; run the plain backbone |
| Single-writer preflight | `git status` clean; committed config with pre-run snapshot + fresh config_hash; no llama/mei listener on bench ports; no other model server; disk + memory gates pass; Kiem single-writer todo consumed; latest daily discovery note consumed (todo 13); no concurrent writer |
| Raw evidence | Pre-run config snapshot `results/configs/<hash>.yaml`; append-only 25 rows; transcripts + prompt_results; **server log MUST be archived this time** (explicit requirement — the completed ManniX leg lacks a server-log artifact, §4); runner_git_sha; failure classifications with zero-harness review |
| Teardown | `unload_all.sh` discipline; verify no llama/mei listener on benchmark ports; no successor model until all benchmark ports/processes free. After the 6-bit leg is terminal AND committed (serialized), the only following slot is the gated Gravity-30B-A5B-Base @ `ee52d6f6ff6572ed72851dbaac5a79ef982a74a4` (56.96 GB public bf16 base → needs a compatible pinned quant/repack or resource-gate change before any staging) |

ManniX leg-3 facts stay as measured (§2-§5); the AXQ 4-bit leg above is the
single explicit next gate and it **remains unlaunched**.

## 10. Side-effect statement and checks performed this tick (Measured)

- No results/ change (log.jsonl 4,120 rows before/after; LEADERBOARD.md,
  SUMMARY.md, score_chart.png untouched, mtimes 21:30), no config/selection/
  runner/task/check change, no Kiem mutation, no push/GitHub activity, no
  CoCore action, no `/Users/tijs/projects/mei` touch, no cache deletion, no
  weight download (only the small AXQ metadata files above, saved under
  `/tmp/axq-audit/`), no credentials.
- Read-only checks: AGENTS.md; `git status` (clean, several times);
  full `results/log.jsonl` re-parse with per-group/per-suite pass/fail and
  harness recompute (§2); live-config + snapshot sha256 + `cmp` (§3);
  transcript/prompt-result presence scan (§4); eligibility source
  (`build_summary_charts.py:320-337`) and battery constants
  (`build_leaderboard.py:39-40`); LEADERBOARD row-by-row reconciliation;
  focused 45-test and full 332-test suites (§5); `df -k` + `shutil.disk_usage`
  + `sysctl hw.memsize` + staging arithmetic (§7); `ps`/`lsof` (§7); HF hub
  cache listing (§7); `~/bin/kiem todos` + `~/bin/kiem notes` (§8); HF API
  tree + metadata GETs for both AXQ repos at the pinned revisions (§6).
- Files created: **this artifact only**
  (`artifacts/qwen36-decision-audit-post-mannix-complete-20260916.md`),
  committed as one report-only commit with `git diff --check` clean; no other
  path staged. Follows the prior conversion-blocker and unload discipline;
  no interleaved commit noise.
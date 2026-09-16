# Qwen3.6 track — public-discovery/decision audit, 2026-09-16

CPU-only, report-only audit of the Qwen3.6 discovery surface and the current
run-gate state. **No code was implemented, no model/server/probe was launched or
stopped, no benchmark ran, no cache was touched, no download/install happened,
no Mei checkout, Kiem, GitHub action, push, or CoCore action occurred.** The
only repository write is this artifact, committed as one scoped report-only
commit. Source labels are kept distinct: **Measured** = verified live this tick
(local read-only checks, tests, git, disk); **Public metadata** = Hugging Face
API/card records (imported and/or re-verified read-only this tick — card claims
are recorded precisely but are NOT benchmark facts); **Decision** = this
audit's judgment.

Audit date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (only repo touched).

## 1. Checkout state (Measured)

- HEAD `2253bad0160f23ced4bc95c351bedfcc4321a4c2` — `artifacts: record ManniX
  Qwen3.6 llama.cpp gate`. `git status --porcelain=v1 -b` =
  `## main...origin/main [ahead 37]`; working tree clean before and after all
  audit checks. `git fsck` clean (no output).
- No active benchmark processes: `ps` shows no `run_bench`/`llama-server`/
  `mei`/`mlx`/`vllm` process (only macOS system daemons and two unrelated
  Hermes marktplaats tool servers). No listener on benchmark ports
  **8024 / 8080 / 11434** (`lsof -nP -iTCP -sTCP:LISTEN`; unrelated local
  listeners 49152/5000/7000/8765/8766/9119 remain — not benchmark state).

## 2. Result inventory — `results/log.jsonl` (Measured)

Re-parsed this tick (contents unchanged; results are append-only and no run
happened since the 0915 audit):

- **4064 total rows; 916 Qwen3.6 rows; exactly eight Qwen3.6 model strings**
  (418 stock MLX, 316 text-only MLX, 96 uncensored GGUF, 25 mixed46, 21
  community GGUF, 20 OptiQ, 15 DWQ, 5 official GGUF; sum = 916).
- **45 Qwen3.6 groups** keyed by (model, config_hash, runner_git_sha).

**Current-methodology eligibility (Measured + Decision):** a group is
*complete* when it covers all six current suites (sanity, hermes_ops,
kiem_mini, hearth_mini, kipclip_mini, hearth_full) and has **zero
`harness_error: true` rows** → **18 complete zero-harness groups**: 15 with
the exact 25-row 2/8/5/3/4/3 shape plus three multi-run fragments that cover
all six suites (27-row `277258e7326f`@`258148c2d48a`, 54-row
`632e9c29f2c5`@`0a7c7af571f4`, 75-row `a23687499989`@`0a7c7af571f4`).
- **OptiQ is NOT eligible**: its 20 rows are two **coding-only** fragments
  under config hash `31a7f0b6a256` — 15 rows at runner `b5b7f49bcb62`
  (kiem_mini 4/5, hearth_mini 3/3, kipclip_mini 4/4, hearth_full 3/3, sole
  failure `kiem_mini-testwrite`, `harness_error: false`) plus 5 rows at runner
  `f713b29fc5c7` (kiem_mini 3/5). No `sanity`/`hermes_ops` rows →
  no 25-row current-methodology eligibility; absent from headline tables.

## 3. Selection manifest and chart dry-run (Measured)

- `results/qwen36-mei-selection.json` is the **three-fragment STOCK** selection
  (family `Qwen3.6-35B-A3B`, engine mei, model_contains
  `mlx-community/Qwen3.6-35B-A3B-4bit`, config_hash `cea524483faf`, runners
  `de1d34279681` / `e5e8e82cdeb9` / `6a6d9f534804`) — **not OptiQ**; reconciled
  partial (`synthetic_eligible=false`, 1 `harness_error: true`).
- Chart dry-run re-verified this tick with
  `uv run --locked --no-sync python runner/build_summary_charts.py --selection results/qwen36-mei-selection.json --output-dir /tmp/qw-chart-test-20260916`:
  writes **only** `suite_heatmap.png` (1 group × 6 suites),
  `runtime_breakdown.png`, `failure_taxonomy.png` (3 failure rows / 3
  categories); **`quality_vs_runtime` skipped** ("no group had both a pass rate
  and recoverable runtime") and **`engine_delta` skipped** ("no family had both
  a pass-rate and runtime delta") because the selected stock fragments are
  partial. Output went to system temp; no repo file touched.

## 4. Passing test commands (Measured, this tick)

- `uv run --locked --no-sync python -m unittest discover -s runner/tests -p 'test_build_summary_charts.py'`
  → **Ran 42 tests in 1.558s — OK** (exit 0).
- `uv run --locked --no-sync python -m unittest discover -s runner/tests`
  → **Ran 332 tests in 67.768s — OK** (exit 0).
- (Earlier audits recorded the identical suites passing via plain
  `uv run --locked`; this tick used `--no-sync` to guarantee no environment
  mutation.)

## 5. OptiQ acceptance config and ManniX gate (Measured)

- `configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml` (committed at HEAD, tracked):
  SHA-256 `6011477d17118ee15e29860b208244dcd95411db0fbe328cf60a084d103f4245` →
  config hash **`6011477d1711`**. Identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, port 8024, context 65536,
  prefill_step_size 512, fresh KV path
  `mei-runtime/kv-qwen36-optiq-acceptance`, safe controls (no
  `--model-profile`, no unsafe-compile). **No acceptance rows and no
  `results/configs/6011477d1711.yaml` snapshot exist** (results/ untouched; a
  snapshot would be created by the first run). The expected future shape is
  25 rows = sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3 +
  kipclip_mini 4 + hearth_full 3.
- **ManniX gate commit `2253bad`** (current HEAD). Candidate revision
  `75a75137d610ed037a09b46c29ca1d37fd000f2e`
  (`ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF`, file
  `Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`); staged blob size
  **16,702,973,408 B** and SHA-256
  `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22` — both
  **re-verified read-only this tick** (`stat -f %z` on the HF-cache blob;
  `shasum -a 256` of the 16.7 GB blob, 51 s). **Distinguishing the evidence:**
  the gate's identity/plain/streaming/native-tool probes passed and the
  **exploratory 5/6 canary** (one trial, `passed=5, failed=0, errors=1`) is
  canary evidence only — the sole error is `kiem_mini-testwrite` truncated at
  `max_tokens=4096` (`finish_reason=length`), a token-cap artifact, NOT a
  benchmark result: **no `results/log.jsonl` row was appended and nothing is
  ranked**. ManniX's separate 25-row llama.cpp acceptance remains **admitted
  but blocked** by the disk gate (§6).

## 6. Disk gate (Measured + Decision)

- Recorded audit free disk: **27,317,862,400 bytes = 25.441741943359375 GiB =
  27.3178624 decimal GB** (parent-verified at dispatch). Live re-read at
  `2026-09-16T07:02:11Z`: 27,319,660,544 B = 25.443416595458984 GiB —
  identical state, normal ±2 MB drift.
- Runner launch gate `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GB
  (`runner/bench_common.py:78`) → **no run is authorized now**. Discovery
  post-download floor: **20 GiB**.
- Every direct/prebuilt candidate package leaves the disk far below the 20 GiB
  floor after a fresh download (arithmetic checked, baseline 27,317,862,400 B):

| package | tree bytes | left after download | left (GiB) |
|---|---|---:|---:|
| TheDrainFlorist VQ-3.8 | 16,846,291,308 | 10,471,571,092 | 9.752411 |
| treeish oQ3e | 17,228,073,315 | 10,089,789,085 | 9.396848 |
| majentik RotorQuant Q4_K_M | 21,166,769,272 | 6,151,093,128 | 5.728652 |
| d9beuD oQ4e | 21,635,996,979 | 5,681,865,421 | 5.291650 |
| AutomatosX AXQ-4bit | 23,120,765,421 | 4,197,096,979 | 3.908851 |

→ **No new candidate should be staged or runtime-boundary tested this tick,
and no new Kiem todo is warranted.** Existing decisions preserved: **do not
close the Qwen3.6 track**; the next run gate is the existing-cache OptiQ
fresh-KV 25-row acceptance on port **8024**, only once **free disk ≥ 30 GiB**
AND all exact identity/controls/snapshot shape/teardown checks pass; ManniX's
separate 25-row llama.cpp acceptance remains admitted but blocked by the same
disk gate.

## 7. Read-only Hugging Face public metadata scan (Public metadata + Decision)

Scan window `2026-09-16T07:01:00Z` – `2026-09-16T07:01:55Z` (UTC). Read-only
API queries (GET only; no weight or repo-file downloads beyond tiny READMEs):

- `https://huggingface.co/api/models?search=Qwen3.6-35B-A3B&limit=100&full=false&sort=downloads&direction=-1`
  (100 results, downloads-sorted top-100).
- Targeted discovery: `search=d9beuD`, `search=RotorQuant`,
  `search=RomanOneAndFun`, `search=oQ3e`, `search=Quark Qwen3.6`,
  `author=AutomatosX`; per-revision tree sums via
  `…/api/models/{repo}/tree/{revision}?recursive=true`; card claims read from
  the pinned-revision READMEs.

Direct/prebuilt candidates (immutable revisions, complete tree sizes):

- **TheDrainFlorist VQ-3.8**
  (`TheDrainFlorist/Qwen3.6-35B-A3B-VQ-3.8bpw` @
  `c16275c3347e1048c1c98478efa28c783cd0120c`): tree **16,846,291,308 B**
  (16 files). **Already audited** (`qwen36-vq-public-candidate-audit-20260916.md`),
  no local cache entry.
- **AutomatosX AXQ-4bit**
  (`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` @
  `d880b11584ae6ee1e18a1e86f082a8397cf2ce24`): tree **23,120,765,421 B**
  (22 files). **Already queued/deferred** (0915 audit: level-B MLX-LM claims,
  no validated native manifest, no Mei/vmlx claim).
- **d9beuD oQ4e** (`d9beuD/Qwen3.6-35B-A3B-oQ4e-mtp` @
  `ba59b89188b99348e8fb8d057a705b527158a7f2`): tree **21,635,996,979 B**
  (17 files). Card: base `Qwen/Qwen3.6-35B-A3B`, `library_name: mlx`,
  quantized with oQ (oMLX v0.5.3) mixed precision — **4-bit, group 64, MLX
  safetensors** ("4-bit oQ MLX"). Downloaded 61.
- **treeish oQ3e** (`treeish/Qwen3.6-35B-A3B-oQ3e-MTP-MLX` @
  `85dd79d1f9169cf5c7c7c63e4fb2658680e1ed8c`): tree **17,228,073,315 B**
  (18 files). Card: oQ3e **imatrix**-enhanced mixed precision, **MTP** head
  embedded, 4 weight shards (17,204,858,031 B tensor data); card states the
  distribution "**does not identify the exact base-model commit used for
  conversion**" (byte-pinned, not a byte-reproducible recipe) and "Treeish
  uses this model from 32 GB of unified memory and **recommends 48 GB**".
  Downloaded 28 → deprioritized.
- **majentik RotorQuant GGUF Q4_K_M**
  (`majentik/Qwen3.6-35B-A3B-RotorQuant-GGUF-Q4_K_M` @
  `9b088115c319626606799e2d50da5515acb17db0`): tree **21,166,769,272 B**
  (3 files: GGUF + metadata). Card: base `Qwen/Qwen3.6-35B-A3B`; the standard
  Q4_K_M **GGUF works with upstream llama.cpp**, but the **RotorQuant KV path
  "via a dedicated llama.cpp fork"** (the card now recommends upstream native
  `-ctk/-ctv` KV quantization instead; the fork flow is labeled
  experimental/legacy, PR closed without merging June 2026). Public scan
  metadata also flags **PAIT-GGUF-100** — recorded as an **unadjudicated
  public scanner status, NOT a local security verdict** (no local verdict is
  made or implied).
- **RomanOneAndFun Q6** (`RomanOneAndFun/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-MTP-APEX_I-Quality_Q6`):
  a **distilled derivative** (base_model `lordx64/…-Reasoning-Distilled`, not a
  pure `Qwen/Qwen3.6-35B-A3B` base quant) with **zero downloads** →
  **rejected** for this track (pure-base-comparability requirement).
- **amd Quark UINT4** (`amd/Qwen3.6-35B-A3B-Quark-UINT4-G32-GGUF`): API tree
  has **no model blob — README + scripts only** (5 files, 18,857 B) →
  **deprioritized/rejected** for this track. (For completeness, the sibling
  `amd/Qwen3.6-35B-A3B-Quark-UINT4-G128` main tree does carry a
  22,328,075,224 B `model.safetensors`, 66 files / 22,804,866,125 B; either
  way the package is not stageable under §6.)

None of these displace the standing selection; all remain below the disk
floor (§6), so none is staged or runtime-boundary tested this tick.

## 8. Side-effect statement and reconciliation

- No results/ change (no `log.jsonl` row, no `LEADERBOARD.md`/`SUMMARY.md`
  edit), no config/selection/runner/task/check change, **no Kiem mutation**
  (no todo added — none warranted per §6), no push, no GitHub activity, no
  CoCore action, no sibling repo touched, no public side effect.
- The next run gate remains the existing-cache OptiQ fresh-KV 25-row
  acceptance on port 8024 once disk ≥ 30 GiB and all exact
  controls/identity/teardown checks pass (§6); ManniX's 25-row llama.cpp
  acceptance stays admitted-but-blocked by the same gate.

## 9. Checks performed this tick

- Read-only: AGENTS.md; `git status`/`git fsck`; `ps`/`lsof` (8024/8080/11434
  free); `results/log.jsonl` re-parse (4064 / 916 / 8 / 45 groups / 18
  eligible); `results/qwen36-mei-selection.json`; acceptance.yaml
  `shasum -a 256`; ManniX staged blob `stat` + full `shasum -a 256`;
  `df -k`/statvfs; chart dry-run to /tmp; both test suites; read-only HF API
  scans and pinned-revision READMEs.
- Files created: **this artifact only**
  (`artifacts/qwen36-public-discovery-audit-20260916.md`), committed as one
  report-only commit. `git diff --check` clean before commit; HEAD unchanged
  by the audit itself (the artifact commit is the only change).
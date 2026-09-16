# Qwen3.6 track — decision audit, 2026-09-16

Continuation (NOT a replacement) of `artifacts/qwen36-decision-audit-20260915.md`;
that artifact stays authoritative for everything it measured. This tick is ONE
durable, CPU-only follow-up: no model run, no download, no install, no cache
deletion, no results/ or selection-manifest change, no Kiem change during the
audit worker's report-writing phase (the parent performed a separate, verified
post-audit Kiem reconciliation — see §12), no sibling repo touched, no push.
Everything marked **Measured** was verified live in this tick; **Public
metadata** is Hub-API/card or prior-tick recorded data; **Decision** is this
audit's judgment.

Audit date: 2026-09-16 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (only repo touched).

## 1. Checkout state (Measured)

- HEAD `27ffe2c142a39753075849bdd30bac1ba339a37a`
  (`configs/Qwen3.6-35B-A3B-OptiQ: add fresh-KV acceptance leg config (planning/setup only)`),
  clean `main`, **ahead 32** of origin (`git status --porcelain=v1 -b` = `## main...origin/main [ahead 32]`,
  clean before and after all work this tick). The 0915 audit closed at ahead 28;
  the four new commits are the audit fixes `bb293db`/`d6f8c5d`/`f3e76b5` and the
  acceptance config `27ffe2c`. `git fsck` clean.
- No benchmark process and **no listener on port 8024** at audit time
  (read-only `lsof`/`pgrep`; re-checked after all checks ran).

## 2. Result inventory (carried, unchanged)

`results/log.jsonl` was NOT read or modified this tick (task scope). Its mtime
is `2026-09-14 11:40:08`, size 4,523,012 B; `LEADERBOARD.md`
`2026-09-14 11:40:14` (226,900 B); `SUMMARY.md` `2026-09-13` (59,419 B). Results
are append-only and no run has happened since, so the 0915 **measured**
inventory is unchanged: **4064 total rows, 916 Qwen3.6 rows**, exactly **eight
distinct Qwen3.6 model strings** (418 stock MLX, 316 text-only MLX, 96
uncensored GGUF, 25 mixed46, 21 community GGUF, 20 OptiQ, 15 DWQ, 5 official
GGUF — 418+316+96+25+21+20+15+5 = 916 ✓).

**OptiQ eligibility read (Decision, facts from 0915 §2/§4):** OptiQ remains two
**coding-only** fragments under config hash `31a7f0b6a256`: 15 rows at runner
`b5b7f49bcb62` = **14/15** (sole failure `kiem_mini-testwrite`,
`harness_error: false`, classified model behavior) plus 5 rows at runner
`f713b29fc5c7` = **3/5**. No `sanity`/`hermes_ops` rows → **no 25-row
current-methodology eligibility**; OptiQ is absent from “Best overall” and
appears only in the all-groups unranked/partial table. Unchanged this tick.

## 3. Fresh-KV acceptance config (Measured)

`configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml` — committed at HEAD
(`git ls-files` ✓); SHA-256
`6011477d17118ee15e29860b208244dcd95411db0fbe328cf60a084d103f4245` → config hash
**`6011477d1711`** (measured `shasum`). Canonical `mei.yaml` is untouched.

- Exact identity: `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit` (model ==
  served_model_id); port **8024** (shared-port rule, never concurrent); context
  cap **65536**; `prefill_step_size` **512** (the gate's actual value, not the
  0.4.2-era 1024); temperature 0.6 / top-p 0.95 / top-k 20,
  `reasoning_mode: thinking`, cache-reuse true, max-tokens unset (0.5.0 auto
  profile → 4096).
- Pinned revision `70a3aa32c7feef511182bf16aa332f37e8d82014`; Mei source
  `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` (**v0.5.0**, tag-level commit);
  vmlx/swift pin `44461ffdf8dca836b624b2d0d268c800dedea05e` (read from the
  gate's scratch build checkout).
- Safe controls (non-negotiable, read from config): env
  `VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0
  BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0`; flags
  `--compiled-decode false --load-mmap false --memory-limit-bytes 30000000000
  --prefill-step-size 512 --context-cap 65536`; **no `--model-profile`** (the
  first wrapper run named the profile + unsafe-compile=1 and OOM'd — recorded
  history, do not re-add).
- **Distinct KV path**: `~/.local/share/local-model-bench/mei-runtime/kv-qwen36-optiq-acceptance`
  (Measured: does not exist yet — `ls` ENOENT; created only by the server at
  load, so a pre-run clear is a no-op today). This is the ONLY path the runner's
  `clear_kv_cache_dir` may ever delete; the gated evidence dir
  `kv-qwen36-optiq-safe` (Measured: 10,372,820 KiB ≈ 9.9 GiB) must stay.
- Expected future shape: **25 rows = sanity 2 + hermes_ops 8 + kiem_mini 5 +
  hearth_mini 3 + kipclip_mini 4 + hearth_full 3** (2+8+5+3+4+3 = 25; runner
  default suite set since 2026-08-25). **No acceptance rows and no
  results/configs/<hash> snapshot for `6011477d1711` exist yet** (results/
  untouched; a snapshot would be created by the first run).

## 4. Disk gate (Measured)

- Free disk at audit time: **23,676,715,008 B = 22.051 GiB** (`df -k /` re-read;
  pre-dispatch figure 23,681,609,728 B / 22.055 GiB — both ≈ 22.05 GiB, the
  ±5 MB drift is normal). Below the runner's launch gate
  `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GB (`runner/bench_common.py:78`) →
  **no run is authorized now**; `run_bench.py` refuses before any model load.

## 5. Snapshot accounting — 17 files, NOT 22.1 GB (Measured local + Public metadata)

The pinned snapshot now resolves to **17 dereferenced files** locally; the
optional `optiq/` sidecars are present (symlinks dated 2026-09-14) and their
blobs resolve:

| scope | bytes |
|---|---:|
| 14 top-level blobs (5 shards + config/tokenizer/metadata/template), excl `.gitattributes` | **22,155,958,532** |
| `optiq/mtp.safetensors` | 1,644,816,498 |
| `optiq/optiq_vision.safetensors` | 893,179,469 |
| **full tree incl `.gitattributes` (1,570)** | **24,693,956,069** |

All Measured locally this tick via `stat -L` (dereferenced). The Hub public tree
(Public metadata) also reports 17 files / 24,693,956,069 B — exact match with
the local dereferenced measurement (22,155,958,532 + 1,570 + 1,644,816,498 +
893,179,469 = 24,693,956,069 ✓).

**Accounting call-out (explicit):** config `model_bytes: 22155958660` (Measured
derivation) = the prior **15 top-level entries including the `optiq/` directory
inode (128 B) and excluding `.gitattributes`** — i.e. 22,155,958,532 + 128, NOT
the full tree. The 0915 audit's 22,155,960,230 B figure =
22,155,958,532 + 1,570 + 128 (same top-level scope). The full pinned tree on
disk today is **24,693,956,069 B (≈ 23.0 GiB), not 22.1 GB** — anything that
quotes 22.1 GB is describing only the root blobs, not the complete artifact.

## 6. Existing gate evidence (carried from 0915, unchanged)

- **OptiQ native gate**: plain/stream/native tool identity passed (exact
  `/v1/models` served ID on every response; native `get_weather` non-stream AND
  stream); cache probe growing cached_tokens **0 → 1076 → 1092 → 1108** (disk KV
  tier, SAFE dir); memory ≈ **23.09–23.18 GB** active under the **30 GB** limit.
- **mixed46**: exact **65536 prefill crashed with Metal OOM** (prefill
  `completed=44032 total=65536`, `Trace/BPT trap: 5`, MLX Insufficient Memory);
  **remains unranked**; its launcher still pins unsafe-compile=1 (reconcile
  before any future run). **Decision: no mixed46 runtime-boundary experiment in
  this CPU-only unit.**
- **Official ggml-org GGUF** current fragment: 5 rows, **3 failures incl 2
  harness errors** (runner `19aee89cd756`, 2026-09-13) — the official control
  has visible failures; the canary 12/12 does not rank or contradict it.
- **AXQ**: previously audited (Public metadata, 0915 §6 — level-B MLX-LM claims,
  no validated native manifest, MTP unverified/development-only, no Mei/vmlx
  compatibility claim); **not cached locally** and **not a Mei candidate**; no
  download authorized (disk gate alone refuses).
- **ManniX** (Public metadata, carried): public revision `75a75137…` exposes
  CD-IQ4_K_M at **16,702,973,408 B**; its public sha256 sidecar is
  `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22`. **Not
  cached** and remains deferred by the disk floor (no local measurement of the
  payload was possible or attempted).

## 7. Chart behavior from the existing selection (Measured/carried)

- `results/qwen36-mei-selection.json` is the **three-fragment STOCK** selection
  (family Qwen3.6-35B-A3B → `mlx-community/Qwen3.6-35B-A3B-4bit`,
  config_hash `cea524483faf`, runners `de1d34279681`/`e5e8e82cdeb9`/`6a6d9f534804`),
  **not OptiQ**; reconciled `partial` (`synthetic_eligible=false`, 1
  `harness_error: true`) → no headline pass-rate/runtime, no engine delta.
- `runner/build_summary_charts.py` is output-only: writes **only temp PNGs** via
  `_save()`; never edits LEADERBOARD/SUMMARY/log rows. Headline charts require
  full-eligible groups; this selection yields only the three partial charts.

## 8. Verification performed this tick (Measured)

- Focused chart unittest:
  `uv run --locked python -m unittest discover -s runner/tests -p 'test_build_summary_charts.py'`
  → **Ran 42 tests in 1.563s — OK** (exit 0).
- Full runner unittest:
  `uv run --locked python -m unittest discover -s runner/tests` → **Ran 332
  tests in 68.811s — OK** (exit 0). Test temp outputs went to system temp only.
- Acceptance wrapper `server_command` dry-run via bash (stub model/kv dirs;
  `--dry-run` returns before any build or launch):
  `runner/start_mei_server.sh … --dry-run` → **exit 0**, launch line contains
  `--compiled-decode false`, `--load-mmap false`, `--memory-limit-bytes
  30000000000`, `--prefill-step-size 512`, exact served identity
  `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`, `--port 8024`; with the
  acceptance values the line also carries the exact model-dir (pinned snapshot)
  and **fresh KV path** `…/mei-runtime/kv-qwen36-optiq-acceptance`. The line
  does **not** include `--model-profile` or any `unsafe-compile`/`unsafe-compile=1`
  token; env-level `VMLX_ENABLE_UNSAFE_COMPILE=0` lives in the config's launch
  command. A **bare** wrapper dry-run (no optional controls) omits
  `--compiled-decode`, `--load-mmap false`, `--memory-limit-bytes` (forwards
  only base identity/port/context/KV/sampling) — backward-compatible forwarding
  confirmed. Dry-run created no kv/build runtime dirs.
- Post-checks: port 8024 free, no stray mei/bench process, `git status` clean.

## 9. Decision (this audit)

- **One existing-cache OptiQ acceptance leg remains justified** as the only
  relevant pending admission gate for the Qwen3.6 track: only lane with a
  passing live safe gate, a gated 14/15 coding fragment at the correct config
  hash, 12/12 canary determinism, and a locally complete pinned snapshot. It is
  **BLOCKED** until **free disk ≥ 30 GiB** AND all preflight gates pass; today's
  ~22.05 GiB fails the runner gate before any launch.
- **No mixed46 runtime-boundary experiment** in this CPU-only unit (65536-prefill
  Metal OOM unresolved; launcher unsafe-compile divergent).
- **Do not close Qwen3.6 yet** — OptiQ admission is pending.
- **No model run or external side effect happened in this tick** (no server,
  no probe beyond the wrapper `--dry-run`'s own read-only preflight, no
  download, no cache delete, no results/ or selection change, no push).

## 10. Next-gate checklist (explicit, binding when authorized)

- [ ] **Identity**: `/v1/models` returns exactly `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`
      on port **8024**; one Mei server only (shared-port rule).
- [ ] **Config**: acceptance hash `6011477d1711` (committed file/byte SHA as §3);
      pinned revision `70a3aa32…`; Mei source `1518e701…` (v0.5.0) / vmlx
      `44461ffd…`; prebuilt gate binary `mei-build-qwen36-optiq-050` or a
      re-verified rebuild from that exact source state.
- [ ] **Shape**: exactly **25 rows** = sanity 2 + hermes_ops 8 + kiem_mini 5 +
      hearth_mini 3 + kipclip_mini 4 + hearth_full 3; **clean runner SHA** (no
      `+dirty`; config committed before launch).
- [ ] **Resource limit**: free disk **≥ 30 GiB** before launch (runner gate),
      `--memory-limit-bytes 30000000000` on the 32-GiB host; abort on Metal OOM
      (`Trace/BPT trap` / Insufficient Memory).
- [ ] **Controls**: NO download beyond the pinned snapshot (no new payloads);
      env `VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0
      BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0`; flags
      `--compiled-decode false --load-mmap false --prefill-step-size 512
      --context-cap 65536`; **no `--model-profile`**, no `unsafe-compile=1`.
- [ ] **KV path**: fresh acceptance path `…/mei-runtime/kv-qwen36-optiq-acceptance`
      — **never** the safe evidence path `kv-qwen36-optiq-safe` (runner clears
      the config's KV dir pre-run; the safe dir must survive).
- [ ] **Raw evidence**: committed config snapshot `results/configs/6011477d1711.yaml`,
      live server stdout transcript, probe/identity capture, then the appended
      `results/log.jsonl` rows (append-only, unedited).
- [ ] **Teardown/review**: `stop_mei_server.sh` + `unload_all.sh` (never CoCore;
      restore script manual), port 8024 free and no orphan process; review row
      count == 25, zero harness errors, recorded config hash + runner SHA,
      per-suite failures (known `kiem_mini-testwrite` risk) before any
      leaderboard/chart regeneration.

## 11. Checks performed this tick

- `git status --porcelain=v1 -b` clean at start and end: HEAD
  `27ffe2c142a39753075849bdd30bac1ba339a37a`, `main`, ahead 32; `git fsck` clean.
- Read-only: AGENTS.md; 0915 audit; `configs/Qwen3.6-35B-A3B-OptiQ/acceptance.yaml`
  (+ `shasum -a 256`); `runner/start_mei_server.sh`; snapshot `stat -L` sums and
  optiq sidecar sizes; `df -k`; `lsof`/`pgrep`; results-file mtime/size
  (metadata only — `results/log.jsonl` content not read).
- Commands: focused chart unittest (42 OK), full runner unittest (332 OK),
  two bash wrapper `--dry-run` reproductions (full acceptance set and bare).
- Files created: **this repository artifact only** by the audit worker
  (`artifacts/qwen36-decision-audit-20260916.md`). Nothing in `runner/`,
  `configs/`, `tasks/`, `checks/`, `fixtures/`, `results/`,
  `results/qwen36-mei-selection.json`, or any sibling repo was modified. Kiem
  was reconciled separately by the parent after verification (§12).

## 12. Post-audit Kiem reconciliation

After the audit worker verified this artifact, the parent separately reconciled
Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2` (verified independent of this
audit):

- Re-read the plan after verifying the artifact.
- Clarified the checked item as **setup-only / deferred** (plan line 99 now
  reads setup complete/deferred).
- Added the explicit **open fresh-KV OptiQ acceptance gate** as a new open
  acceptance todo (public todo index **15**).
- Read back the final plan/todos: open acceptance todo index **15**, final plan
  version `f4c00e0f2af813fd8ce1831212e410401bf546c6da4e63f8c994026a7578031b`.

No Kiem change was made by the audit worker; the reconciliation above is the
parent's post-audit action only.
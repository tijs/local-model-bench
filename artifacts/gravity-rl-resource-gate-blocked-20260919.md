# Gravity RL (batiai/Gravity-30BA5B-RL-GGUF Q4_K_M) CPU-only resource-gate audit — 2026-09-19

**Timestamp (measurement / write):** 2026-09-19T13:33Z (UTC; local CEST). All measurements were
taken read-only on 2026-09-19 around 13:33Z from the live host; no staging, launch, probe, config
edit, Kiem write, or publish was performed by this unit.

**Verdict (bounded CPU-only reconciliation):** the queued Gravity RL candidate **must not be
staged and must not be launched this tick**. Live free disk is above the 30 GiB pre-launch floor
today, but staging the pinned 19,613,407,328 B (18.266 GiB) artifact would leave only **20.269 GiB
free — about 9.73 GiB below the required post-staging 30 GiB launch reserve** (it would clear the
20 GiB post-staging floor by only ≈ 276 MiB). The post-staging `>= 30 GiB` launch gate is
therefore **not met, and staging must not start**. No model file is staged, no benchmark rows or
provider exist, and there is no active benchmark process, server, or listener. The existing Kiem
queued item stays **open**; the candidate remains **QUEUED / UNRANKED / NOT STAGED**.

Evidence classes are kept separate below: measured local facts, committed-config facts, pinned
remote provenance (labeled, NOT a local on-disk hash), and the queue-state identifiers supplied by
the parent preflight (labeled, not independently re-derived from a Kiem store this tick).

---

## 1. Audit scope and boundary

- Target repo: `/Users/tijs/projects/local-model-bench`, branch `main`, **clean** at
  `b1ad34388a7ec02ccb6598d2e0603eeae14d2582` (verified `git status --porcelain=v1` empty at
  13:33Z, before and after this audit). No other worktree changes were made.
- Unit did **only** read-only inspection (df, sysctl, lsof, ps, grep, find, git) plus this
  artifact. It did **not**: stage/download the model, start/stop any server, run a benchmark or
  probe, edit any config, touch `results/log.jsonl` or `results/LEADERBOARD.md`, modify Kiem
  state, touch `/Users/tijs/projects/mei` (left with its dirty untracked `Casks/kiem.rb` and
  `tap/` as found), or publish/push anything.
- No process, port, or file write was initiated by this unit.

## 2. Candidate identity (pinned provenance; config-committed)

- Model: `batiai/Gravity-30BA5B-RL-GGUF` : `Q4_K_M`
- Revision: `ae61d230482a5a6efa869bc6b72fb784bb630cdb` (immutable HF revision, config line 47)
- Exact file: `Gravity-30BA5B-RL-Q4_K_M.gguf`
- Expected size: **19,613,407,328 bytes** (= 18.266409009695053 GiB)
- Expected SHA-256: `cc134bbc858cbc9186172cf582234d606c15352e9c016e0f3e1cccfe17ccd4e5`
- **Provenance label:** revision, size, and SHA-256 are the **HF LFS blob-store oid at the pin**,
  as committed in the config (`settings.artifact_identity`, config lines 126–128) and verified via
  the HF API 2026-09-17 per that comment. They are **NOT a local on-disk hash** — the model is
  not staged, so no local sha256 exists to compare. Re-verify on-disk `blob == snapshots/<rev>
  symlink target == LFS oid` at any future staging time (repo provenance rule).

## 3. Committed config (measured local state of the repo file)

- Config path: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Exact current SHA-256 (measured on disk this tick): `85851d6b44c5f15db336f345ec5b9aa324889d9aa2402bf4c06ef03c8d55d639`
  (prefix `85851d6b44c5f15d`)
- Tracked in git (committed; last touching commit `f1d450db2f63ea9898c58659270fe7a10dbbf9e5`);
  `git status` clean confirms no uncommitted edits.
- Config itself states: `hermes_provider: null` (line 99), NOT STAGED / placeholder launch-block
  path (lines 64–79), `model_bytes: 19613407328` (line 50), source revision pinned (line 47),
  launch port `8017`, `--n-gpu-layers 99`, `--ctx-size 65536`.

## 4. Measured local facts (live, 2026-09-19T13:33Z)

### 4.1 Disk (exact, `df -Pk /Users/tijs` final read at write time)

- Filesystem `/dev/disk3s5` on `/System/Volumes/Data` (mount backing `/Users/tijs`).
- **Available (free): 40,407,456 KiB = 41,377,234,944 bytes = 38.535552978515625 GiB** (≈ 38.5 GiB).
  *Note: two earlier reads within the minute showed 40,403,468 and (initial parent preflight)
  40,400,908 KiB — a few MiB of ordinary OS churn; the final read above is the recorded value.*
- Pre-launch floor margin: current free − 30 GiB = **9,164,980,224 B ≈ 8.5356 GiB above the
  committed 30 GiB pre-launch floor** → pre-stage free space **is** above 30 GiB.

### 4.2 RAM (exact, `sysctl hw.memsize`)

- **34,359,738,368 bytes = 32 GiB** (32.0 GiB physical RAM). Swap in use as of read:
  `vm.swapusage total 2048.00M used 919.56M free 1128.44M (encrypted)` — recorded for context;
  this CPU-only disk gate does not launch anything.

### 4.3 Runner binary (exact, `./runner/.dspark-head/build/bin/llama-server --version`)

- `version: 0.1.2-dev (build 1, commit a302733)`, `built with AppleClang 21.0.0.21000101 for
  Darwin arm64` — matches the config's `binary_build_provenance` (config line 148). Not executed
  beyond `--version`; no server was started.

### 4.4 Local artifact absence (measured)

- No `models--batiai--Gravity-30BA5B-RL-GGUF` snapshot dir under
  `~/.cache/huggingface/hub/` (no entry, `ls | grep -i gravity` empty).
- A bounded home scan for `Gravity-30BA5B-RL-Q4_K_M.gguf` (and any `*gravity*` name under
  `~/.local/share/local-model-bench`, the HF cache, and the repo) found **no model file** — the
  only hit is the config directory itself.
- No `~/.local/share/local-model-bench/models/` directory exists (the model-store path is absent).
- The config's expected snapshot path
  `~/.cache/huggingface/hub/models--batiai--Gravity-30BA5B-RL-GGUF/snapshots/ae61d230482a5a6efa869bc6b72fb784bb630cdb/Gravity-30BA5B-RL-Q4_K_M.gguf`
  does not exist → **local artifact ABSENT**.

### 4.5 Results and provider state (measured)

- `results/log.jsonl`: **0 rows** matching `gravity` (grep count 0).
- `results/LEADERBOARD.md`: **0 matching lines** (grep count 0).
- **No Gravity bench provider:** `~/.hermes/profiles/bench/config.yaml` contains **no** `gravity`
  entry (grep exit 1; file present, config.yaml exists 2026-09-18); the committed config itself
  declares `hermes_provider: null` (config line 99). No gravity/provider reference exists in
  `runner/` or `scripts/` (only unrelated UI-bundle substrings and Android layout `gravity`
  attributes in the gitignored `.dspark-head` build tree).

### 4.6 No active benchmark / server / listener (measured)

- Process scan (`ps aux` filtered for `llama-server|run_bench|probe|mlx|mei|dspark|benchmark`):
  **no match** — no benchmark, probe, llama-server, MLX/Mei, or dspark process running.
- Benchmark port **8017 is FREE** (no listener, `lsof -nP -iTCP:8017 -sTCP:LISTEN` empty).
- All current TCP listeners were enumerated and ruled out as non-benchmark:
  `rapportd` :49383, `ControlCe` :5000/:7000 (system), hermes dashboard python3 :9119,
  tailnet dashboard router python :8766 (both hermes infra), and an unowned external
  `deno` service :8765 (cwd `/Users/tijs/projects/side-business`, running ~3h; not a benchmark
  server, left untouched). No unload/teardown action was taken against anything.

## 5. Byte arithmetic — the resource gate (exact)

Policy floors (this tick):
- **30 GiB pre-launch floor** — committed runner constant `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0`
  (`runner/bench_common.py:78`), enforced at `runner/run_bench.py:546-548`.
- **20 GiB post-staging floor** — queue/preflight policy floor carried by the parent preflight
  (not a committed runner constant; labeled accordingly).
- Required **post-staging `>= 30 GiB` launch reserve** — the gate this audit checks.

Arithmetic (all GiB = 1,073,741,824 B; model size = config-pinned `model_bytes`):

```
free_now            = 40,407,456 KiB × 1024 = 41,377,234,944 B = 38.535552978515625 GiB
free_now − 30 GiB   =  9,164,980,224 B ≈ 8.5356 GiB   → pre-stage free IS above 30 GiB ✓
model               = 19,613,407,328 B                = 18.266409009695053 GiB
free_after_staging  = 41,377,234,944 − 19,613,407,328 = 21,763,827,616 B = 20.269143968820572 GiB
after − 20 GiB      =    288,991,136 B = 275.6034240722656 MiB (≈ 288.99 MB)
                    → clears the 20 GiB post-staging floor by ≈ 276 MiB (about 0.27 GiB) ✓
after − 30 GiB      =  −10,448,427,104 B = −9.730856031179428 GiB
                    → sits ≈ 9.73 GiB BELOW the 30 GiB launch reserve ✗
```

**Conclusion of the gate:** after staging would leave only **≈ 20.269 GiB free** — comfortably
above the 20 GiB post-staging floor (≈ 276 MiB / ≈ 0.27 GiB margin) but **≈ 9.73 GiB below the
30 GiB post-staging launch reserve**. The required `post-staging >= 30 GiB` launch gate is
**NOT met**, so **staging must not start** this tick (staging would consume ~18.27 GiB and strand
the machine below the launch reserve with no run possible).

## 6. Decision (this tick)

1. **CPU-only reconciliation / block:** no staging, no launch, no probe, no config change, no
   benchmark/leaderboard edit. This audit is read-only evidence only.
2. **Keep the existing Kiem queued item OPEN** (durable plan
   `7f5c67e7-b564-4df3-8209-14f7443b56e2`, serialized queue slot after Bonsai 2 PTQ1_0; daily
   discovery note `2c419bd1-0104-4e32-8045-76463c3b645a`). These identifiers are carried from the
   parent queue state (a bounded read-only search of the side-business/Kiem scratch tree found no
   matching JSON/MD/TS/JSONL artifact to re-derive them from); **no Kiem state was written or
   modified** by this unit.
3. Candidate status remains **QUEUED / UNRANKED / NOT STAGED** exactly as committed in the
   config (comments lines 2–9, 64–71, 153–168).
4. **Future unblock condition (recorded for the next tick, not acted on now):** free disk must
   reach `free_now ≥ 30 GiB + 19,613,407,328 B + launch headroom` so that post-staging free stays
   `>= 30 GiB` (i.e. `free_now ≥ ~49.27 GiB` before staging may start), or a policy change must be
   explicitly committed. Re-verify on-disk size == 19,613,407,328 B and `sha256sum ==
   cc134bbc…` (the HF LFS oid) only at that future staging time.

## 7. Evidence index

| Fact | Where measured / cited |
|---|---|
| Repo clean at b1ad34388a7ec02ccb6598d2e0603eeae14d2582 | `git status --porcelain=v1` + `git rev-parse HEAD` (13:33Z) |
| Config SHA-256 85851d6b44c5f15d…, tracked, last commit f1d450d | `shasum -a 256 configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`; `git log -1 -- configs/…` |
| Candidate identity, bytes, LFS oid (pinned provenance, NOT local) | config lines 1, 47, 50, 66–68, 126–128 |
| Free 41,377,234,944 B = 38.5356 GiB; above 30 GiB by 9,164,980,224 B | `df -Pk /Users/tijs` (final read 13:33Z) |
| RAM 34,359,738,368 B = 32 GiB | `sysctl hw.memsize` |
| Runner 0.1.2-dev (build 1, commit a302733), AppleClang 21.0.0.21000101 | `runner/.dspark-head/build/bin/llama-server --version` |
| Model absent (no hub snapshot, no file, no models dir, placeholder path gone) | `ls ~/.cache/huggingface/hub`; bounded `find`; `ls ~/.local/share/local-model-bench/models` |
| 0 rows in log.jsonl; 0 lines in LEADERBOARD.md | `grep -c -i gravity results/log.jsonl` → 0; `results/LEADERBOARD.md` → 0 |
| No bench provider (config.yaml, hermes_provider: null) | `grep -i gravity ~/.hermes/profiles/bench/config.yaml` (no match); config line 99 |
| No bench process; port 8017 free; listeners enumerated and ruled out | `ps aux` filter; `lsof -nP -iTCP:8017 -sTCP:LISTEN` (empty); `lsof -nP -iTCP -sTCP:LISTEN` |
| 30.0 GB pre-launch floor (committed) | `runner/bench_common.py:78`; enforcement `runner/run_bench.py:546-548` |
| Post-staging arithmetic 20.269 GiB; +288,991,136 B over 20 GiB; −10,448,427,104 B under 30 GiB | computed from the two measured/pinned byte values above (section 5) |

*All measurements taken read-only 2026-09-19T13:33Z (± minutes). Remote HF values (revision,
size, LFS oid) are pinned provenance carried from the committed config — not local hashes. No
file other than this artifact was created, edited, staged, or committed.*
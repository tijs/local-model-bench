# Qwen3.6 track — AXQ 4-bit preflight, BLOCKED, 2026-09-17

CPU-only preflight/report cycle for the authorized AX-Qwen3.6 AXQ 4-bit gate.
**No model, probe, server, benchmark, wrapper, or build ran; no weights were
downloaded or staged; no tooling installed; no cache deleted; no
`/Users/tijs/projects/mei` touch; no Kiem mutation; no
results/log.jsonl / LEADERBOARD / configs / runner / tasks / checks /
fixtures change; no restart/stop of anything (CoCore untouched, remains off);
no publish/push; no secrets used.** The only repository write is this
artifact, committed as one scoped report-only commit.

Source labels (repo convention): **Measured** = verified live this tick
(read-only local checks); **Carried** = previously recorded facts re-verified
read-only where cheap; **Decision** = this preflight's judgment.

## 1. Checkout state (Measured)

- HEAD `2beddd7667bf147d9bce1d6bad3f3494357ec7b0` (`artifacts: Qwen3.6
  post-ManniX-complete decision audit`), branch `main`, **ahead 51 / behind 0**
  of origin, working tree clean (`git status --porcelain=v1` empty before and
  after every check).
- Prior audit of record: `artifacts/qwen36-decision-audit-post-mannix-complete-20260916.md`
  (HEAD commit 2beddd7). Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`
  read read-only (`kiem show`); open todos unchanged (plan todo 13 daily
  discovery consume, todo 19 AXQ 4-bit gate, todo 20 AXQ 6-bit gate;
  `2c419bd1` todo 5 Gravity remains **Queued**). No AXQ-leg todo exists in
  Kiem; queue is parent-authorized per delegation.

## 2. Disk — exact bytes and gate arithmetic (Measured)

Write-time measurement (timestamp **2026-09-17 01:22 CEST / UTC+02:00**):

- `statvfs`/`shutil.disk_usage` on `/Users/tijs/projects/local-model-bench`
  (and `/Users/tijs/projects`, same volume): **free = 51,960,860,672 bytes =
  48.392323 GiB = 51.961 decimal GB** (second sample this tick earlier read
  51,957,354,496 B = 48.389057 GiB; ~3.5 MB normal drift between samples).
- Carried parent figure for comparison: ~51,957,870,592 B (~48.39 GiB),
  shortfall ~3,339,833,344 B — consistent with my samples; live recheck wins.

Gate arithmetic (exact, GiB = ×2^30):

| Gate | Threshold bytes | Measured free vs threshold | Verdict |
|---|---:|---:|---|
| Pre-staging | 51.5 GiB = **55,297,703,936 B** | 51,960,860,672 − 55,297,703,936 = **−3,336,843,264 B = −3.1080 GiB short** | **FAIL** |
| Launch (runner `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GiB at `run_bench.py:545`, Carried) | 30 GiB = 32,212,254,720 B | +19,748,605,952 B = +18.3923 GiB headroom | PASS (alone) |
| Post-staging floor | 20 GiB = 21,474,836,480 B | +30,486,024,192 B = +28.3923 GiB headroom | PASS (alone) |

Constraint check (Measured arithmetic): **if the full package were staged
today**, 51,960,860,672 − 23,120,765,421 = **28,840,095,251 B = 26.859 GiB**
would remain free — **below the 30 GiB launch gate**, so even a complete
staging today could not launch. The 4-bit package is 23,120,765,421 B
(21.533 GiB; Carried public tree size, re-stated from pinned-revision audit).

**Pre-staging gate NOT met: 48.392 GiB < 51.5 GiB** by 3.108 GiB
(≈3.337e9 bytes). Required ≈ 30 GiB + 21.53 GiB ≈ 51.5 GiB pre-staging;
current free is short. Memory: `hw.memsize` = 34,359,738,368 B = 32 GiB
(Measured; unchanged — preflight item, not the blocker).

## 3. AXQ model / config / staging presence (Measured, all absent)

- No `configs/*axq*` and no `configs/Qwen3.6-35B-A3B-MLX-AXQ-*` directory
  (configs/ holds only Qwen3.6-35B-A3B-OptiQ and
  Qwen3.6-27B-A3B-Coder-MTP-GGUF).
- HF hub cache (`~/.cache/huggingface/hub/`) contains exactly 4 model dirs —
  EigenLabs mixed-4bit, ManniX-ITA GGUF, mlx-community 4bit,
  mlx-community 4bit-DWQ. **No AutomatosX / AX-Qwen3.6 entry (grep empty).**
- No staging dir, no `models/` dir. **Zero local presence → no
  existing-cache acceptance leg possible.**

## 4. Processes and ports (Measured)

- No `run_bench`, `mei`, `llama-server`/`llama`, `vllm`, `omlx`, `mlx_lm`,
  or `cocore` process (`ps aux` grep; prior orphan PID 37099 no longer
  exists).
- No listener on benchmark-family ports 8017 / 8020–8026 (incl. 8024, 8025) /
  8082 / 8080 / 8090 / 11434 (`lsof -nP -iTCP -sTCP:LISTEN`).
- Current listeners are macOS system + Hermes tooling only: `rapportd` 49152,
  `ControlCenter` 5000/7000, Hermes local tools 127.0.0.1:8765/8766/9119 —
  none benchmark-owned.

## 5. Result-state evidence — unchanged (Measured)

- `results/log.jsonl`: 4,591,611 B, **4,120 lines**, mtime 2026-09-16
  21:30:48, sha256[:16] `e25da61d7ef02eeb` — byte-count, row count, and mtime
  identical to the post-ManniX-complete audit record; tracked and clean in
  git. No change.
- `results/LEADERBOARD.md`: 229,585 B, mtime 2026-09-16 21:30:53, sha256[:16]
  `54998b73df523f1b` — unchanged; no regeneration performed (append-only).
- No config/runner/tasks/checks/fixtures modification in `git status`.

## 6. Decision (Decision)

- **Gate remains BLOCKED.** Pre-staging disk requirement (≥ 51.5 GiB free) is
  not met: 48.392 GiB measured (+3.5 MB drift observed; short ≈ 3.108 GiB ≈
  3.337e9 B). Additionally, staging the full 4-bit package today would leave
  26.859 GiB — still under the 30 GiB launch gate — so neither staging nor
  launch is justified on current disk.
- **Defer without downloading, staging, or running.** No cache to run from;
  no AXQ config exists; unproven Mei/vmlx compatibility (level-B mlx-lm card
  claim only — Carried); zero local presence; no runtime-boundary
  investigation this tick (nothing to investigate on absent weights).
- Queue untouched and in order: **AXQ 4-bit → AXQ 6-bit → gated Gravity**
  (`2c419bd1` todo 5 @ `ee52d6f6ff6572ed72851dbaac5a79ef982a74a4` stays
  Queued). No Kiem mutation; no closure.
- No test suites run this cycle (bounded preflight; nothing changed that
  would require them); read-only checks: AGENTS.md, `git status`/log, Kiem
  plan+todos read, disk statvfs/shutil samples, staging arithmetic,
  ps/lsof scans, HF hub listing, log.jsonl/LEADERBOARD hash+count+mtime.

### Next gate (unchanged, unlaunched)

**AXQ 4-bit Mei 25-row acceptance leg** — `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`
at immutable revision `d880b11584ae6ee1e18a1e86f082a8397cf2ce24` (package
23,120,765,421 B). Preconditions per plan todo 19: fresh single-writer audit
proving **≥ 51.5 GiB free before staging**, ≥ 30 GiB free at launch, ≥ 20 GiB
after staging, sufficient memory; committed Mei config (port 8024,
`VMLX_ENABLE_UNSAFE_COMPILE=0`, plain+streaming, native tools, 25-row
battery 2+8+5+3+4+3); pre-run config snapshot, append-only rows, transcripts,
prompt results, **archived server log (explicit requirement from prior
audit)**, runner SHA, provenance, failure classification, teardown/free-port
evidence. Then AXQ 6-bit (bc8b9a1d4b…) after the 4-bit leg is terminal and
committed; then the gated Gravity slot.

## 7. Side-effect statement (Measured)

- Only file created: **this artifact**
  (`artifacts/qwen36-axq4-preflight-blocked-20260917.md`); committed as one
  report-only commit (`git diff --check` clean); no other path staged. No
  results/ change, no Kiem mutation, no push/GitHub activity, no CoCore
  action, no `/Users/tijs/projects/mei` touch, no cache deletion, no weight
  download, no credentials.
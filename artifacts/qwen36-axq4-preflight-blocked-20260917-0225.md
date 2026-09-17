# Qwen3.6 track — AXQ 4-bit preflight, BLOCKED, 2026-09-17 02:31 (tick 0225)

CPU-only preflight/report continuation cycle (02:25 tick) for the authorized
AX-Qwen3.6 AXQ 4-bit gate. **No model, probe, server, benchmark, wrapper, or
build ran; no weights were downloaded or staged; no tooling installed; no cache
deleted; no `/Users/tijs/projects/mei` touch; no Kiem mutation; no
results/log.jsonl / LEADERBOARD / configs / runner / tasks / checks / fixtures
change; no restart/stop of anything (CoCore untouched, remains off); no
publish/push; no secrets used.** The only repository write is this artifact,
committed as one scoped report-only commit.

Source labels (repo convention): **Measured** = verified live this tick
(read-only local checks); **Carried** = previously recorded facts re-verified
read-only where cheap; **Decision** = this preflight's judgment.

## 1. Checkout state (Measured)

- HEAD `7aa0d02` (`artifacts: Qwen3.6 AXQ 4-bit preflight blocked 2026-09-17`),
  branch `main`, **ahead 52 / behind 0** of origin, working tree clean
  (`git status --porcelain=v1` empty before every check this tick).
- Prior tick artifact of record: `artifacts/qwen36-axq4-preflight-blocked-20260917.md`
  (HEAD commit 7aa0d02) — read only, **not edited**; this file is the new
  `-0225` continuation report.
- Kiem plan note `7f5c67e7-b564-4df3-8209-14f7443b56e2` read read-only via the
  local kiem CLI (`/Users/tijs/projects/kiem/target/release/kiem show` + `kiem
  todos` from repo cwd); `~/.kiem/kiem.db` size/mtime verified unchanged by the
  reads (2,883,584 B, mtime 2026-09-16 23:02:35 CEST → no mutation). Plan note
  modified 2026-09-16T21:02:19Z, content version `ee38ace5…`. Open todos
  unchanged: plan todo 13 (daily discovery consume), todo 19 (AXQ 4-bit gate),
  todo 20 (AXQ 6-bit gate); discovery note `2c419bd1` todo 5 (Gravity) remains
  **Queued**. Queue is parent-authorized per delegation; no Kiem mutation, no
  closure.

## 2. Disk — exact bytes and gate arithmetic (Measured)

Write-time measurement (timestamp **2026-09-17 02:31:28 CEST / UTC+02:00**):
three live samples this tick via `statvfs`/`shutil.disk_usage` on
`/Users/tijs/projects/local-model-bench` (and `/`, same volume): 51,951,058,944 B
→ 51,950,723,072 B → **51,950,723,072 B** (≤0.4 MB drift; final two samples
identical). Reported free: **51,950,723,072 bytes = 48.382881 GiB = 51.951
decimal GB**.

Gate arithmetic (exact, GiB = ×2^30):

| Gate | Threshold bytes | Measured free vs threshold | Verdict |
|---|---:|---:|---|
| Pre-staging | 51.5 GiB = **55,297,703,936 B** | 51,950,723,072 − 55,297,703,936 = **−3,346,980,864 B = −3.1171 GiB short** | **FAIL** |
| Launch (runner `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GiB, Carried) | 30 GiB = 32,212,254,720 B | +19,738,468,352 B = +18.3829 GiB headroom | PASS (alone) |
| Post-staging floor | 20 GiB = 21,474,836,480 B | +30,475,886,592 B = +28.3829 GiB headroom | PASS (alone) |

Constraint check (Measured arithmetic): **if the full package were staged
today**, 51,950,723,072 − 23,120,765,421 = **28,829,957,651 B = 26.849990 GiB**
would remain free — **below the 30 GiB launch gate**, so even a complete
staging today could not launch. The 4-bit package is 23,120,765,421 B
(21.532891 GiB; Carried public tree size, re-stated from pinned-revision
audit).

**Pre-staging gate NOT met: 48.383 GiB < 51.5 GiB** by 3.117 GiB (3,346,980,864 B).
Consistent with the dispatch baseline (51,952,705,536 B / 48.3847 GiB, expected
shortage ≈ 3.116 GiB; live recheck wins: 3.1171 GiB short, drift ≈ 2 MB).
Memory (Measured, not the blocker): `hw.memsize` = 34,359,738,368 B = 32 GiB;
`vm_stat` free pages 1,239,796 × 16,384 = 20,312,817,664 B = 18.918 GiB free.

## 3. AXQ model / config / staging presence (Measured, all absent)

- No `configs/*axq*` and no `configs/Qwen3.6-35B-A3B-MLX-AXQ-*` directory;
  `configs/` Qwen3.6 entries are only: 27B-A3B-Coder-MTP-GGUF, 35B-A3B,
  35B-A3B-DWQ, 35B-A3B-OptiQ, 35B-A3B-Uncensored, 35B-A3B-mixed46,
  35B-A3B-textonly. **Zero AXQ config.**
- HF hub cache (`~/.cache/huggingface/hub/`) contains exactly 4 model dirs —
  EigenLabs mixed-4bit, ManniX-ITA GGUF, mlx-community 4bit, mlx-community
  4bit-DWQ. **No AutomatosX / AX-Qwen3.6 entry (grep empty).**
- No `models/` dir in the repo, no staging dir under `~/projects` or
  `/Users/tijs/staging`; only big cache file on the volume is the pre-existing
  vllm-mlx prefix-cache entry for Qwen3-Coder-30B (`~/.cache/vllm-mlx/…`,
  unrelated to AXQ, untouched).
- `/tmp/axq*` and `/tmp/axq-audit/` hold KB-scale **audit scratch metadata**
  (README/config.json/tree.json copies from the 2026-09-16 public-metadata
  audits, no weights); left in place, not staging. **Zero local model presence
  → no existing-cache acceptance leg possible.**

## 4. Processes and ports (Measured)

- No `run_bench`, `mei`, `llama-server`/`llama`, `vllm`, `omlx`, `mlx_lm`,
  `qwen`, or `cocore`/Kiem daemon process (`ps aux` greps empty).
- No listener on benchmark-family ports 8017 / 8020–8026 (incl. 8024, 8025) /
  8082 / 8080 / 8090 / 11434 (`lsof -nP -iTCP -sTCP:LISTEN`).
- Current listeners are macOS system + Hermes tooling only: `rapportd` 49152,
  `ControlCenter` 5000/7000, Hermes local tools 127.0.0.1:8765 (deno) /
  8766 (python3.1) / 9119 (python3) — none benchmark-owned.

## 5. Result-state evidence — unchanged (Measured)

- `results/log.jsonl`: 4,591,611 B, **4,120 lines**, mtime 2026-09-16 21:30:48,
  sha256 `e25da61d7ef02eeb84b8aaeb8fcf242c89323284d7b2f257abebedfbeefe20ae` —
  byte count, row count, mtime, and hash identical to the prior audit records;
  tracked and clean in git. No change.
- `results/LEADERBOARD.md`: 229,585 B, mtime 2026-09-16 21:30:53, sha256
  `54998b73df523f1b69f97fe3b637892d021aee2a8e813832d51c2308e803e0df` —
  unchanged; no regeneration performed (append-only).
- No config/runner/tasks/checks/fixtures modification in `git status`.

## 6. Decision (Decision)

- **Gate remains BLOCKED.** Pre-staging disk requirement (≥ 51.5 GiB free) is
  not met: 48.382881 GiB measured (≈ 3.1171 GiB short ≈ 3.347e9 B).
  Additionally, staging the full 4-bit package today would leave 26.850 GiB —
  still under the 30 GiB launch gate — so neither staging nor launch is
  justified on current disk.
- **Defer without downloading, staging, or running.** No cache to run from; no
  AXQ config exists; unproven Mei/vmlx compatibility (level-B mlx-lm card claim
  only — Carried); zero local presence; no runtime-boundary investigation this
  tick (nothing to investigate on absent weights).
- Queue untouched and in order: **AXQ 4-bit → AXQ 6-bit → gated Gravity**
  (`2c419bd1` todo 5 @ `ee52d6f6ff6572ed72851dbaac5a79ef982a74a4` stays
  Queued). No Kiem mutation; no closure.
- No test suites run this cycle (bounded preflight; nothing changed that would
  require them); read-only checks: AGENTS.md, `git status`/log, Kiem plan note +
  todos via kiem CLI (db mtime/size verified unchanged), disk statvfs/shutil
  samples, staging arithmetic, ps/lsof scans, HF hub + configs + /tmp listing,
  log.jsonl/LEADERBOARD hash+count+mtime.

### Next gate (unchanged, unlaunched)

**AXQ 4-bit Mei 25-row acceptance leg** — `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`
at immutable revision `d880b11584ae6ee1e18a1e86f082a8397cf2ce24` (package
23,120,765,421 B). Preconditions per plan todo 19: fresh single-writer audit
proving **≥ 51.5 GiB free before staging**, ≥ 30 GiB free at launch, ≥ 20 GiB
after staging, sufficient memory; committed Mei config (port 8024,
`VMLX_ENABLE_UNSAFE_COMPILE=0`, plain+streaming, native tools, 25-row battery
2+8+5+3+4+3); pre-run config snapshot, append-only rows, transcripts, prompt
results, archived server log, runner SHA, provenance, failure classification,
teardown/free-port evidence. Then AXQ 6-bit (`bc8b9a1d4b…`) after the 4-bit leg
is terminal and committed; then the gated Gravity slot.

## 7. Side-effect statement (Measured)

- Only file created: **this artifact**
  (`artifacts/qwen36-axq4-preflight-blocked-20260917-0225.md`); pre-staging
  `git status` recheck showed this artifact as the **only** untracked/modified
  path; committed as one report-only commit via a safe commit-message file;
  `git diff --check` clean. No other path staged, no results/ change, no Kiem
  mutation, no push/GitHub activity, no CoCore action, no
  `/Users/tijs/projects/mei` touch, no cache deletion, no weight download, no
  credentials.
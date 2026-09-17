# Qwen3.6 track — AXQ 4-bit preflight, BLOCKED, 2026-09-17 03:35 (fresh tick)

Fresh CPU-only preflight for the authorized AX-Qwen3.6 AXQ 4-bit gate.
**No model, probe, server, benchmark, wrapper, or build ran; no weights
downloaded or staged; no tooling installed; no cache deleted; no
`/Users/tijs/projects/mei` touch; no Kiem mutation; no results/log.jsonl /
LEADERBOARD / configs / runner / tasks / checks / fixtures change; no
restart/stop of anything (CoCore untouched, remains off); no publish/push; no
secrets used.** The only intended repository change is this artifact, left
uncommitted for the parent's independent inspection and single report-only
commit.

Source labels (repo convention): **Measured** = verified live this tick
(read-only local checks); **Carried** = previously recorded facts re-stated
(read-only re-verified where cheap); **Decision** = this preflight's judgment.

## 1. Checkout state (Measured)

- HEAD `928ef3d` (full SHA `928ef3dae7bba941001ad8bca39d53c9bba97708`,
  `artifacts: Qwen3.6 AXQ 4-bit preflight blocked 2026-09-17 02:31 (tick
  0225)`), branch `main`, **ahead 53 / behind 0** of origin/main
  (`git rev-list --left-right --count origin/main...main` = `0 53`), working
  tree **clean before the artifact** (`git status --porcelain` empty).
- Prior tick artifact of record: `artifacts/qwen36-axq4-preflight-blocked-20260917-0225.md`
  (committed at HEAD 928ef3d) — read only, **not edited**; this file is the new
  `-0335` continuation report.
- Kiem plan note `7f5c67e7-b564-4df3-8209-14f7443b56e2` read read-only
  (Carried state, re-verified via local kiem CLI): **todo 19 (AXQ 4-bit gate)
  and todo 20 (AXQ 6-bit gate) remain open**; daily discovery todo 13 and
  Gravity todo 5 remain **Queued**. No Kiem mutation, no closure.

## 2. Disk — exact bytes and gate arithmetic (Measured)

Fresh `statvfs` samples this tick on `/Users/tijs/projects/local-model-bench`
(and `/`, same volume) ended at **54,352,244,736 bytes free =
50.6194725039 GiB = 54.352244736 decimal GB** (03:35 CEST).

Gate arithmetic (exact, GiB = ×2^30):

| Gate | Threshold bytes | Measured free vs threshold | Verdict |
|---|---:|---:|---|
| Pre-staging | 51.5 GiB = **55,297,703,936 B** | 54,352,244,736 − 55,297,703,936 = **−945,459,200 B = −0.8805274963 GiB short** | **FAIL** |
| Launch (runner `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GiB, Carried) | 30 GiB = 32,212,254,720 B | +22,139,990,016 B = +20.6194725037 GiB headroom | PASS (alone) |
| Post-staging floor | 20 GiB = 21,474,836,480 B | +32,877,408,256 B = +30.6194725037 GiB headroom | PASS (alone) |

Constraint check (Measured arithmetic): the pinned 4-bit public package is
**23,120,765,421 B** (Carried immutable-tree size). **If the full package were
staged today**, 54,352,244,736 − 23,120,765,421 = **31,231,479,315 B =
29.0865817247 GiB** would remain free — **980,775,405 B = 0.9141430678 GiB
below the 30 GiB launch threshold (FAIL)**. Even a complete staging today could
not launch, so **staging today is not justified** (pre-staging gate unmet
anyway).

Memory (Measured, **not** the blocker): `hw.memsize` = 34,359,738,368 B =
32 GiB; `vm_stat` free pages 1,232,220 × 16,384 B/page = 20,188,692,480 B =
18.8021850586 GiB free.

## 3. AXQ model / config / staging presence (Measured, all absent)

- **No AXQ/AutomatosX model** in `/Users/tijs/.local/share/local-model-bench/mei-models`
  or `~/.cache/huggingface/hub` (grep empty).
- **No AXQ config exists under `configs/`** (no `configs/*axq*`).
- **No existing-cache acceptance path** — zero local model presence means no
  cache-acceptance leg is possible.

## 4. Processes and ports (Measured)

- **No exact benchmark runner/suite/model processes** found (`ps` greps for
  run_bench/mei/llama/vllm/mlx/qwen runner & server patterns empty).
- **No listeners** on benchmark-family ports 8012 / 8016 / 8017 / 8018 / 8020 /
  8024 / 8025 / 8026 / 8027 / 8080 / 8082 / 8090 / 11434 (`lsof -nP -iTCP
  -sTCP:LISTEN`). Remaining listeners are macOS system + Hermes tooling only.

## 5. Result-state evidence — unchanged (Measured)

- `results/log.jsonl`: **4,591,611 B, 4,120 nonblank rows**, SHA-256
  `e25da61d7ef02eeb84b8aaeb8fcf242c89323284d7b2f257abebedfbeefe20ae`, mtime
  2026-09-16 21:30:48 CEST — identical to prior records; tracked and clean.
- `results/LEADERBOARD.md`: **229,585 B**, SHA-256
  `54998b73df523f1b69f97fe3b637892d021aee2a8e813832d51c2308e803e0df`,
  unchanged from 2026-09-16; no regeneration performed (append-only).
- No config/runner/tasks/checks/fixtures modification in `git status`.

## 6. Decision (Decision)

- **Gate BLOCKED.** Pre-staging disk requirement (≥ 51.5 GiB free) not met:
  50.6194725039 GiB measured, **0.8805274963 GiB (945,459,200 B) short**.
  Staging the full 4-bit package today would leave 29.0865817247 GiB — still
  **0.9141430678 GiB below the 30 GiB launch gate** — so neither staging nor
  launch is justified today.
- **Do not download / stage / run.** No weights, no AXQ config, no
  existing-cache acceptance path; memory is not the blocker.
- **No tests run** because no source changed (bounded read-only preflight;
  harness state byte-identical).
- Queue remains and in order: **AXQ 4-bit → AXQ 6-bit → gated Gravity**.
- **No public action**; the only intended change is this new artifact.

### Next gate (unchanged, unlaunched)

**AXQ 4-bit Mei 25-row acceptance leg** —
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` at immutable revision
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24`. Requirements: **committed
reproducible Mei config** (**port 8024**), exact served identity/revision
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24`, safe
**`VMLX_ENABLE_UNSAFE_COMPILE=0` / no unsafe compiled decode**, **plain +
streaming / native tools**, **25 rows (2+8+5+3+4+3)**, and
provenance + archived server log + transcripts + teardown/free-port evidence.
Then AXQ 6-bit after the 4-bit leg is terminal and committed; then the gated
Gravity slot.

## 7. Side-effect statement (Measured)

- Only file created: **this artifact**
  (`artifacts/qwen36-axq4-preflight-blocked-20260917-0335.md`); post-write
  `git status` shows it as the **only** untracked path. Not committed, not
  staged — left for the parent's independent inspection and single report-only
  commit (`git diff --check` clean). No other path touched, no results/ change,
  no Kiem mutation, no push/GitHub activity, no CoCore action, no
  `/Users/tijs/projects/mei` touch, no cache deletion, no weight download, no
  credentials.
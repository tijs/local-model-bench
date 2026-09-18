# AXQ6 Disposable-Artifact Cleanup Evidence — 2026-09-18

**Operation:** Explicit, user-authorized cleanup of the retired AXQ6
(`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`) disposable artifacts from the
local-model-bench data root. Build files, staged source/vmlx working copies,
staged model payload, runtime KV cache, and scratch/probe logs were deleted.
All committed repository evidence, append-only result history, raw probe
evidence, the retired config, and the model provenance sidecar were preserved.

**Authorization:** User's exact words: *"[Tijs Teulings] Also clean up all the
build files and other related artifacts for axq6 which we now no longer need"*.

**Start UTC:** `2026-09-18T16:01:22Z` · **End UTC:** `2026-09-18T16:01:52Z`
**Data root:** `/Users/tijs/.local/share/local-model-bench`
**Repo:** `/Users/tijs/projects/local-model-bench` (main, clean before and after)

## 1. Pre-deletion re-checks (live state)

- **Processes:** `ps aux | grep -iE "mei|axq|qwen36|vmlx|mlx|run_bench|llama-server"`
  → no bench/model/build/probe process. Only match was the unrelated macOS
  system ExtensionKit process `DateTimeIntentsExtension` (PID 1222, 0.0% CPU).
- **Listeners:** ports **8024 and 8025** free (`lsof -nP -iTCP:8024 -iTCP:8025` empty).
- **Open handles:** `lsof +D` over the data root plus per-directory `lsof` on all
  5 directory targets → **0 handles** on every target.
- **Git state:** `main` at `5319dc8334dae7ac18b1c180f8383129c6ac9f24`
  ("config(AXQ6): retire AXQ6 from the prospect queue + guard test"),
  `git status` clean, `origin/main...main` = `0 87` (ahead 87, **no push**).
  The Qwen3.6 benchmark cron job (`ba2552668fdf`) is paused during cleanup.

## 2. External reference verification (recoverability, re-checked pre-delete)

- **Repo:** `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`
- **Public:** `private: false` (via `https://huggingface.co/api/models/...`)
- **Live revision (resolved commit):** `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`
- **Tree:** 23 entries; the 5 `model-*.safetensors` shards, `mtp.safetensors`,
  `vision.safetensors`, and metadata files are all present upstream.
- **Local ↔ upstream byte match:** local payload shard sizes match upstream tree
  sizes exactly (e.g. `model-00001-of-00005.safetensors` 5,367,600,594 B both
  sides; `mtp.safetensors` 1,689,283,776 B both sides; `vision.safetensors`
  893,179,624 B both sides). The local staged payload is fully recoverable.
- Verdict: local copies are disposable; nothing is lost by deletion.

## 3. Disk BEFORE (pre-deletion)

`/System/Volumes/Data` (disk3s5) — the volume hosting the data root:

| Metric | Before |
|---|---|
| Total | 482,797,652 KB (460 GiB) |
| Used | 392,877,760 KB (374.7 GiB) |
| Available | 62,137,900 KB (59.3 GiB) |
| Capacity | 87% |

## 4. Deleted targets with per-target sizes (du-reported 1024-byte blocks)

| # | Absolute path | du KB | bytes (KB×1024) |
|---|---|---|---|
| 1 | `/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050` | 3,101,096 | 3,175,522,304 |
| 2 | `/Users/tijs/.local/share/local-model-bench/mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb-vmlxfix15bada58` | 3,320 | 3,399,680 |
| 3 | `/Users/tijs/.local/share/local-model-bench/vmlx-swift` | 126,456 | 129,490,944 |
| 4 | `/Users/tijs/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP` (payload only) | 26,353,280 | 26,985,758,720 |
| 5 | `/Users/tijs/.local/share/local-model-bench/mei-runtime/kv-axq6-mtp` | 195,036 | 199,716,864 |
| 6 | `/Users/tijs/.local/share/local-model-bench/staging-logs/axq6-stage-20260918.log` | 4 | 4,096 |
| 7 | `/Users/tijs/.local/share/local-model-bench/scratch-typecheck/axq6-evaluate-refactor.diff` | 4 | 4,096 |
| 8 | `/Users/tijs/.local/share/local-model-bench/scratch-typecheck/axq6-patched-build.log` | 12 | 12,288 |
| 9 | `/Users/tijs/.local/share/local-model-bench/scratch-typecheck/axq6-pathdep-build.log` | 8,012 | 8,204,288 |
| 10 | `/Users/tijs/.local/share/local-model-bench/scratch-typecheck/axq6-repro.swift` | 4 | 4,096 |
| 11 | `/Users/tijs/.local/share/local-model-bench/scratch-typecheck/axq6-repro-fixed.swift` | 4 | 4,096 |
| — | **Aggregate (sum of du -ck)** | **29,787,228** | **30,502,121,472** |

Deletion performed in two explicit batches of exact absolute paths only
(`rm -f` for the 6 files, `rm -rf` for the 5 directories). No globs, no parent
roots, no adjacent files. Parent containers (`mei-source/`, `mei-models/`,
`mei-runtime/`, `staging-logs/`, `scratch-typecheck/`) were **not** removed;
`mei-models/` still holds other staged payloads/provenance.

## 5. Post-delete verification (all pass)

- **All 11 targets absent:** loop over the exact allowlist reported *GONE ok*
  for every path (fail=0).
- **Retained items exist:** see KEEP list in §6 — all present (`check ok=1`).
- **Provenance sidecar preserved:** `mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP.provenance.json`
  (1,388 B) confirmed present after payload deletion.
- **Processes/listeners:** no AXQ6/mei/run_bench process remains; ports 8024/8025
  still free.
- **Parents intact:** `mei-models`, `mei-source`, `mei-runtime`, `staging-logs`,
  `scratch-typecheck` all still exist.

## 6. Disk AFTER + reclaimed space

`/System/Volumes/Data` (disk3s5):

| Metric | After |
|---|---|
| Total | 482,797,652 KB (460 GiB) |
| Used | 363,303,136 KB (346.5 GiB) |
| Available | 91,712,524 KB (87.5 GiB) |
| Capacity | 80% |

- **Used decreased / Available increased:** 29,574,624 KB (28.2 GiB).
- Pre-deletion `du` aggregate: 29,787,228 KB (28.4 GiB). The small gap vs. the
  filesystem delta (212,604 KB) is expected APFS accounting/sparse/rounding
  behavior, per the guarded-cleanup convention.

## 7. KEEP list (preserved, verified present)

- `/Users/tijs/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP.provenance.json` — recoverability metadata for the deleted payload (revision `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`).
- `results/log.jsonl` — append-only benchmark rows (0 AXQ6 rows; untouched).
- `results/LEADERBOARD.md` — untouched.
- `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml` — retired config
  (`orchestration.viable: retired`); untouched.
- `artifacts/qwen36-axq6-native-gate-direct-probe-20260918.md`
- `artifacts/qwen36-axq6-native-gate-typecheck-fix-20260918.md`
- `artifacts/qwen36-axq6-native-gate-build-failure-20260918-092556z.md`
- `results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/` — raw probe
  evidence incl. `probe.json` + `server.log.snapshot`; untouched.
- Unrelated: `mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP.provenance.json`,
  other staged payloads, Mei `~/projects/mei` Casks/tap, and any unrelated
  caches/worktrees.

## 8. Append-only history / raw evidence preservation (explicit)

**Append-only benchmark history and raw evidence were NOT modified, rewritten,
or deleted:** `results/log.jsonl` and `results/LEADERBOARD.md` are byte-untouched;
no AXQ6 rows exist in the log and none were injected or removed; the
`results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/` raw probe evidence
directory is intact; the retired config is preserved exactly as committed
(`5319dc8`). This cleanup deleted only the disposable local build/source/payload/
runtime/scratch copies named in §4, which remain recoverable from the verified
public upstream revision. No public activity; no secrets involved.

## 9. Repository change

- Evidence file `artifacts/axq6-disposable-cleanup-20260918.md` now contains the
  above; it is the **only** change in the cleanup commit (narrow message, no push).
- Cleanup commit SHA: see `git rev-parse HEAD` at commit time (recorded in the
  commit history; verified `git show --name-only --format=` lists exactly this
  evidence path).
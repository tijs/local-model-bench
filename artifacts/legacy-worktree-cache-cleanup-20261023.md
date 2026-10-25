# Old worktree and inactive Mei model-cache cleanup

## Authorization and exact allowlist

Tijs asked to clear old worktrees and the cache to reclaim disk. This cleanup removes only two clean obsolete worktree checkouts and an inactive CoCore-managed Qwen cache that was byte-identical to a retained local-model-bench copy, plus that server's now-unused KV cache. No branch refs, model-bench results, configs, source work, or shared package caches are deleted.

DELETE (full exact paths):

- `/Users/tijs/projects/local-model-bench-current-summary-archive-20261020` — clean worktree at `ec86488ee4368c4d61014058883ee4b2d0b44dae`, 35,952 KiB. Its branch `docs/current-summary-archive-20261020` is already an ancestor of main; preserve the branch ref.
- `/Users/tijs/.hermes/cache/scratch/minicpm-v47-phase-diag-native-20261021-a1/mei-source` — clean detached worktree at `8e9b0a99b402655c51af7b771638f64dc6faa03c`, 6,648 KiB. Preserve `work/minicpm-v47-mei-20261019` at that commit; the related Kiem plan remains open and the checkout can be recreated from the branch.
- `/Users/tijs/.cache/mei/models/Qwen3.6-35B-A3B-4bit-textonly` — 19,078,188 KiB. This inactive CoCore cache is an exact duplicate of the retained local-model-bench text-only derivative; identity manifest: `artifacts/qwen-cache-duplicate-manifest-20261023.json`.
- `/Users/tijs/.cache/mei/runtime/kv/qwen36-text` — 782,668 KiB; generated KV state for the unloaded Qwen service, not benchmark results.

## Pre-delete evidence

- At 2026-10-23T19:13:33Z, `/System/Volumes/Data` reported 24,010,293,248 bytes free (22.361 GiB). Aggregate `du` for the four exact delete targets: 20,381,138,944 bytes (18.981 GiB). APFS `df` delta will be measured separately.
- Both old worktrees were clean, had no open handles, and their branch refs were verified. No stale worktree registrations were reported by `git worktree prune --expire=now --dry-run --verbose`.
- The pinned upstream source `mlx-community/Qwen3.6-35B-A3B-4bit@38740b847e4cb78f352aba30aa41c76e08e6eb46` returned HTTP 200 at its revision-specific tree endpoint (17 entries; four upstream weight shards total 20,402,204,271 bytes). The retained local-model-bench sidecar records the text-only derivative and four local shards totaling 19,509,024,480 bytes. All 17 canonical files in the CoCore cache matched the retained copy by size and SHA-256; only Hugging Face transfer/cache metadata differed. Full file hashes are in the identity manifest.
- Both exact services were already unloaded (`dev.cocore.provider`, `dev.tijs.mei.qwen36-text`); target PIDs were absent, ports 8024/8017 were free, and `lsof +D` returned exit 1 with empty output for each deletion target. No runner, Swift build/test, or model-serving process was active. The launch-agent plists and selected-model setting are left unchanged; a later manual restart may re-download the cache.

## KEEP

- Primary Mei/local-model-bench checkouts and all user-owned untracked research files.
- The current Flint verification worktree/build and the dirty forced-disk-gate worktree; these are current/incomplete, not old cleanup targets.
- Branch refs `docs/current-summary-archive-20261020` and `work/minicpm-v47-mei-20261019`.
- The retained Qwen3.6 text-only model and provenance at `/Users/tijs/.local/share/local-model-bench/mei-models/`, the primary Ornith model, all other model payloads, configs, results, logs, and Kiem plans.
- `~/.cache/huggingface/hub` (only 16 KiB metadata at inventory), shared SwiftPM/Xcode caches, and all other project/task scratch directories.

## Post-delete verification

- At 2026-10-23T19:15:26Z, both obsolete worktree paths and both exact CoCore cache paths were absent. The cache parent `/Users/tijs/.cache/mei` was empty after removing only its model and runtime/KV contents and was removed. Both branch refs remain at their exact commits; the MiniCPM Kiem plan remains open. Worktree readback shows only the Mei main plus current Flint verification worktree, and local-model-bench main plus the dirty forced-disk-gate worktree. No stale registrations were reported; those current/incomplete worktrees remain untouched.
- The retained local-model-bench Qwen text-only model and provenance sidecar still exist; all 17 canonical files had matched the deleted cache copy by size/SHA-256 before deletion. Both Mei/CoCore LaunchAgents remain unloaded; ports 8024/8017 are free. Primary Mei untracked research files, benchmark configs/results, model payloads, cleanup evidence, and shared SwiftPM/Xcode caches remain untouched.
- Pre-clean `df` at 2026-10-23T19:13:33Z: 24,010,293,248 bytes available. Latest post-clean `df` at 2026-10-23T19:16:07Z: 43,933,892,608 bytes (40.917 GiB). Net filesystem increase: 19,923,599,360 bytes (18.555 GiB). Deleted-tree aggregate `du` was 20,381,138,944 bytes (18.981 GiB); the filesystem delta is reported separately.
- At that latest snapshot, subtracting Flint's exact 17,848,619,410-byte LFS total leaves 26,085,273,198 bytes (24.294 GiB), above the 10 GiB disk floor before any further download/runtime overhead. The current build scratch is retained. No Flint weights are staged and no benchmark has run.
- Cleanup evidence and the Qwen duplicate identity manifest are local/untracked. No commit or push was made.
# Local model-cache retirement — Flint disk recovery

## Authorization and frozen allowlist

Tijs explicitly authorized retiring these two local model payloads:

- DELETE `/Users/tijs/.local/share/local-model-bench/mei-models/MiniCPM-V-4.7-35B-A3B-4bit` — `du -sk`: 22,996,816 KiB (23,548,739,584 bytes). Exact upstream: `mlx-community/MiniCPM-V-4.7-35B-A3B-4bit@0e3b706c1599ad95294122c67c77ce662de18794`.
- DELETE `/Users/tijs/.local/share/local-model-bench/mei-models/gguf/Underdog-Saluki-27B-1.0` — `du -sk`: 7,713,268 KiB (7,898,386,432 bytes). Exact upstream: `ConwayResearch/Underdog-Saluki-27B-1.0@1336c0b5d74dfe6ad7f793577092f5effd9f97c6`.

KEEP: all provenance/evidence, including `MiniCPM-V-4.7-35B-A3B-4bit.provenance.json`; copy and update the Saluki sidecar outside the deleted payload at `/Users/tijs/.local/share/local-model-bench/mei-models/gguf/Underdog-Saluki-27B-1.0.provenance.json`; retain all benchmark configs/results/transcripts and the open Saluki evaluation plan. Also keep the active Qwen3.6 text-only model root, primary Ornith aligned root, and all other model/build/runtime roots. Do not delete branches, configs, historical results, or unrelated data.

## Recoverability and integrity preflight

- MiniCPM pinned Hub model API returned `private:false`, resolved SHA equal to the requested revision `0e3b706c1599ad95294122c67c77ce662de18794`, and the pinned shard sizes/LFS OIDs. The local provenance sidecar's hashes matched all 17 listed files, including all five safetensors shards and tokenizer.
- Saluki pinned tree API returned HTTP 200 at revision `1336c0b5d74dfe6ad7f793577092f5effd9f97c6`; the pinned GGUF is 7,898,369,152 bytes with SHA-256 `4a673518b11b1c4445f9b9a9d3c40356f5ba39f6a6260dcb25f3fbfd475d9efb`. A no-download HEAD request to that pinned file returned HTTP 200, and the local GGUF hash matched the sidecar. The repository's current head differs; the pinned revision remains directly resolvable.
- No local-model-bench YAML config references either exact local payload; the MiniCPM benchmark record is for a separate official GGUF run, not this MLX copy. The local MiniCPM MLX sidecar says loadability was not checked. Saluki has no active benchmark config and its Kiem plan remains “when requested.”
- Both exact target directories resolved to the allowlisted paths, were not symlinks, and `lsof +D` returned exit 1 with empty output for each. No process argv referenced either path. An installed Mei server for Qwen3.6 on port 8024 uses a separate model root and is left untouched.
- Pre-clean inventory at 2026-10-23T15:31:42Z: filesystem `/System/Volumes/Data` had 12,377,192 KiB available (12,674,244,608 bytes; 11.804 GiB). Immediately before the first deletion at 15:33:10Z, `df` reported 12,339,988 KiB. Aggregate target `du` size was 31,447,126,016 bytes (29.287 GiB). APFS `df` change may differ from `du` because of clones/snapshots.

## Post-clean verification

- At 2026-10-23T15:33:24Z, both exact payload directories were absent; their parents remain. The MiniCPM provenance sidecar remains adjacent with `local_directory: null`, `local_directory_original` preserved, `retained: false`, and retirement status. The Saluki sidecar remains at `/Users/tijs/.local/share/local-model-bench/mei-models/gguf/Underdog-Saluki-27B-1.0.provenance.json` with `local_path: null`, original path preserved, and retirement status. Both sidecars parse as JSON.
- Other model roots remain: MiniCPM GGUF benchmark evidence/configs (separate artifact), active Qwen3.6 text-only model under `~/.cache/mei/models`, primary Ornith aligned model, Qwen3.6 full/text-only bench copies, and all remaining models/builds/runtimes. No benchmark configs, `results/log.jsonl`, leaderboards, transcripts, or historical evidence were changed.
- Filesystem `/System/Volumes/Data`: immediately before first deletion, available 12,339,988 KiB; after both deletions, available 43,041,100 KiB (44,074,086,400 bytes / 41.047 GiB). Net `df` increase: 30,701,112 KiB (31,437,938,688 bytes / 29.243 GiB). Per-path `df` increases: 23,549,218,816 bytes (MiniCPM) and 7,898,918,912 bytes (Saluki); their sum exceeds the net by 10,199,040 bytes because `df` dipped between the two deletes. The `du` aggregate was 31,447,126,016 bytes (29.287 GiB); report filesystem and tree measurements separately.
- Against the selected Flint artifact's 17,848,619,410-byte LFS total, the latest free space leaves an optimistic 26,225,466,990 bytes (24.424 GiB), above the ordinary 10 GiB floor; non-LFS/download/build overhead still requires a fresh gate. No Flint weights were staged and no Flint benchmark was run.
- No commit or push was made.
- Later follow-up snapshot at 2026-10-23T15:37:05Z: available space was 42,825,519,104 bytes (39.884 GiB), leaving 24,976,899,694 bytes (23.262 GiB) after the selected artifact's LFS total. This is lower than the immediate post-clean snapshot; remeasure again before staging.
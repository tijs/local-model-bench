# Qwen3.6-35B-A3B scheme-aware MLX quantisation — scheduled recheck, 2026-09-14

Append-only evidence note. This file is a NEW status recheck, separate from the
historical blocker record
`artifacts/qwen36-scheme-aware-conv-blocker-20260914.md` (committed as `2a5e701`,
`artifacts: record scheme-aware Qwen3.6 quantisation branch blocker
(intentionally unexecuted)`). That artifact was NOT edited. This recheck
re-verifies the blocker facts read-only and records the current machine state.

## Status: still blocked; no experiment executed

No model weights were downloaded, no conversion or calibration was run, no
Mei/llama.cpp server was launched, `results/log.jsonl` and
`results/LEADERBOARD.md` were not touched (all append-only results remain
unmodified), `/Users/tijs/projects/mei` was not invoked or mutated, and no Kiem
state was changed. This recheck is purely observational; the branch remains
intentionally unexecuted exactly as the blocker artifact documents.

## Read-only verification commands and exact outputs (2026-09-14)

Repository state:

```
$ git -C /Users/tijs/projects/local-model-bench status
On branch main
Your branch is ahead of 'origin/main' by 20 commits.
  (use "git push" to publish your local commits)
nothing to commit, working tree clean

$ git -C /Users/tijs/projects/local-model-bench rev-parse HEAD
5ee6015ee270e6627fa1990209e1b5755bde15c6

$ git -C /Users/tijs/projects/local-model-bench log --oneline --follow -- artifacts/qwen36-scheme-aware-conv-blocker-20260914.md
2a5e701 artifacts: record scheme-aware Qwen3.6 quantisation branch blocker (intentionally unexecuted)
```

Disk (read-only `df`):

```
$ df -h /System/Volumes/Data
Filesystem      Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s5   460Gi   401Gi    22Gi    95%    2.3M  230M    1%   /System/Volumes/Data

$ df -k /System/Volumes/Data
Filesystem   1024-blocks      Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s5   482797652 419982428  23022276    95% 2257916 230222760    1%   /System/Volumes/Data
```

Available now: 23,022,276 KiB = 21.95 GiB (22 GiB). This is LOWER than the
~31-32 GiB free recorded in the blocker artifact at the same commit date —
headroom has shrunk, not improved. The 65.42 GiB bf16 source still cannot fit,
and the >= 20 GiB remaining floor could not be held even if it did.

Memory (read-only `sysctl`):

```
$ sysctl hw.memsize
hw.memsize: 34359738368        (32.0 GiB)

$ sysctl vm.swapusage
vm.swapusage: total = 2048.00M  used = 1042.00M  free = 1006.00M  (encrypted)
```

32 GiB unified memory is unchanged. A ~66 GiB bf16 model cannot be made
resident for DWQ / dynamic quant calibration on this Mac (second independent
blocker, as recorded).

HF cache and local model/cache roots:

```
$ ls -1 ~/.cache/huggingface/hub | grep -i qwen3.6
models--EigenLabs--Qwen3.6-35B-A3B-MLX-mixed-4bit
models--ggml-org--Qwen3.6-35B-A3B-GGUF
models--mlx-community--Qwen3.6-35B-A3B-4bit
models--mlx-community--Qwen3.6-35B-A3B-4bit-DWQ
models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit

$ find ~/.cache/huggingface -maxdepth 4 -iname '*bf16*'
# only hits: LiquidAI LFM2.5-* -MLX-bf16 lock dirs and an
# mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit tree-metadata filename containing
# the substring "bf16" — NO Qwen3.6 bf16/fp16 source repo or snapshot exists.
```

Conclusion: the five Qwen3.6 entries are all already-quantised artifacts
(EigenLabs mixed-4bit, ggml-org GGUF, mlx-community 4bit / 4bit-DWQ /
OptiQ-4bit). NO Qwen3.6 BF16 (or fp16) source is present in the HF cache or
any local model root scanned at this recheck, so a calibrated conversion would
still require the fresh ~65-67 GiB download. Staged plain-affine lanes are
confirmed present and untouched under `configs/Qwen3.6-35B-A3B*`
(`DWQ/mei.yaml`, `OptiQ/mei.yaml`, `mixed46/mei.yaml`, `textonly/*`,
`Uncensored/gguf.yaml`, base `gguf-*.yaml` + `mei*.yaml`).

No running servers: `ps aux | grep -iE 'llama|mei'` returned no matches.

## Pinned source revision (preserved, unchanged)

`mlx-community/Qwen3.6-35B-A3B-bf16` at revision
`04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` (14 safetensors shards plus
metadata, total 70,241,335,712 bytes = 65.42 GiB). This is the exact pin
recorded in the historical blocker artifact and must be reused verbatim for
provenance on any future run.

## One precise future-machine first command + prerequisites

Prerequisites (checked on the future machine BEFORE running anything):

1. `pip install "mlx-lm[train]"`, then verify `python -c 'import mlx_lm'`
   succeeds (calibrated tools `mlx_lm.dwq` / `mlx_lm.dynamic_quant` /
   `mlx_lm.awq` / `mlx_lm.gptq` are not in the base install and not in the
   locked bench venv on this Mac).
2. `df -h /System/Volumes/Data` proves free space covers source 65.42 GiB +
   output quant dir + calibration scratch, still leaving >= 20 GiB remaining
   (≈ >= 105 GiB free for a 4-bit output).
3. `sysctl hw.memsize` proves enough RAM to make the ~66 GiB bf16 source
   resident for the calibration training loop (32 GiB here is insufficient).
4. Source pinned by 40-hex revision as above (Mei's converter already rejects
   unpinned hub sources).

First command on that machine (documentation only; verified against the tool's
own help at execution time):

```
mlx_lm.dwq --help
```

(each calibrated entry point's full option surface must be pinned from its
own `--help` output before any run; `mlx_lm.dwq --model
mlx-community/Qwen3.6-35B-A3B-bf16@04bbe07c3ed2d93cbf832f523fea344bca1d0fcf
--mlx-path <out> --bits 4 ...` is the shape of the eventual command, per
LEARNED_QUANTS.md, NOT executed here). On THIS Mac the honest probe remains
Mei's wrapper `--dry-run`, which exits 3 (safety refusal) because the disk
requirement cannot be proven safe — that refusal is the expected outcome and
must not be forced.

## Result

Recheck confirms the historical blocker stands unchanged: (a) disk free
dropped to ~22 GiB vs 65.42 GiB source and below the 20 GiB floor, (b) 32 GiB
RAM still cannot host the ~66 GiB bf16 source for calibration, (c) mlx_lm is
absent from the locked bench venv and Mei's converter has no calibrated path.
No experiment was executed. This note is append-only evidence; do not edit it
retroactively. Future status changes belong in new, later-dated files.
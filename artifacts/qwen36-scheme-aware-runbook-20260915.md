# Qwen3.6-35B-A3B scheme-aware MLX quantisation — future-machine runbook, 2026-09-15

Append-only runbook artifact. Complements (does not edit) the historical blocker
record `artifacts/qwen36-scheme-aware-conv-blocker-20260914.md` (committed
`2a5e701`) and the recheck `artifacts/qwen36-scheme-aware-recheck-20260914.md`
(committed `281fe4b`). New value added here and here only: (a) a fail-closed
preflight sequence with stop conditions, (b) the exact first help commands whose
outputs must be captured, (c) the currently-sourced mlx-lm documentation facts
for DWQ / dynamic quant, explicitly labelled as documentation only, and (d) a
staged conversion → staging → gate → benchmark ordering that forbids any
`results/log.jsonl` row or leaderboard change until the candidate passes.

Nothing in this file was executed on this Mac at writing time: no weights
downloaded, no package installed, no conversion or calibration run, no
Mei/llama.cpp server launched, `results/log.jsonl` and `results/LEADERBOARD.md`
untouched, `/Users/tijs/projects/mei` not invoked or mutated, no Kiem state
changed. This runbook is for a future machine that satisfies the preflight.

## Pinned source (preserved exactly, unchanged)

`mlx-community/Qwen3.6-35B-A3B-bf16` at revision
`04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` — 14 safetensors shards plus
metadata, total file bytes 70,241,335,712 (65.42 GiB). Reuse this exact
`<repo>@<40-hex>` form verbatim for provenance on the future run.

## Fail-closed preflight (future machine; any step failing = STOP)

Run in order. Each item is a gate: if it does not pass, stop — do not download,
do not convert, do not write any result row, and record the failed step in a
new dated artifact.

1. **Disk gate** — `df -h /System/Volumes/Data` and `df -k /System/Volumes/Data`
   must prove free space >= source (65.42 GiB) + output quant dir + calibration
   scratch + a remaining floor of >= 20 GiB (≈ >= 105 GiB free for a 4-bit
   output). Below that: STOP (this Mac recorded only ~22 GiB free on
   2026-09-14, far under the floor).
2. **RAM gate** — `sysctl hw.memsize` (and `sysctl vm.swapusage` for context)
   must prove enough memory to make the ~66 GiB bf16 source resident for the
   DWQ / dynamic-quant calibration training loop. 32 GiB (this Mac) is
   insufficient: STOP. The exact workspace requirement beyond residency is
   confirmed from `--help` output, not guessed.
3. **Tooling gate** — `pip install "mlx-lm[train]"`, then verify
   `python -c 'import mlx_lm'` succeeds and the console scripts
   `mlx_lm.dwq` / `mlx_lm.dynamic_quant` resolve (`which mlx_lm.dwq`). The
   calibrated tools are NOT present in the locked bench venv (`uv run --locked
   python -c 'import mlx_lm'` fails with `ModuleNotFoundError` on this Mac) and
   NOT in the base `mlx-lm` install. Any import/entry-point failure: STOP.
4. **Source-revision gate** — before any download, verify (read-only metadata
   query via `huggingface_hub`) that the resolved revision of
   `mlx-community/Qwen3.6-35B-A3B-bf16` is exactly
   `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf`. Any mismatch: STOP. Start the
   download only after gates 1–4 all pass. (No bf16/fp16 Qwen3.6 source exists
   in the HF cache on this Mac — only already-quantised artifacts — so a fresh
   download is unavoidable.)

## First help commands to capture (exact, on the qualifying machine)

Execute these two commands and record their full output verbatim in the run
log / a new evidence artifact BEFORE any conversion:

```
mlx_lm.dwq --help
mlx_lm.dynamic_quant --help
```

The exact option surface for the eventual run is pinned ONLY from these
execution-time outputs (LEARNED_QUANTS.md points at `--help` for the full
list). Never guess flags from documentation or from this file.

## Sourced mlx-lm documentation facts (consulted 2026-09-15; documentation only, NOT execution-time)

From the official mlx-lm web documentation / current source (`main`), quoted
for orientation; do NOT treat as verified flag syntax:

- `LEARNED_QUANTS.md` documents DWQ, AWQ, dynamic quantization, and GPTQ as
  separate calibrated tools (`mlx_lm.dwq`, `mlx_lm.awq`, `mlx_lm.dynamic_quant`,
  `mlx_lm.gptq`); they require `pip install "mlx-lm[train]"` and run calibration
  on the UNQUANTISED source model.
- DWQ defaults shown in current source include: `bits=4`, `group_size=64`,
  `num_samples=2048`, `max_seq_length=1025`, `batch_size=4`; `--grad-checkpoint`
  is available.
- `mlx_lm.dynamic_quant` exposes `target-bpw`, low/high bits and group sizes,
  sensitivities, and `--grad-checkpoint`.

These are sourced defaults only. Capture and pin real values from
`mlx_lm.dwq --help` / `mlx_lm.dynamic_quant --help` at execution time before
any conversion; this file claims no command was run.

## Staged conversion / gate / benchmark order (fail-closed)

1. **Convert (calibrated)** on the qualifying machine, from the pinned bf16
   source only, using flags captured from `--help` (e.g. the DWQ shape
   `--bits 4 --group-size ... --num-samples ...`, or dynamic quant
   `--target-bpw ...`; NOT executed, NOT fixed here). Output to a dedicated
   quant dir with provenance recorded.
2. **Stage with provenance** — bring the artifact into a local model root via
   `/Users/tijs/projects/mei/tools/stage_mlx_checkpoint.py` using
   `--repo mlx-community/Qwen3.6-35B-A3B-bf16 --revision
   04bbe07c3ed2d93cbf832f523fea344bca1d0fcf --target <model-root> --expect-bytes
   <measured>`; verify the staged snapshot bytes match expectations.
3. **Config gate** — a benchmark config under
   `configs/Qwen3.6-35B-A3B-<lane>/` must be written and COMMITTED before any
   run (AGENTS.md invariant: a benchmark config must be committed before a
   run).
4. **Candidate gate** — run the server-side acceptance gate (loadability plus
   native probes, per the repo's existing gate pattern, e.g.
   `artifacts/qwen36-optiq-gate-20260914.md`) and record raw evidence in a new
   dated artifact. Fail-closed: a candidate that fails the gate is NOT ranked
   and the branch stops there.
5. **Benchmark run** — only after the gate passed:
   `uv run --locked python runner/run_bench.py --config
   configs/Qwen3.6-35B-A3B-<lane>/mei.yaml`.
6. **Results append** — during the gate-only phase (before step 4 passes), no
   `results/log.jsonl` row may be written and no leaderboard entry may appear.
   After the candidate gate passes, a real benchmark run may append rows to
   `results/log.jsonl` even if it is interrupted or partially fails; such
   failed/interrupted rows are append-only evidence that must be preserved,
   classified, and never hand-edited or counted as a complete/promoted result.
   Regenerate `results/LEADERBOARD.md` only per the repository's normal
   complete-history policy, after reconciliation.

## Result

Runbook only; no experiment executed, no artifact converted, no results
produced, on this Mac or by this file. Status of the branch remains: blocked on
this Mac (disk ~22 GiB free, 32 GiB RAM, no mlx_lm in the locked env). This
file is append-only; do not edit it retroactively. Future status changes belong
in new, later-dated artifacts.
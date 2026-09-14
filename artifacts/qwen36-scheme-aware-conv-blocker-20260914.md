# Qwen3.6-35B-A3B scheme-aware MLX quantisation branch - blocker record, 2026-09-14

Intentional unexecuted experiment. This file documents an investigation that
was deliberately NOT run on this Mac. No model weights were downloaded, no
conversion or calibration was executed, no quantised artifact was produced, and
no `results/log.jsonl` row or leaderboard change belongs to this branch. It
exists so a future machine can resume the branch from a verified, reproducible
state.

## Investigated alternative

"Scheme-aware" quantisation here means a calibrated MLX quant method from the
mlx-lm Learned Quantisation family (DWQ / AWQ / dynamic quant / GPTQ), which
tunes quantisation parameters on calibration data. The alternative target is a
scheme-aware 4-bit Qwen3.6-35B-A3B alongside the plain affine quantisations
already staged in this repo (`configs/Qwen3.6-35B-A3B-*`: EigenLabs mixed-4bit,
mlx-community OptiQ-4bit / DWQ-4bit lanes).

## Verified blocking facts (as of 2026-09-14)

- Host: macOS 26.5.2, 32.0 GiB unified memory (`hw.memsize` 34359738368), disk
  `df` on /System/Volumes/Data: 460 GiB total, 391 GiB used, ~31 GiB free
  (parent measured ~32 GiB after the Mei v0.5.0 build; both readings sit far
  below the download size and the 20 GiB floor used below).
- Public source candidates are far larger than local headroom:
  - `mlx-community/Qwen3.6-35B-A3B-bf16` at revision
    `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf`: 14 safetensors shards plus
    metadata, total file bytes 70,241,335,712 (65.42 GiB).
  - `Qwen/Qwen3.6-35B-A3B`: 71,926,865,825 bytes (66.99 GiB).
- Cache: only already-quantised Qwen3.6 artifacts exist under
  `~/.cache/huggingface/hub` (EigenLabs `...-MLX-mixed-4bit`, ggml-org GGUF,
  mlx-community `-4bit`, `-4bit-DWQ`, `-OptiQ-4bit`). No bf16/fp16 source is
  cached, so a calibrated conversion would require a fresh ~65-67 GiB download.
- Benchmark env: in local-model-bench, `uv run --locked python -c 'import
  mlx_lm'` fails with `ModuleNotFoundError: No module named 'mlx_lm'`; the
  locked venv does not provide mlx-lm.
- Mei's converter (`/Users/tijs/projects/mei/tools/convert_mlx_quant.py`)
  wraps only `mlx_lm.convert` with `VALID_Q_MODES = ("affine", "mxfp4",
  "nvfp4", "mxfp8")`. It has NO calibrated/scheme-aware path, refuses unpinned
  hub sources (hub `--source` requires `--revision` as a 40-hex pinned commit,
  otherwise exit 2), and enforces a `--min-free-gib` disk floor (exit 3 safety
  refusal when the estimated source + output + free-floor requirement cannot
  be proven safe). `--dry-run` validates without downloading.
- Public mlx-lm docs (github.com/ml-explore/mlx-lm, `main`, consulted
  2026-09-14): `mlx_lm/convert.py` exposes `-q/--quantize` with `--q-mode`
  choices affine/mxfp4/nvfp4/mxfp8 (plus `--quant-predicate` mixed-bit
  recipes); the calibrated methods are NOT in convert.py.
  `mlx_lm/LEARNED_QUANTS.md` documents them as separate tools (`mlx_lm.dwq`,
  `mlx_lm.dynamic_quant`, `mlx_lm.awq`, `mlx_lm.gptq`) that require
  `pip install "mlx-lm[train]"` and run calibration on the UNQUANTISED source
  model. These options were read from the public source; they were not
  exercised locally.

## Safe stop condition

Do NOT download the 65.42 GiB bf16 source on this machine: ~31-32 GiB free
cannot hold it and would fall below the < 20 GiB remaining floor. The branch
stays stopped until a future machine proves, with `df`, that free space covers
source (65.42 GiB) + output quant dir + calibration scratch + a remaining
floor of >= 20 GiB (roughly >= 105 GiB for a 4-bit output), and has enough RAM
to make the ~66 GiB bf16 model resident for calibration. DWQ / dynamic quant
are training loops over the full-precision model; the 32 GiB Mac cannot host
them, which is the second independent blocker.

## Reproducible next command / prerequisites (future machine)

Prerequisites:

1. mlx + mlx-lm with the train extra:
   `pip install "mlx-lm[train]"`, then verify `python -c 'import mlx_lm'`.
2. Disk and RAM satisfy the floor above (verified with `df` and
   `sysctl hw.memsize`).
3. Pinned source revision for provenance:
   `mlx-community/Qwen3.6-35B-A3B-bf16` at
   `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` (65.42 GiB, 14 shards).

First step on that machine (documentation only here): `mlx_lm.dwq --help` /
`mlx_lm.dynamic_quant --help` to enumerate the current option surface at
execution time (LEARNED_QUANTS.md points at `--help` for a full list). On THIS
machine the honest probe is Mei's wrapper dry-run, which exits 3 (safety
refusal) because the disk requirement cannot be proven safe; that refusal is
the expected outcome and must not be forced.

Recorded example (from LEARNED_QUANTS.md, NOT executed):

```
pip install "mlx-lm[train]"
mlx_lm.dwq --model <pinned-bf16-source> --mlx-path <out> \
    --bits 4 --group-size 32 --num-samples 1024 ...
mlx_lm.dynamic_quant --model <pinned-bf16-source> --target-bpw 4.8 ...
```

Exact flags must be pinned from `--help` output at execution time. The
resulting artifact must be staged with `stage_mlx_checkpoint.py` provenance and
gated before any benchmark rows.

## Result

No calibrated quant, no converted artifact, and no quality/benchmark result was
produced by this branch. Status: blocked on this Mac by (a) disk headroom
(~31-32 GiB free vs 65.42 GiB source, below the 20 GiB floor), (b) memory
(32 GiB RAM cannot make the ~66 GiB bf16 source resident for calibration), and
(c) tooling (mlx_lm absent from the locked bench venv; Mei's converter has no
calibrated path). Resume on a machine satisfying the prerequisites above.
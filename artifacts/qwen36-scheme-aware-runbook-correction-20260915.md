# Qwen3.6-35B-A3B — mlx-lm DWQ: source vs documentation default discrepancy, correction note 2026-09-15

Append-only correction/evidence artifact for the Qwen3.6 future-machine
quantisation preparation. Corrects a sourced-defaults claim in
`artifacts/qwen36-scheme-aware-runbook-20260915.md` (2026-09-15 runbook, lines
70-87, specifically lines 79-81). That runbook is append-only — "this file is
append-only; do not edit it retroactively" — and is NOT edited here. No other
repository file, `results/`, `configs/`, runner code/tests, models, caches, or
`/Users/tijs/projects/mei` was touched. This note is evidence/correction only,
NOT a conversion plan: no downloading, installing, converting, serving, or
benchmarking was performed for it.

## 1. The claim being corrected

The runbook's 2026-09-15 "Sourced mlx-lm documentation facts" section states
that current mlx-lm DWQ documentation/source defaults are `num_samples=2048`
and `batch_size=4` (together with `bits=4`, `group_size=64`,
`max_seq_length=1025`, and the availability of `--grad-checkpoint`). Those
values were explicitly labelled "documentation only, NOT execution-time — never
guess flags from documentation" and were never claimed to be verified flag
syntax.

## 2. Pinned official source revision (read-only inspection)

Official mlx-lm `main` was read at commit
`d8f7f88d8a1f730a761a49f59b2d547ce571f431`. Exact URLs:

- Commit: https://github.com/ml-explore/mlx-lm/commit/d8f7f88d8a1f730a761a49f59b2d547ce571f431
- Doc: https://raw.githubusercontent.com/ml-explore/mlx-lm/d8f7f88d8a1f730a761a49f59b2d547ce571f431/mlx_lm/LEARNED_QUANTS.md
- Code: https://raw.githubusercontent.com/ml-explore/mlx-lm/d8f7f88d8a1f730a761a49f59b2d547ce571f431/mlx_lm/quant/dwq.py

Inspection method: web/source inspection — `main` was resolved to
`d8f7f88d8a1f730a761a49f59b2d547ce571f431` via the GitHub API and the two raw
files above were fetched at that revision as plain text. This is NOT
execution-time evidence: no `mlx_lm.dwq` / `mlx_lm.dynamic_quant` process ran
for this note, and the calibrated tools are not installed on this Mac.

## 3. Documented defaults vs executable parser defaults — they disagree

| DWQ default | `mlx_lm/LEARNED_QUANTS.md` @ d8f7f88 (lines 40-42) | `mlx_lm/quant/dwq.py` @ d8f7f88 (lines 271-279) |
| --- | --- | --- |
| samples | documents `--num-samples 1024` | parser default `num_samples=2048` |
| batch size | documents `--batch-size 8` | parser default `batch_size=4` |

At the pinned revision, `LEARNED_QUANTS.md` documents DWQ with
`--num-samples 1024` and `--batch-size 8`, while the executable argument parser
in `quant/dwq.py` at the same revision sets `num_samples=2048` and
`batch_size=4`. Documentation and executable defaults therefore disagree at
this commit (line numbers refer to the raw files fetched at d8f7f88).

## 4. Conclusion

Because the documentation and the executable disagree (and either may change
again), the exact `mlx_lm.dwq --help` output captured on the future qualifying
machine remains the sole authoritative source for the option surface and its
defaults — which is exactly what the runbook already requires ("The exact
option surface for the eventual run is pinned ONLY from these execution-time
outputs"). Documentation values must not be treated as runtime truth.

## 5. Status / result — 2026-09-15

- Preflight on this Mac remains BLOCKED (no gate passed): `/System/Volumes/Data`
  free = 23,460,236 KiB ≈ 22.35 GiB (runbook floor is ≥ ~105 GiB);
  `hw.memsize` = 34,359,738,368 (32 GiB, insufficient for ~66 GiB bf16
  residency); `uv run --locked python -c 'import mlx_lm'` →
  `ModuleNotFoundError`; no local Qwen3.6 BF16/FP16 HF-cache candidate found.
- No experiment ran: no conversion/calibration, no server launched, no
  `results/log.jsonl` row appended, no `results/LEADERBOARD.md` change, no
  publish/push/commit. Models and caches untouched.
- Net effect: the runbook's 2048/4 "sourced defaults" stay unchanged (append-
  only) but are, per section 3, contradicted by its own cited documentation at
  the same revision; both sides remain unverified until execution-time `--help`
  is captured.

## 6. Future action

On the qualifying machine, before any conversion (runbook gates 1-4), run
`mlx_lm.dwq --help` (and `mlx_lm.dynamic_quant --help`), record the output
verbatim in a new dated artifact, and pin the flag surface — including the
actual `--num-samples` / `--batch-size` defaults — from that execution-time
output only. Re-resolve the installed mlx-lm revision and re-read
LEARNED_QUANTS.md / quant/dwq.py at that exact revision as secondary context;
if defaults still disagree at the installed revision, the `--help` output wins.

## Checks

- `git status --porcelain` in this repo shows exactly one change:
  `?? artifacts/qwen36-scheme-aware-runbook-correction-20260915.md` — no other
  file created or modified (runbook, results/log.jsonl, LEADERBOARD.md,
  configs, runner, models, caches, mei all untouched).
- `git diff --check` → exit 0, no whitespace errors; `git diff --stat` →
  no tracked modifications.
- Trailing-whitespace scan of this file (`[[:blank:]]$`) → no matches.
- File left uncommitted for parent review and a narrow commit.
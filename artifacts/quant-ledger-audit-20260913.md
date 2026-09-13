# Quant-ledger audit — 2026-09-13

Precise, reproducible statement of every pass/total count behind the
quantisation conclusions in `results/SUMMARY.md`, derived mechanically from the
append-only `results/log.jsonl`.

## Reproduction

```bash
uv run --locked python runner/quant_ledger_audit.py          # print the ledger
uv run --locked python runner/quant_ledger_audit.py --check   # exit 1 on drift
```

`--check` compares the live derivation against the pins in the script
(`PINNED_GROUPS`, `PINNED_AGGREGATES`) and fails if the ledger changes, so the
summary's numbers cannot silently go stale. The pin is enforced in CI-style by
`runner/tests/test_quant_ledger_audit.py` (run with the repo's standard
`uv run --locked python -m unittest discover -s runner/tests -v`).

Inputs as of this audit:

- `results/log.jsonl` sha256
  `6ba8910488daf07512c470d61f588dbe0fced8abcd602cf01d06d4457464776b`
  (4039 rows; 148 `kiem_mini-testwrite` rows).
- Repo HEAD: `7fb38d3` (configs in this audit are the post-repair live tree).

## Method

Every number is scoped to **suite `kiem_mini`, task `kiem_mini-testwrite`**,
counted over *all* config hashes / runner SHAs / reruns ("all time"). A row
counts as a pass only when its boolean `pass` field is `true` (`harness_error`
rows are still counted — they are model/engine results, not harness defects).

## Per-model ledger (all time)

| model | engine | `kiem_mini-testwrite` |
|---|---|---|
| `mlx-community/Qwen3.6-35B-A3B-4bit` (stock) | mei | **1/14** |
| `Tostibrown/Qwen3.6-35B-A3B-4bit-textonly` (text-only) | mei | **1/10** |
| `EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit` (mixed46) | mei | **1/13** |
| `mlx-community/Qwen3.6-35B-A3B-4bit-DWQ` (DWQ 4/8) | mei | **0/3** |
| `mlx-community/Qwen3.5-9B-8bit` (9B 8-bit) | mei | **0/3** |
| `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit` (Ornith) | mei | **0/40** |
| `ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M` (same weights, GGUF) | llama.cpp | **2/6** |
| `bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0` (same weights, GGUF) | llama.cpp | **3/3** |

Aggregates:

| scope | `kiem_mini-testwrite` |
|---|---|
| every MLX **uniform 4-bit affine g64** Mei model (7-model membership) | **4/69** |
| every Mei row of any quant, all time (incl. mixed-precision legs) | **5/88** |

The seven uniform-4-bit members are: Ornith `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`
(0/40), `orcarouter/Qwen3.8-27B-Uncensored-MLX` (1/2), `mlx-community/gemma-4-26b-a4b-it-4bit`
(0/1), `mlx-community/Qwen3.8-27B-4bit` (1/1), stock Qwen3.6 4-bit (1/14),
text-only Qwen3.6 4-bit (1/10), `mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit`
(0/1) — sum **4/69**.

## Qualifying the summary's aggregate

`SUMMARY.md` line 1029 reads "every MLX model, all time | **4/69**". The value is
correct **only** under the uniform-4-bit scope above. The label was unqualified:
the mixed-precision and 8-bit Mei legs are also MLX/Mei but are deliberately
excluded from 4/69, and their inclusion would change the ledger to 5/88:

- DWQ (mixed 4/8): **0/3**
- EigenLabs mixed46 (mixed 4/6): **1/13**
- Qwen3.5-9B 8-bit (uniform 8-bit): **0/3**

`runner/quant_ledger_audit.py` pins the exact 4/69 membership so the aggregate
can no longer be (mis)read as covering every MLX row.

## Worktree-pin repair (same day)

The 2026-09-13 artifact cleanup removed the Mei worktrees the live Qwen3.6
configs pointed at (`artifacts/qwen36-focused-cleanup-20260913.md`). All twelve
Qwen3.6 Mei configs now build from the canonical `~/projects/mei` checkout with
an explicit `BEFORE RUNNING` commit/`tag` pin whose state equals the deleted
worktree's:

| deleted worktree | canonical ~/projects/mei pin | vmlx pin |
|---|---|---|
| `mei-040` | tag **v0.4.0** (`0c88f0a6`) | `654eb455` |
| `mei-profiles` | branch **feat/model-profiles** (`b3da99f`) | `23551729` |
| `mei-050` | branch **feat/0.5.0-dev** (`bd0a06d`) | `44461ffd` |
| `mei-rc` | branch **research/0.4.2-outofbox-reuse** (`8d2a97d`) | `44461ffd` |
| `mei-bisect` | branch **research/sync-bisect** (`1518e70` == tag v0.5.0) | `44461ffd` |

Every pinned commit resolves in the canonical repo (`git cat-file -t`), and the
vmlx pins were read from each pin's `Package.resolved`. HTTP dry-runs of all
twelve launch commands exit 0 and print the exact `mei isolated launch:` line
without building, binding a port, or launching a server; the DWQ config's
dry-run stops only at its documented staging gap (staged model root released by
the cleanup — re-stage from `source_revision 73c707af4243` before a rerun).
# OptiQ full coding benchmark — 2026-09-14

Full 4-suite coding coverage for `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`
(mei), completing the earlier kiem_mini-only leg (5 rows at runner SHA
`f713b29f`, committed `ac72c83` + audit pin `b5b7f49`). Append-only rows;
nothing historical was rewritten.

## Run provenance

- Config: `configs/Qwen3.6-35B-A3B-OptiQ/mei.yaml`, `config_hash`
  `31a7f0b6a256` (snapshot already committed at `results/configs/31a7f0b6a256.yaml`).
- Runner SHA: `b5b7f49bcb62` (clean tree; HEAD `b5b7f49`).
- Server: isolated Mei on port 8024 via `bench-mei` provider;
  run log `/tmp/qwen36-optiq-full-coding-20260914.log` (`OPTIQ_FULL_CODING_EXIT=0`).
- Window: 2026-09-14T08:51:12Z – 09:40:08Z.

## Result — 14/15 pass (93%), zero harness errors

| suite | result |
|---|---|
| kiem_mini | 4/5 — feature, rename, debug, parse-note pass; **testwrite FAIL** |
| hearth_mini | 3/3 |
| kipclip_mini | 4/4 |
| hearth_full | 3/3 |

The single failure, `kiem_mini-testwrite` (`harness_error: false`), killed 2/3
mutants — one survived (agent's tests missed a bug). Same task also failed on
the earlier kiem_mini-only leg. Classified model behavior, not a harness or
engine defect.

Leaderboard regenerated from 4064 rows: new group
`mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit | mei | 31a7f0b6a256 | b5b7f49bcb62`
(15 rows, 93%, 1 fail) in `results/LEADERBOARD.md`. 15 transcripts under
`results/transcripts/<suite>/<task>/20260914T*Z_mlx-community_Qwen3.6-35B-A3B-OptiQ-4bit.log`.

## Ledger reconciliation (`runner/quant_ledger_audit.py`)

Derived from `results/log.jsonl` (sha256
`704201fb47d2f8f7703625b95da8eaf107da97bc43473cbbc1bb0d9021d2badc`, 4064 rows;
151 `kiem_mini-testwrite` rows):

- `all_mei` **5/90** — vs pinned 5/89. The full-coding run appended exactly one
  new testwrite row (a FAIL), so passes stay at 5, total 89 → 90.
- `mlx_uniform_4bit` **4/69** — unchanged. OptiQ-4bit is a mixed-precision
  scheme with a distinct config, **not** a uniform-4-bit affine g64 member; it
  is not in the seven-model `MLX_UNIFORM_4BIT` membership.
- Per-model pins (`PINNED_GROUPS`) — unchanged; OptiQ-4bit is not a pinned
  per-model group. Its testwrite tally is now 0/2.

Deliberate edit: `PINNED_AGGREGATES["all_mei"]` `(5, 89)` → `(5, 90)`, scope
comment updated. No other pin, row, `SUMMARY.md`, config, or source changed.

## Verification

- `uv run --locked python runner/quant_ledger_audit.py --check` → exit 0.
- `uv run --locked python -m unittest discover -s runner/tests -p 'test_quant_ledger_audit.py' -v` → pass.
- `uv run --locked python -m unittest discover -s runner/tests -v` → pass.
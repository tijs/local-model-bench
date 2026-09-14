# Quant-ledger audit — 2026-09-14 (post-OptiQ run)

Post-run statement of every pass/total count behind the quantisation
conclusions in `results/SUMMARY.md`, derived mechanically from the append-only
`results/log.jsonl` after the OptiQ `kiem_mini` benchmark run. Supersedes
`artifacts/quant-ledger-audit-20260913.md` (preserved unchanged) — the only
deliberate change is the `all_mei` pin re-pinned from 5/88 to 5/89.

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
  `2be1edff29bec9cb8873cb7d98ddb9621b6bc2ded5f19fbf505123aaf2001222`
  (4049 rows; 150 `kiem_mini-testwrite` rows).
- Repo HEAD: `ac72c83` (the committed OptiQ `kiem_mini` benchmark evidence).

## Method

Every number is scoped to **suite `kiem_mini`, task `kiem_mini-testwrite`**,
counted over *all* config hashes / runner SHAs / reruns ("all time"). A row
counts as a pass only when its boolean `pass` field is `true` (`harness_error`
rows are still counted — they are model/engine results, not harness defects).

## Per-model ledger (all time, post-run derived output)

| model | engine | `kiem_mini-testwrite` |
|---|---|---|
| `EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit` | mei | 1/13 |
| `HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M` | llama.cpp | 3/5 (1 harness_error) |
| `JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M` | llama.cpp | 3/3 |
| `JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M` | llama.cpp | 2/3 |
| `LiquidAI/LFM2.5-2.6B-GGUF:BF16` | llama.cpp | 0/1 |
| `LiquidAI/LFM2.5-2.6B-GGUF:Q8_0` | llama.cpp | 0/1 |
| `LiquidAI/LFM2.5-8B-A1B-GGUF:BF16` | llama.cpp | 0/1 |
| `LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0` | llama.cpp | 0/2 |
| `Tostibrown/Qwen3.6-35B-A3B-4bit-textonly` | mei | 1/10 |
| `anthropic/claude-haiku-4.5` | openrouter | 1/1 |
| `bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M` | llama.cpp | 1/4 |
| `bartowski/Qwen3.8-27B-GGUF:Q4_K_M` | llama.cpp | 3/3 |
| `bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0` | llama.cpp | 3/3 |
| `empero-ai/Qwen3.8-27B-Ridge-GGUF` | llama.cpp | 1/1 |
| `ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M` | llama.cpp | 0/1 |
| `mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit` | mei | 0/1 |
| `mlx-community/Qwen3.5-9B-8bit` | mei | 0/3 |
| `mlx-community/Qwen3.6-35B-A3B-4bit` | mei | 1/14 |
| `mlx-community/Qwen3.6-35B-A3B-4bit-DWQ` | mei | 0/3 |
| `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit` **(new 2026-09-14)** | mei | **0/1** |
| `mlx-community/Qwen3.8-27B-4bit` | mei | 1/1 |
| `mlx-community/gemma-4-26b-a4b-it-4bit` | mei | 0/1 |
| `mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact` | llama.cpp | 1/4 (1 harness_error) |
| `mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality` | llama.cpp | 0/1 |
| `mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact` | llama.cpp | 0/1 |
| `mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality` | llama.cpp | 0/1 |
| `openai/gpt-5.6-luna` | openrouter | 1/1 |
| `orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit)` | mei | 1/2 |
| `ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M` | llama.cpp | 2/6 |
| `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit` | mei | 0/40 (2 harness_error) |
| `poolside/Laguna-XS-2.1-GGUF:Q4_K_M` | llama.cpp | 1/2 |
| `trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M` | llama.cpp | 0/3 |
| `unsloth/Devstral-Small-2507-GGUF:Q4_K_M` | llama.cpp | 2/3 |
| `unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M` | llama.cpp | 2/3 |
| `unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL` | llama.cpp | 1/1 |
| `unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M` | llama.cpp | 3/6 |

Aggregates:

| scope | `kiem_mini-testwrite` |
|---|---|
| every MLX **uniform 4-bit affine g64** Mei model (7-model membership) | **4/69** (unchanged) |
| every Mei row of any quant, all time (incl. mixed-precision legs) | **5/89** (re-pinned from 5/88) |

## The OptiQ run (2026-09-14)

The OptiQ `kiem_mini` run (`configs/Qwen3.6-35B-A3B-OptiQ/mei.yaml`, config hash
`31a7f0b6a256`, runner SHA `f713b29f`) appended 5 rows to the ledger — the
model's full task suite: `kiem_mini-feature` (fail), `kiem_mini-rename` (pass),
`kiem_mini-debug` (pass), `kiem_mini-parse-note` (pass), and
`kiem_mini-testwrite` (fail). Run-level: **3/5 passes, 0 harness errors**.

Only the testwrite row lands in this audit's scope: `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`
is **0/1** (a fail with `harness_error: false`). That single row moves the
`all_mei` aggregate from 5/88 to 5/89 while passes stay at 5.

OptiQ-4bit is a distinct quantisation scheme, **not** a uniform-4-bit affine g64
member: it is not in the seven-model `MLX_UNIFORM_4BIT` membership, so
`mlx_uniform_4bit` stays **4/69** and no pinned group changed.

## Deliberate pin update

- `runner/quant_ledger_audit.py` `PINNED_AGGREGATES["all_mei"]`: `(5, 88)` →
  `(5, 89)` (comment and scope-header date updated to 2026-09-14).
- No other pin, result row, `SUMMARY.md`, `LEADERBOARD.md`, config, or source
  changed; `artifacts/quant-ledger-audit-20260913.md` preserved verbatim.
- `--check` passes (exit 0) after the re-pin.
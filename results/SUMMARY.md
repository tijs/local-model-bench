# Summary: choosing a model for Mei

**Historical application-runtime results.** Hermes is retired. These saved
campaigns are not Peixinho app validation; current native-model checks are in
[MODEL_ONLY.md](MODEL_ONLY.md).

**Choose Qwen3.6-35B-A3B 4-bit text-only for text/agentic coding with Mei.**
`Tostibrown/Qwen3.6-35B-A3B-4bit-textonly` is the **best measured Mei option**,
based on the latest full **Mei 0.6.1 campaign (2026-09-27)**.
As of 2026-10-20, **no full Mei benchmark has been rerun on current Mei 0.9.0**;
these saved 0.6.1 results are not a validation of 0.9.0.

## Why Qwen, rather than Ornith MLX?

Both completed **25 task rows, with 24/25 passes, 14/15 coding, 8/8 Hermes Ops
and zero harness errors**. Both failed only `kiem_mini-testwrite` (2/3 mutants
killed). Quality is tied in this single-trial campaign.

| Mei 0.6.1 model | Normalized composite | Decode tok/s | Avg coding turns | Avg TTFT (s) | Approx. total run (s) |
|---|---:|---:|---:|---:|---:|
| Qwen3.6 35B-A3B 4-bit text-only | 0.799 | 51.8 | 7.9 | 35.20 | 3,492 |
| Ornith 1.5 35B-A3B MLX 4-bit | 0.734 | 42.6 | 10.8 | 33.97 | 2,352 |

Qwen has the better normalized composite, faster decode and fewer coding
turns. **Ornith MLX had lower TTFT and a shorter total run time** — Qwen is
not universally faster. Scores use the generated leaderboard's cross-engine
normalization; decode and TTFT are sanity + Hermes Ops averages, not coding
throughput. Total run time is displayed, not scored.

## Scope and next candidate

Cross-engine context: MiniCPM-V 4.7 Q4_K_M is **#2 overall (0.835), llama.cpp only**, not a Mei result; see the generated [leaderboard](LEADERBOARD.md#best-overall-gate-then-weighted-composite-score).

**There is no image/vision suite and no image-based model recommendation.**
The recommended Qwen text-only build cannot serve images; MiniCPM's llama.cpp
run used `--no-mmproj` and does not establish visual ability.

MiniCPM needs native Mei support and a comparable Mei run before it can
challenge this pick: Kiem `proj/mei`, plan `1659c325-9310-4796-a531-1d842c0fb354`.

## Evidence

- [Full Mei 0.6.1 campaign and caveats](HISTORY.md#2026-09-27-mei-061-three-contender-campaign--ornith-and-qwen36-text-only-at-2425-qwen38-speed-gated).
- Exact configs: [Qwen text-only `46f751ca4515`](configs/46f751ca4515.yaml)
  and [Ornith MLX `18466a4917a8`](configs/18466a4917a8.yaml); Mei source
  `ae7b3b4e` (v0.6.1), vmlx `fef563a5`.
- [`log.jsonl`](log.jsonl) and [`transcripts/`](transcripts/) — raw task evidence;
  [`HISTORY.md`](HISTORY.md) — release campaigns and the archived Mei working log.

## Historical ledger reconciliation — 2026-10-25

Hermes is retired; the recommendations above describe historical campaigns,
not Peixinho application validation. Current native model-only results are
reported separately in [MODEL_ONLY.md](MODEL_ONLY.md).

The all-time `kiem_mini-testwrite` audit was stale relative to six existing
failed historical rows: stock Qwen +1, text-only Qwen +3 and Ornith +2. Recomputed
from unchanged append-only records, the uniform 4-bit scope is **4/75** and
all Mei quants **5/97**. The old 4/69 and 5/91 pins described the earlier scope;
this reconciliation adds no task attempts and changes no historical rows.

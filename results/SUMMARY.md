# Summary

**As of 2026-10-20.** Hand-curated interpretation of saved benchmark evidence;
[`LEADERBOARD.md`](LEADERBOARD.md#best-overall-gate-then-weighted-composite-score)
is the generated source for scores, gates and the full ranking. This is not
a working log or an implementation plan.

## Current front-runners

| rank | model / quant | engine | score | coding | Hermes Ops |
|---|---|---|---:|---:|---:|
| 1 | ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 0.845 | 13/15 | 8/8 |
| 2 | openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M | llama.cpp | 0.835 | 13/15 | 7/8 |

**Current #2: MiniCPM-V 4.7.** A serious contender, not the winner: Ornith
remains #1. These are results for the current text/tool/coding suite, not
proof of visual capability or a general engine winner.

## MiniCPM: benchmark scope and failures

Completed **2026-10-19**, config `cc13a6f07dcf`: **25/25 task rows**, **22/25
passes** (sanity 2/2, Hermes Ops 7/8, coding 13/15), **zero harness errors**.
The generated row reports **37.3 tok/s decode**, **6.45 s average TTFT** and
**1,584 s total runtime**.

**No image/vision tasks exist in the current benchmark.** This run used
`--no-mmproj`; projector, image and video behavior remain untested.

The three task/model failures, not infrastructure failures:

- `hermes_ops-multi-step-chain`: hit the 40-turn limit without a final answer.
- `kiem_mini-testwrite`: killed 2/3 mutants; one survived.
- `kipclip_mini-testwrite`: generated TypeScript failed type-checking (22 errors).

## Next meaningful direction

Establish native MiniCPM-V 4.7 support and correctness in Mei before
optimization or a comparable scored run. Active steps, blockers and acceptance
gates live in Kiem, not here:

- `proj/mei`, plan `1659c325-9310-4796-a531-1d842c0fb354`.
- `proj/local_model_bench`, benchmark record `0636081f-5fd5-4972-8e57-25271f9217e2`.

Vision needs a separately defined and verified task suite; this text result
is not vision evidence.

## Where the detail lives

- [`LEADERBOARD.md`](LEADERBOARD.md) — generated full ranking, scoring and gates;
  never hand-edit it.
- [`log.jsonl`](log.jsonl), [`configs/`](configs/) and
  [`transcripts/`](transcripts/) — raw task rows, exact run-config snapshots and
  coding transcripts; [`../configs/`](../configs/) holds launch configurations.
- [`HISTORY.md`](HISTORY.md) — release campaigns and superseded comparisons,
  including the [archived September Mei working log](HISTORY.md#archived-mei-optimization-working-log-2026-09-09-to-2026-09-17).
- [`INFERENCE_ENGINES.md`](../docs/INFERENCE_ENGINES.md) — engine technical research;
  [`OMLX_MODEL_MATRIX.md`](../docs/OMLX_MODEL_MATRIX.md) is retired oMLX research only.

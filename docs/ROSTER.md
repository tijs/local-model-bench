# Four retained contenders — 2 November 2026

Retain **base Qwen3.6 / Mei**, **Ornith1.5 / Mei**, **Groot / Mei** and
**Logics-SWE / llama.cpp** by user direction. The prior two-model shortlist was
premature: Qwen/Ornith had not received the same current repeated comparison.

[Fresh eight-run plan](FOUR_MODEL_COMPARISON.md) ·
[Main summary and graphs](../results/AGENT_SUMMARY.md) ·
[Machine-readable roster](../configs/active_roster.json)

All four will run fresh on frozen v9.9, seeds 17/29, with no prior Groot/Logics
result substituted for a retest. The final summary will show quality/time/memory
tradeoffs with engine labels, both observations and explicit profile caveats.
No ordering or new score is inferred before the measurements finish.

ThinkingCap and MiniCPM remain alternatives. Clover remains experimental native
Kapitsa/Metal diffusion, not a Mei implementation. Flint/JANGH2 remains user-
retired. No historical evidence or staged weights are deleted by this decision.
The [v9.8.1 roster](https://github.com/tijs/local-model-bench/blob/benchmark-v9.8.1/docs/ROSTER.md)
remains available as historical context, not the current selection.

This is a manual roster, not an automatic runner selector. Never use `--all` to
select it: that discovers historical configs too. Use the committed explicit
fresh profile and normal one-server/resource/evidence rules.

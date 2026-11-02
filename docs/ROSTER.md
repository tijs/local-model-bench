# Four retained contenders — 2 November 2026

Retain **base Qwen3.6 / Mei**, **Ornith1.5 / Mei**, **Groot / Mei** and
**Logics-SWE / llama.cpp** by user direction. The prior two-model shortlist was
premature: Qwen/Ornith had not received the same current repeated comparison.

[Fresh eight-run plan](FOUR_MODEL_COMPARISON.md) ·
[Main summary and graphs](../results/AGENT_SUMMARY.md) ·
[Machine-readable roster](../configs/active_roster.json)

All four completed fresh full runs on frozen v9.10, seeds 17/29. No older
Groot/Logics result was substituted. Household scores were Qwen 9/11,
Ornith 9/11, Groot 11/10 and Logics-SWE 11/11, each out of 12. Python scores
were Qwen 2/2, Ornith 3/1, Groot 3/3 and Logics-SWE 3/3, each out of 3.
All four remain contenders. Groot used the least observed wired-memory increase;
Logics-SWE had the highest household total in these two trajectories. These
observations do not establish a universal replacement or statistical superiority.

ThinkingCap and MiniCPM remain alternatives. Clover remains experimental native
Kapitsa/Metal diffusion, not a Mei implementation. Flint/JANGH2 remains user-
retired. No historical evidence or staged weights are deleted by this decision.
The [v9.8.1 roster](https://github.com/tijs/local-model-bench/blob/benchmark-v9.8.1/docs/ROSTER.md)
remains available as historical context, not the current selection.

This is a manual roster, not an automatic runner selector. Never use `--all` to
select it: that discovers historical configs too. Use the committed explicit
fresh profile and normal one-server/resource/evidence rules.

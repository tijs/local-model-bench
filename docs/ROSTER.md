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

MiniCPM and ThinkingCap remain tested alternatives, with these latest completed
profiles in the [historical v9.5 report](../results/AGENT_V9.md):

| Model / engine | Household | Python | Full time | Coverage |
|---|---:|---:|---:|---|
| MiniCPM-V4.7 Q4_K_M / llama.cpp, CPU8/q8 KV, no repacking, two checkpoints | 11/12 | 3/3 | 9m38s | One trajectory; no v9.10 repeats |
| ThinkingCap Q4_K_M / llama.cpp | 11/12 | 3/3 | 8m47s | One trajectory; no v9.10 repeats |

They were left out when the repeated comparison narrowed to four models; neither
was retired. A fresh run on the same frozen method and declared repeat plan is
required before either joins the current averaged graphs. Historical scores
are preserved separately and are not evidence of how they compare on v9.10.

MiniCPM is explicitly queued for two fresh same-method runs and paired short/long
context speed measurements after Mei stable. It will rejoin the current averages
and graphs once that evidence is complete. The follow-up is tracked in the
[stable-release and comparison plan](kiem://note/e48c7c4e-eb1a-4989-be5f-10e2047be86e).

Clover remains experimental native
Kapitsa/Metal diffusion, not a Mei implementation. Flint/JANGH2 remains user-
retired. No historical evidence or staged weights are deleted by this decision.
The [v9.8.1 roster](https://github.com/tijs/local-model-bench/blob/benchmark-v9.8.1/docs/ROSTER.md)
remains available as historical context, not the current selection.

This is a manual roster, not an automatic runner selector. Never use `--all` to
select it: that discovers historical configs too. Use the committed explicit
fresh profile and normal one-server/resource/evidence rules.

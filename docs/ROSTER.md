# Four retained contenders

Retain **base Qwen3.6**, **Ornith1.5** and **Groot** on Mei 0.11.0, and
**Logics-SWE** on its pinned llama.cpp build. All four completed both
declared seeds on frozen benchmark-v9.11.5. This is a serving-profile
comparison; the weights, sampler settings and engines differ.

[Current scores and audits](../results/FOUR_MODEL_MEI011_FINAL.md) ·
[Changes since Mei 0.10.0](../results/MEI011_DELTA.md) ·
[Machine-readable roster](../configs/active_roster.json)

Groot and Logics-SWE passed 22/24 household and 6/6 Python tasks each. Groot
had the smallest weights and the lowest observed wired-memory increase. Qwen
had the shortest mean task time and passed 18/24 household and 6/6 Python;
Ornith passed 19/24 household and 4/6 Python. Two seeds do not establish a
universal winner or actual Peixinho acceptance.

[ToolSpace IQ4_XS and Gemma RAM13GB](../results/QUEUED_CHALLENGERS_FINAL.md)
completed both seeds on the same frozen method. Gemma matched the best
household score but had fewer Python passes and longer task times than Groot
or Logics-SWE. ToolSpace matched Qwen's household score with fewer Python
passes and longer task times. Both are tested alternatives.

MiniCPM remains a tested alternative. Its [earlier two-seed result](../results/MINICPM_MEI010.md)
passed 23/24 household and 5/6 Python, with a critical safety failure. It is
unranked and was not rerun in this cohort. ThinkingCap remains in the
[historical v9.5 report](../results/AGENT_V9.md).

Clover remains experimental native
Kapitsa/Metal diffusion, not a Mei implementation. Flint/JANGH2 remains user-
retired. No historical evidence or staged weights are deleted by this decision.
The [v9.8.1 roster](https://github.com/tijs/local-model-bench/blob/benchmark-v9.8.1/docs/ROSTER.md)
remains available as historical context, not the current selection.

This is a manual roster, not an automatic runner selector. Never use `--all` to
select it: that discovers historical configs too. Use the committed explicit
fresh profile and normal one-server/resource/evidence rules.

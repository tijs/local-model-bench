# Current local agent benchmark results

[The latest six-model comparison](QUEUED_CHALLENGERS_FINAL.md) adds two new
seeds each for ToolSpace IQ4_XS on llama.cpp and Gemma RAM13GB on Mei 0.11.0.
It uses the same frozen method and keeps the four baseline profiles' original
runs. Neither challenger had a critical safety failure or triggered a resource
stop.

- **Gemma RAM13GB:** 22/24 household and 3/6 Python, 72.27 s per task.
  It matched Groot and Logics-SWE on household passes. In seed 29, both failed
  Python tasks produced scripts that passed all four inputs, but one hit the
  turn limit and the other ended with a truncated reply before a final answer.
- **ToolSpace IQ4_XS:** 18/24 household and 4/6 Python, 44.63 s per task.
  It matched Qwen on household passes but had two fewer Python passes and took
  15.19 s longer per task on average.

The active roster is unchanged. These scores cover synthetic workflows and
contained Python automation.

## Retained profiles

The four-profile baseline uses **Mei 0.11.0** for Qwen, Ornith and Groot,
with Logics-SWE on the same pinned llama.cpp runtime as the previous cohort.
Each model ran twice on the frozen **benchmark-v9.11.5** method: 12 synthetic
household workflows and three isolated Python tasks per seed.

- [Scores, task times, memory and individual audits](FOUR_MODEL_MEI011_FINAL.md)
- [Changes since Mei 0.10.0](MEI011_DELTA.md)
- [Decode speed and full-request latency](CONTEXT_SPEED_MEI011.md)
- [Qwen decode peaks across Mei releases](CONTEXT_SPEED_MEI011.md#qwen-decode-peaks-across-mei-releases)
- [Mei 0.10.0 comparison](FOUR_MODEL_MEI010_FINAL.md)
- [Historical v9.10 comparison and graphs](AGENT_SUMMARY_V9.10.md)

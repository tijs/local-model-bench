# Matched serving-profile qualification review

All 12 completed predeclared cells pass observable greedy parity, post-run
model integrity and owned cleanup. Each source/model/context retains ten
measured responses across two fresh processes (five each). Three normal-budget
Swift HTTP clients pass 27/27 tests. The earlier stopped Qwen A1 is preserved
separately and contributes no measured timing pair. This is not a scored
benchmark or completed stable qualification.

| Model | Context | Control mean TPS | Candidate mean TPS | Candidate change |
|---|---:|---:|---:|---:|
| groot | 17 tokens | 56.56 | 56.96 | +0.7% |
| groot | 30,000 tokens | 43.17 | 43.44 | +0.6% |
| qwen | 17 tokens | 66.21 | 42.90 | -35.2% |
| qwen | 30,000 tokens | 45.80 | 39.32 | -14.1% |
| ornith | 17 tokens | 64.43 | 56.01 | -13.1% |
| ornith | 30,000 tokens | 46.38 | 43.04 | -7.2% |

Means give both processes equal weight; all five measurements in each process
count equally. Do not treat ten within-process repeats as ten independent
processes. Original production binaries, identical Metal/weights/settings,
compilation enabled, 512 MiB allocator/prefix limits and 128 greedy output
tokens were used. This tested allowance is not a promoted production default.

Qwen candidate process medians are 43.33/43.91 short and 39.16/39.64 long,
versus controls 66.74/65.97 short and 45.99/44.90 long. This material deficit
prevents a generalized speed claim or unreviewed promotion. Ornith candidate
process medians split widely (42.78/69.78 short; 35.45/49.89 long), whereas
both controls are stable near 64.5/46.4. Groot is approximately neutral. The
full evidence must be reviewed before deciding whether the patch, artifact,
allocator history or host execution explains the difference. No cause is
proved by the CPU flag-lookup microbenchmark alone.

The fresh Qwen/Ornith continuation completed after authorized normal Safari
and Mail quits, with swap flat at 1572.5 MiB. Ornith B2 has one isolated
warning-pressure sample followed immediately by normal pressure, which the
unchanged capacity policy permits. There was no sustained warning or critical
pressure stop. All 168 model-file checks matched; 9,526,083,333 owned KV bytes
were preserved/inventoried then removed after each server exited.

Full native tools/history/cache/exact-65,536 gates, performance review, stable
publication/Homebrew verification and eight new scored front-runner runs remain
open. No historical task scores or figures were rewritten.

The requested summary will use one pair of averaged short/long TPS points per
model joined by a line, with actual token counts, runtime identity and repetition
counts. Task traces from the current v9.10 cohort cannot supply a matched long
context: Qwen tops out near 4.3K tokens. Controlled observations are required
for all four profiles, including pinned Logics/llama.cpp. Qualification-only
candidate measurements must not be mixed with published rc.2 task scores.

# Leaderboard

Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not
hand-edit rows below, edit the log and regenerate instead.

> **⚠ 138/2823 rows below predate 2026-08-21
> grading fixes** (no `runner_git_sha` — that field didn't exist yet).
> **Do not treat any pre-2026-08-21 PASS/FAIL as final signal** until
> re-run under current grading. Known-affected checks: `kiem_mini-feature`
> (used to grade only the library function, never the CLI wiring),
> `hermes_ops-error-recovery` (used to reward fabricated file contents if
> an unrelated word like "error" appeared anywhere), `hermes_ops-selection`
> (used to match "18" as a substring of any number, including "2018"),
> `hermes_ops-chaining` (used to accept extra content beyond the requested
> single number), and `sanity-tool` (used multiset argument matching,
> which could pass wrong argument names). Re-running is the only way to
> get current, trustworthy rows for these tasks.

Grouped by (model, inference_engine, quant, config_hash, runner_git_sha) — never
averaged across different configs OR different harness/grading code
versions, even for the same model+inference_engine, since either would mix
genuinely different experiments (e.g. before/after a settings fix, or
before/after a grading-bug fix). `config_hash` links to a verbatim
snapshot of the exact config content used (`results/configs/`), not the
live (possibly since-edited) config file — see `config_hash` values
flagged "config since changed" for rows predating that snapshot.
`runner_git_sha` rows marked `+dirty` were graded by uncommitted code.

**`avg tok/s` is DECODE-ONLY** (changed 2026-09-09):
`completion_tokens / (wall_seconds - ttft_seconds)`, i.e. throughput once
generation has actually started. It used to be `completion_tokens /
wall_seconds`, which on this suite's large repeated system prompt is
mostly prefill: measured 2026-09-09, TTFT was 74-78% of wall on
`hermes_ops`, and turning on prefix caching moved the reported number
from 10.7 to 27.4 on the SAME model and build while real decode was
unchanged. That figure was feeding the composite score's speed axis, so
the ranking was partly measuring cache state rather than the model.

`avg TTFT` is the other half and is now SCORED in its own right, not
just displayed — it is what interactive use feels like. Both are averaged
across `sanity` (tiny prompt) and `hermes_ops` (large prompt) rows, so
read them as a blend of two prompt shapes, and both are blanked for
proxied configs rather than silently mislabeled: `bench_local_proxy`
buffers the whole response into one chunk, making its TTFT equal to total
generation time. Rows predating TTFT capture are excluded from both.

**Total runtime is displayed but NOT scored** (changed 2026-09-09): it is
an aggregate of decode speed, prefill and turn count, all three already
scored, so scoring it too double-weighted prefill. It stays in the table
because a model can post a good total while looking slow on the
component numbers.

**¹ `temp (coding only)`**: the config's declared temperature is what the
coding suite (`hermes chat`, driven by `run_fixture_suite.py`) actually
runs at, since it respects the server's launch flags. `sanity`/`hermes_ops`
(driven by `run_prompt.py`) deliberately hardcode `temperature=0` for EVERY
model, always, regardless of this config value — a longstanding, documented
design choice (see `tasks/SCHEMA.md` "Temperature is deliberately fixed
at 0"), not a bug.
Note also: `configs/Qwen3.8-27B-Ridge/gguf.yaml` is the only config that
sets `--presence-penalty` (1.5) — a third confound alongside temp/
reasoning-mode when comparing it against `configs/Qwen3.8-27B/gguf.yaml`,
not currently its own column since no other config sets this flag.

**² `slow passes`**: count of PASS rows
that took longer than `bench_common.py`'s `INTERACTIVE_BUDGET_SECONDS`
(300s) to complete — still correct, and still counted in `pass rate`
above, but not a practically usable result in a real interactive agentic
session. Deliberately separate from `timeout_seconds`/`--timeout`, which
exist to give a slow-but-alive model a fair chance to finish generating
without being cut off mid-response — a task can legitimately take up to
that much generous budget and still show up here if it's well past what
an interactive session would tolerate. 300s is a judgment call (see that
constant's own comment), not a hard spec.

**³ `avg coding turns` / `coding tool errors`**: pulled from hermes's own
SQLite session store (`hermes sessions export`) after each coding-suite
task; blank/0 for sanity/hermes_ops-only groups, which call the raw API
directly and have no hermes session to pull from. `coding tool errors` is
a best-effort heuristic (documented in
`run_fixture_suite.py`'s `extract_hermes_session_stats()`), not a fully
generic classifier — confirmed live that a tool's own `exit_code` can
read 0 even when its output clearly shows a build failure, so this also
scans for the same compiler-error markers `grade_mutation.sh` already
looks for as a fallback.

**⁴ `sanity gate` / `pass rate`**: `sanity`
is a fail-fast GATE — run_bench.py stops the whole config entirely if
sanity-basic fails — not a quality signal to blend in alongside real
tool-use/coding results. It's shown here as its own `passed/total` column
instead. `pass rate` now covers only `hermes_ops` + coding-suite rows;
folding sanity in used to compress real differences between models,
since it sits at or near ceiling for nearly everything.

**⁵ `hallucinated tools`**: this only
fires in the two synthetic prompt suites (sanity/hermes_ops), whose fixed
tool manifest makes "called a tool that doesn't exist in it" a clean,
checkable signal. The coding suite has no equivalent check — a hermes
chat session's real tool manifest isn't fixed/known the way hermes_ops's
41-tool mock manifest is, so this reads 0 for every coding-suite row
regardless of what actually happened. Read this column as "not observed
on the two synthetic suites," not "never hallucinated a tool".

**⁶ `reasoning effort`**: added 2026-08-27 (reasoning is a large part of
a thinking-mode model's output, so it needs to be as visible as quant or
temperature). `n/a` means the config has no tunable effort level (a
non-thinking model, or a thinking model whose template doesn't expose
one) -- not the same as `?`, which means the lookup itself failed (see
`_fairness_fields()`'s own comment). A blank-looking value here can
still be a real, active setting: e.g. the Qwen3.8-27B/Qwen3.6-35B-A3B
family's own chat_template.jinja silently defaults to `medium` whenever
no `--reasoning-effort` flag is passed, which every GGUF config for
that family does -- read `n/a`/missing here as "not yet labeled," not
"no reasoning was used." Configs for this family have had this field
added explicitly to record that default rather than leave it invisible.

**⁷ `total runtime (s)`**: approximate total elapsed benchmark run
time for that group, RECOVERED from its own saved rows -- not an exact
process-measured duration. Each row's ISO-8601 `timestamp` is that task's
COMPLETION time; estimated start = first row's timestamp minus that row's
`wall_seconds` (when present). End = last row's timestamp. The span
therefore includes the gaps BETWEEN tasks but excludes server
startup/teardown that happened outside the first/last recorded task. `—`
means no usable timestamp was recoverable from that group's rows.

| model | engine | quant | temp (coding only)¹ | reasoning | reasoning effort⁶ | sanity gate⁴ | config | runner | tasks | pass rate⁴ | slow passes² | avg tok/s | avg TTFT (s) | hallucinated tools⁵ | avg coding turns³ | coding tool errors³ | peak RSS (GB) | quant family | cache | MTP | total runtime (s)⁷ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AtomicChat/Laguna-XS-2.1-MLX-5bit | mei | — | 1.0 | thinking | n/a | 2/2 | [d65c8f880447](configs/d65c8f880447.yaml) — *config since changed* | 3e8f2dbb5101+dirty | 8 | 25% | 0 | 19.0 | 68.39 | 0 | — | 0 | 1.2 | MLX 5-bit affine g64 with 8-bit router gates (per staged config.json quantization/quantization_config) | — | — | 871 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | 5fc289161e34 | 8 | 75% | 0 | 43.9 | 7.05 | 0 | — | 0 | 23.1 | — | — | — | 342 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | 6bb085a043fe | 19 | 84% | 3 | 43.8 | 7.05 | 0 | 15.8 | 30 | 23.6 | — | — | — | 2272 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | — | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | 8e7b1897f7e8+dirty | 11 | 91% | 1 | — | — | 0 | — | 0 | 23.8 | — | — | — | 2309 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | — | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | d39c9c37bb8c+dirty | 0 | n/a (all harness errors) | 0 | — | — | 0 | — | 0 | — | — | — | — | 2734 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | d60debfa3654 | 1 | 100% | 0 | 60.2 | 17.32 | 0 | — | 0 | 21.6 | — | — | — | 57 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | — | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) — *config since changed* | d60debfa3654+dirty | 18 | 89% | 1 | 38.8 | 2.66 | 0 | 14.6 | 18 | 23.1 | — | — | — | 2193 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [98fbff8ca864](configs/98fbff8ca864.yaml) — *config since changed* | 0adb046c1c3e+dirty | 23 | 83% | 2 | 43.4 | 7.05 | 0 | 15.7 | 29 | 24.2 | — | — | — | 2767 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [32924ffd3dd9](configs/32924ffd3dd9.yaml) | 18b93c687e8d+dirty | 7 | 100% | 6 | — | — | 0 | 11.6 | 9 | 22.7 | — | — | — | 5139 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [32924ffd3dd9](configs/32924ffd3dd9.yaml) | 7336e84ce111 | 11 | 82% | 6 | 13.9 | 44.52 | 0 | 18.0 | 6 | 22.2 | — | — | — | 8420 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [3a740261a79c](configs/3a740261a79c.yaml) — *config since changed* | 2477ca2ba371 | 19 | 79% | 11 | 13.9 | 44.53 | 0 | 11.9 | 14 | 22.6 | — | — | — | 13281 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [3a740261a79c](configs/3a740261a79c.yaml) — *config since changed* | a04f5cd07f20 | 19 | 84% | 13 | 13.9 | 44.53 | 0 | — | 0 | 22.6 | — | — | — | 13196 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [7103a8c7677c](configs/7103a8c7677c.yaml) — *config since changed* | ba9bffb50e12+dirty | 19 | 74% | 10 | 9.8 | 46.45 | 0 | 11.6 | 9 | 23.9 | — | — | — | 15748 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [b03fc3f2b8f8](configs/b03fc3f2b8f8.yaml) — *config since changed* | 1dbc371640ce | 19 | 79% | 12 | 9.8 | 46.42 | 0 | 13.5 | 15 | 24.0 | — | — | — | 17552 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [b03fc3f2b8f8](configs/b03fc3f2b8f8.yaml) — *config since changed* | 24ac4057b970 | 5 | 80% | 4 | — | — | 0 | 9.6 | 1 | 24.2 | — | — | — | 3864 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [b03fc3f2b8f8](configs/b03fc3f2b8f8.yaml) — *config since changed* | 9df216e99cd9 | 17 | 76% | 10 | 9.8 | 46.48 | 0 | 14.3 | 14 | 24.9 | — | — | — | 16564 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | xhigh | n/a | 2/2 | [3618a30940bc](configs/3618a30940bc.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 15.4 | 4.90 | 0 | — | 0 | 6.2 | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning | 19 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | xhigh | n/a | 2/2 | [3618a30940bc](configs/3618a30940bc.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 11.1 | 4.15 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning | 17 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [6f8f1c7b8d48](configs/6f8f1c7b8d48.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 11.5 | 3.52 | 0 | — | 0 | 8.0 | oQ4e-fp16 mixed precision + MTP tensors | ssd | off | 15 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [6f8f1c7b8d48](configs/6f8f1c7b8d48.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 13.2 | 3.67 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | ssd | off | 16 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [a7867bea182c](configs/a7867bea182c.yaml) — *config since changed* | e155170f4c1d | 8 | 0% | 0 | 12.8 | 3.84 | 0 | — | 0 | 6.9 | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning | 915 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [a7867bea182c](configs/a7867bea182c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 5 | 0% | 0 | 11.7 | 3.68 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning | 10268 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [b6112a82c243](configs/b6112a82c243.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 11.8 | 3.52 | 0 | — | 0 | 6.6 | oQ4e-fp16 mixed precision + MTP tensors | hot | off | 14 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [b6112a82c243](configs/b6112a82c243.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 11.8 | 3.50 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | hot | off | 15 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [b7b32d0eb150](configs/b7b32d0eb150.yaml) — *config since changed* | e155170f4c1d | 8 | 0% | 0 | 11.9 | 3.52 | 0 | — | 0 | 7.0 | oQ4e-fp16 mixed precision + MTP tensors | cold | off | 1086 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [b7b32d0eb150](configs/b7b32d0eb150.yaml) — *config since changed* | fc71ba2c66f8+dirty | 4 | 0% | 0 | 12.4 | 3.50 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | off | 9711 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [f9648093327f](configs/f9648093327f.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 12.4 | 3.51 | 0 | — | 0 | 6.4 | oQ4e-fp16 mixed precision + MTP tensors | cold | off | 16 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | n/a | 2/2 | [f9648093327f](configs/f9648093327f.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 12.4 | 3.49 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | off | 15 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 2c7b7c47693c | 3 | 100% | 0 | 58.5 | 6.40 | 0 | — | 0 | 7.2 | — | — | — | 85 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | — | [26670d622de5](configs/26670d622de5.yaml) | 2c7b7c47693c+dirty | 4 | 100% | 0 | 49.4 | 2.30 | 0 | — | 0 | 7.2 | — | — | — | 223 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 314e422cc5ac | 9 | 56% | 0 | 53.8 | 4.37 | 1 | — | 0 | 7.6 | — | — | — | 736 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 6a6b4bcf6907 | 9 | 56% | 0 | 53.9 | 4.36 | 1 | — | 0 | 7.6 | — | — | — | 707 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 937328228de2 | 9 | 89% | 1 | 53.8 | 4.37 | 1 | 38.0 | 7 | 8.0 | — | — | — | 1201 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | n/a | — | [26670d622de5](configs/26670d622de5.yaml) | c30b4df69e53 | 12 | 33% | 2 | 51.1 | 2.38 | 1 | 23.5 | 57 | 10.4 | — | — | — | 4341 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | ? | — | [011816a7d0df](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 429 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | 0.1 | n/a | n/a | 2/2 | [1d65d14c63a8](configs/1d65d14c63a8.yaml) — *config since changed* | 3182238013a3 | 9 | 11% | 0 | 90.7 | 6.50 | 0 | — | 0 | 4.8 | — | — | — | 125 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | ? | 2/2 | [aa5d02c11bba](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 81.6 | 5.54 | 0 | — | 0 | — | ? | ? | ? | 63 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [0840d8e3ee87](configs/0840d8e3ee87.yaml) | 5f0b7d975f67 | 9 | 56% | 0 | 73.4 | 3.77 | 1 | — | 0 | 5.8 | — | — | — | 1381 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | — | 0.1 | n/a | n/a | 2/2 | [0840d8e3ee87](configs/0840d8e3ee87.yaml) | fa0046f3b929 | 19 | 58% | 2 | 73.4 | 3.77 | 1 | 23.8 | 43 | 8.0 | — | — | — | 3278 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | ? | — | [57734ec83d1b](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 112 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | ? | 2/2 | [8dd47a586509](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 0 | 1.2 | 13.67 | 0 | — | 0 | — | ? | ? | ? | 417 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | ? | 2/2 | [a03394d84d27](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 1.3 | 15.56 | 0 | — | 0 | — | ? | ? | ? | 443 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | n/a | 2/2 | [b2dc92c2ed56](configs/b2dc92c2ed56.yaml) — *config since changed* | 65bb6d23192e | 8 | 75% | 1 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.7 | — | — | — | 1577 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | n/a | — | [b2dc92c2ed56](configs/b2dc92c2ed56.yaml) — *config since changed* | 65bb6d23192e+dirty | 1 | 0% | 0 | — | — | 0 | — | 0 | 5.8 | — | — | — | 107 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | n/a | 2/2 | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | 65bb6d23192e+dirty | 0 | n/a (all harness errors) | 0 | — | 1.39 | 0 | — | 0 | 5.5 | BF16 | cold | off | 5 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | n/a | — | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 0 | 11.1 | 23.25 | 1 | — | 0 | 5.5 | BF16 | cold | off | 2234 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | n/a | 2/2 | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 67% | 0 | 26.6 | 13.93 | 0 | — | 0 | — | BF16 | cold | off | 431 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | n/a | 2/2 | [6be3287df228](configs/6be3287df228.yaml) — *config since changed* | e0571a8c6ad8 | 5 | 80% | 1 | 8.1 | 16.74 | 0 | — | 0 | 5.5 | BF16 | cold | off | 1942 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | — | 0.1 | n/a | n/a | 2/2 | [c1a7fd5d3135](configs/c1a7fd5d3135.yaml) — *config since changed* | 937328228de2 | 1 | 100% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.7 | — | — | — | 159 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | — | 0.1 | n/a | n/a | 2/2 | [c1a7fd5d3135](configs/c1a7fd5d3135.yaml) — *config since changed* | c32555007281 | 9 | 78% | 2 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.8 | — | — | — | 1942 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | 1370f3a3609d | 9 | 56% | 0 | 92.6 | 4.17 | 0 | — | 0 | 17.1 | — | — | — | 285 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | 6a6b4bcf6907 | 9 | 56% | 0 | 92.9 | 4.16 | 0 | — | 0 | 16.8 | — | — | — | 163 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | a5743c4a242c | 19 | 32% | 0 | 92.7 | 4.16 | 0 | 12.1 | 36 | 18.8 | — | — | — | 790 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | ? | 2/2 | [303eba1d5495](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 103.7 | 5.03 | 0 | — | 0 | — | ? | ? | ? | 37 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | 0.2 | n/a | n/a | 2/2 | [5f50ca6ebdf3](configs/5f50ca6ebdf3.yaml) — *config since changed* | 3182238013a3 | 9 | 56% | 0 | 105.0 | 3.54 | 1 | — | 0 | 9.5 | — | — | — | 165 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | ? | — | [f4620fe8538d](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 26 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | — | 0.2 | n/a | n/a | 2/2 | [05a5098cf4c6](configs/05a5098cf4c6.yaml) | 13be39c4b506 | 19 | 32% | 0 | 106.5 | 3.52 | 1 | 5.1 | 12 | 11.3 | — | — | — | 504 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | — | 0.2 | n/a | n/a | 2/2 | [05a5098cf4c6](configs/05a5098cf4c6.yaml) | 50298bcbe02d | 19 | 32% | 0 | 105.1 | 3.55 | 1 | — | 0 | 11.4 | — | — | — | 990 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | — | ? | ? | ? | 2/2 | [85636a621ce0](configs/LiquidAI-LFM2.5-8B-A1B/gguf-dspark.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0 | 82.3 | 8.69 | 0 | — | 0 | — | ? | ? | ? | 183 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | — | 0.2 | n/a | n/a | 2/2 | [f6bb65acb160](configs/f6bb65acb160.yaml) — *config since changed* | 3182238013a3 | 9 | 67% | 0 | 42.9 | 7.47 | 1 | — | 0 | 13.7 | — | — | — | 286 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | — | 0.2 | n/a | n/a | 2/2 | [4f8641aa7094](configs/4f8641aa7094.yaml) — *config since changed* | f12e3bae97e9 | 9 | 67% | 0 | 42.8 | 7.48 | 1 | — | 0 | 13.8 | — | — | — | 248 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | ? | — | [5fd02e54bb9d](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 9 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | ? | 2/2 | [b9bea7cd700c](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 4.5 | 11.62 | 0 | — | 0 | — | ? | ? | ? | 130 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | 0.2 | n/a | n/a | 2/2 | [da00492c3b46](configs/da00492c3b46.yaml) — *config since changed* | e155170f4c1d | 9 | 56% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 10.2 | — | — | — | 482 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [e9ea1ba1fe73](configs/e9ea1ba1fe73.yaml) — *config since changed* | 3db0c69f5007 | 8 | 62% | 0 | 24.3 | 13.04 | 0 | — | 0 | 3.4 | BF16 | cold | off | 560 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [f3b91883da61](configs/f3b91883da61.yaml) — *config since changed* | e155170f4c1d | 8 | 75% | 0 | 23.2 | 13.26 | 0 | — | 0 | 12.2 | BF16 | cold | off | 596 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [f3b91883da61](configs/f3b91883da61.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 100% | 0 | 9.4 | 10.51 | 0 | — | 0 | — | BF16 | cold | off | 232 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | — | 0.2 | n/a | n/a | 2/2 | [9693319bc3a1](configs/9693319bc3a1.yaml) — *config since changed* | 798e2f07f493 | 9 | 67% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.5 | — | — | — | 504 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [00fc47aef271](configs/00fc47aef271.yaml) — *config since changed* | 65bb6d23192e | 8 | 75% | 0 | 15.0 | 13.02 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | cold | off | 375 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 4/4 | [00fc47aef271](configs/00fc47aef271.yaml) — *config since changed* | fc71ba2c66f8+dirty | 9 | 44% | 0 | 9.8 | 9.97 | 0 | — | 0 | — | oQ4-fp16 mixed precision | cold | off | 22061 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [8c159510d3a5](configs/8c159510d3a5.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | — | 1.05 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | ssd | off | 2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [8c159510d3a5](configs/8c159510d3a5.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | — | 0.81 | 0 | — | 0 | — | oQ4-fp16 mixed precision | ssd | off | 2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [b060a851140f](configs/b060a851140f.yaml) — *config since changed* | a19512e1c13a | 0 | n/a (all harness errors) | 0 | — | 0.71 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | hot | off | 3 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [b4a63fbb6a67](configs/b4a63fbb6a67.yaml) — *config since changed* | d0165994ca07 | 9 | 67% | 0 | 11.7 | 13.05 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | cold | off | 489 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [c1ed322cee8c](configs/c1ed322cee8c.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | — | 0.99 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | hot | off | 2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | n/a | 2/2 | [c1ed322cee8c](configs/c1ed322cee8c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | — | 1.57 | 0 | — | 0 | — | oQ4-fp16 mixed precision | hot | off | 4 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | 0.6 | thinking | n/a | 2/2 | [0e7c3d44eade](configs/0e7c3d44eade.yaml) — *config since changed* | d2d191e25579 | 23 | 91% | 0 | 61.5 | 49.65 | 0 | 7.8 | 6 | 1.2 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 2772 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | 0.6 | thinking | n/a | 2/2 | [2e8b1d29956e](configs/2e8b1d29956e.yaml) — *config since changed* | 3e8f2dbb5101+dirty | 23 | 100% | 2 | 57.9 | 43.44 | 0 | 8.9 | 12 | 1.3 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 5212 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | 0.6 | thinking | n/a | — | [3421f91401ab](configs/3421f91401ab.yaml) — *config since changed* | 0869b8310378 | 21 | 95% | 2 | 44.0 | 63.27 | 0 | 8.1 | 14 | 1.1 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 3718 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | 0.6 | thinking | n/a | 2/2 | [3421f91401ab](configs/3421f91401ab.yaml) — *config since changed* | 244380d4563e+dirty | 2 | 100% | 0 | 81.5 | 33.35 | 0 | — | 0 | 1.0 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 146 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | 0.6 | thinking | n/a | 2/2 | [d39c29f2d74b](configs/d39c29f2d74b.yaml) | 19250cc2f87b | 23 | 96% | 2 | 57.9 | 43.49 | 0 | 8.2 | 5 | 1.2 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 2976 |
| anthropic/claude-haiku-4.5 | openrouter | — | None | unspecified | n/a | 2/2 | [6cc890a25129](configs/6cc890a25129.yaml) | 6474518120ce+dirty | 19 | 89% | 0 | 55.0 | 1.72 | 0 | 16.6 | 22 | — | — | — | — | 855 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [3f3368f78d8d](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 13.3 | 58.80 | 0 | — | 0 | — | ? | ? | ? | 1199 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | n/a | 2/2 | [413f324b943c](configs/413f324b943c.yaml) — *config since changed* | 3182238013a3 | 8 | 50% | 1 | 11.7 | 35.49 | 0 | — | 0 | 21.2 | — | — | — | 2525 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [b0b30ac444da](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 50% | 0 | 13.4 | 57.94 | 0 | — | 0 | — | ? | ? | ? | 40255 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | 141399e74bd0 | 19 | 74% | 10 | 11.7 | 35.50 | 0 | 28.1 | 23 | 22.2 | — | — | — | 13066 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | 3959bd7a0f56+dirty | 5 | 60% | 1 | 12.4 | 45.62 | 0 | — | 0 | 21.2 | — | — | — | 1868 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | 75f452b3bab1 | 19 | 74% | 10 | 11.7 | 35.47 | 0 | 32.4 | 28 | 22.2 | — | — | — | 13256 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | — | [38ccea45c281](configs/38ccea45c281.yaml) | b17cb6e405c0+dirty | 18 | 83% | 13 | 10.4 | 11.69 | 0 | 31.2 | 32 | 22.6 | — | — | — | 16315 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | cf45f7655a7c | 19 | 63% | 9 | 11.7 | 35.47 | 0 | — | 0 | 21.8 | — | — | — | 13392 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | 1.0 | thinking | n/a | 2/2 | [5e61e8c02089](configs/5e61e8c02089.yaml) — *config since changed* | 3182238013a3 | 1 | 100% | 0 | 19.9 | 89.00 | 0 | — | 0 | 23.4 | — | — | — | 285 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | 1.0 | thinking | n/a | — | [5e61e8c02089](configs/5e61e8c02089.yaml) — *config since changed* | 3182238013a3+dirty | 7 | 0% | 0 | 13.1 | 27.90 | 0 | — | 0 | 23.2 | — | — | — | 329 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | ? | ? | ? | 2/2 | [fd29e9c067f8](configs/Muse-Glimmer-30B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 33% | 0 | 15.5 | 64.61 | 0 | — | 0 | — | ? | ? | ? | 1225 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | n/a | — | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 0ca55f47516d | 8 | 12% | 0 | 13.8 | 140.09 | 0 | — | 0 | 23.6 | — | — | — | 405 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | n/a | 1/1 | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 1ab13d3b7d57 | 0 | n/a (all harness errors) | 0 | — | 8.18 | 0 | — | 0 | 22.3 | — | — | — | 8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | n/a | 1/1 | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 1ab13d3b7d57+dirty | 0 | n/a (all harness errors) | 0 | 21.4 | 14.39 | 0 | — | 0 | 22.9 | — | — | — | 25 |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | n/a | n/a | 1/2 | [0a014488283a](configs/0a014488283a.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 22.7 | 0.79 | 0 | — | 0 | 20.5 | — | — | — | 2 |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | n/a | n/a | 1/2 | [e54758f4db2f](configs/e54758f4db2f.yaml) | 97f629ff59e1 | 0 | n/a (all harness errors) | 0 | 22.4 | 0.72 | 0 | — | 0 | 20.4 | — | — | — | 2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [e6a0628476cc](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 10.5 | 8.98 | 0 | — | 0 | — | ? | ? | ? | 294 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 4/4 | [f6397d624011](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 11.4 | 52.74 | 0 | — | 0 | — | ? | ? | ? | 12879 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | Q4_K_M+DFlash2 | ? | ? | ? | 2/2 | [0686abeab746](configs/Qwen3.8-27B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 9.3 | 55.96 | 0 | — | 0 | — | ? | ? | ? | 15711 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [5149cbc5a1b1](configs/5149cbc5a1b1.yaml) | 307dc5a146b4+dirty | 0 | n/a (all harness errors) | 0 | 13.5 | 5.83 | 0 | — | 0 | 22.8 | — | — | — | 18 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [5149cbc5a1b1](configs/5149cbc5a1b1.yaml) | b0cc46113de8+dirty | 1 | 100% | 1 | 9.0 | 239.40 | 0 | — | 0 | 23.5 | — | — | — | 359 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [5149cbc5a1b1](configs/5149cbc5a1b1.yaml) | de366070023d | 18 | 89% | 8 | 11.8 | 18.40 | 0 | 13.6 | 14 | 23.7 | — | — | — | 10012 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [c02615b57f21](configs/c02615b57f21.yaml) — *config since changed* | 9756e52a1739 | 19 | 84% | 11 | 11.7 | 38.00 | 0 | — | 0 | 23.7 | — | — | — | 11535 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [c7eb832ac1e8](configs/c7eb832ac1e8.yaml) — *config since changed* | 8bf29fca2f15 | 19 | 79% | 12 | 9.3 | 63.62 | 0 | — | 0 | 23.6 | — | — | — | 14061 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | ? | 2/2 | [163fa63ffb83](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 38.2 | 15.45 | 0 | — | 0 | — | ? | ? | ? | 102 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | ? | — | [29ed581f7054](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 422 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | 2e56f8121142 | 9 | 67% | 0 | 32.0 | 9.34 | 0 | — | 0 | 13.7 | — | — | — | 813 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | 38836484bab4 | 19 | 68% | 3 | 32.0 | 9.34 | 0 | 21.8 | 29 | 21.1 | — | — | — | 4195 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | 9df216e99cd9 | 23 | 83% | 3 | 31.9 | 9.34 | 0 | 18.7 | 33 | 21.0 | — | — | — | 4215 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | c8d9bde5c6d6 | 19 | 68% | 3 | 32.0 | 9.34 | 0 | 20.9 | 29 | 22.1 | — | — | — | 4889 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | ? | ? | ? | 2/2 | [6a3700901e2b](configs/Qwen3.8-27B-Ridge/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 50% | 0 | 7.9 | 52.03 | 0 | — | 0 | — | ? | ? | ? | 1756 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | 0.7 | instruct | n/a | 2/2 | [d135df9d860f](configs/d135df9d860f.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 0 | 7.8 | 30.15 | 0 | — | 0 | 18.9 | — | — | — | 1146 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | — | 0.7 | instruct | n/a | 2/2 | [7b1d82c8abab](configs/7b1d82c8abab.yaml) — *config since changed* | a58bee1684ac | 19 | 84% | 8 | 7.8 | 30.14 | 0 | — | 0 | 20.8 | — | — | — | 6945 |
| gpt-5.6-luna | api | — | ? | ? | ? | — | [86cbe69b94ae](configs/Luna/api.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 121 |
| gpt-5.6-luna | api | — | None | unspecified | n/a | — | [dc55dd82a2c3](configs/dc55dd82a2c3.yaml) — *config since changed* | e155170f4c1d | 1 | 0% | 0 | — | — | 0 | — | 0 | — | — | — | — | 12 |
| mlx-community/Devstral-Small-2507-4bit-DWQ | mlx | — | 0.15 | n/a | n/a | 1/2 | [54b39a32dd69](configs/54b39a32dd69.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | 19.9 | 9.13 | 0 | — | 0 | 8.7 | — | — | — | 21 |
| mlx-community/Devstral-Small-2507-4bit-DWQ | vllm-mlx | — | 0.15 | n/a | n/a | 1/2 | [8d60440a81e5](configs/8d60440a81e5.yaml) — *config since changed* | 8aec9f8f6135 | 0 | n/a (all harness errors) | 0 | 20.0 | 9.13 | 0 | — | 0 | 10.4 | — | — | — | 21 |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | — | 0.1 | n/a | n/a | 0/2 | [662a015ba0e6](configs/662a015ba0e6.yaml) — *config since changed* | 4f0aad77c3ab | 0 | n/a (all harness errors) | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 0.8 | — | — | — | 121 |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | — | 0.1 | n/a | n/a | 0/2 | [662a015ba0e6](configs/662a015ba0e6.yaml) — *config since changed* | 6a6b4bcf6907 | 0 | n/a (all harness errors) | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 0.8 | — | — | — | 120 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | mlx | — | 0.2 | n/a | n/a | 1/2 | [509fe12b4b1a](configs/509fe12b4b1a.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — | 7 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | n/a | 2/2 | [00878f13621f](configs/00878f13621f.yaml) — *config since changed* | 6a6b4bcf6907 | 9 | 56% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — | 986 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | n/a | 1/2 | [00878f13621f](configs/00878f13621f.yaml) — *config since changed* | dd3232d96137 | 0 | n/a (all harness errors) | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.0 | — | — | — | 6 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | n/a | 2/2 | [00878f13621f](configs/00878f13621f.yaml) — *config since changed* | e9a7e8ddd7d5 | 9 | 67% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — | 766 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | n/a | 2/2 | [9f649cd3051f](configs/9f649cd3051f.yaml) — *config since changed* | 9f1a9e467900 | 3 | 67% | 1 | 17.0 | 44.10 | 1 | — | 0 | 3.6 | MLX 4-bit | cold | off | 1367 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | n/a | 2/2 | [f1037eaa5995](configs/f1037eaa5995.yaml) — *config since changed* | 65bb6d23192e | 8 | 50% | 1 | 12.2 | 56.95 | 2 | — | 0 | 4.0 | MLX 4-bit | cold | off | 5998 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | n/a | 2/2 | [f1037eaa5995](configs/f1037eaa5995.yaml) — *config since changed* | fc71ba2c66f8+dirty | 5 | 40% | 0 | 17.2 | 42.82 | 1 | — | 0 | — | MLX 4-bit | cold | off | 17129 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [d9be6d0097ea](configs/d9be6d0097ea.yaml) — *config since changed* | 0869b8310378 | 23 | 22% | 0 | — | n/a (proxied — not real TTFT) | 0 | 11.3 | 26 | 0.7 | MLX 4-bit affine g64 (nemotron_h; 4 safetensors shards) | — | — | 5440 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [e7a6209b765d](configs/e7a6209b765d.yaml) — *config since changed* | cd2ddc279af0 | 8 | 12% | 0 | 55.6 | 68.06 | 0 | — | 0 | 0.4 | MLX 4-bit affine g64 (nemotron_h; 4 safetensors shards) | — | — | 695 |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | mlx | — | 0.7 | n/a | n/a | 1/2 | [c6d10ac83efc](configs/c6d10ac83efc.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | — | 0.76 | 0 | — | 0 | 10.0 | — | — | — | 2 |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | vllm-mlx | — | 0.7 | n/a | n/a | 1/2 | [389d88115d2d](configs/389d88115d2d.yaml) — *config since changed* | 3bca29f0ff7c | 0 | n/a (all harness errors) | 0 | — | 0.75 | 0 | — | 0 | 8.3 | — | — | — | 2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | 0.7 | instruct | n/a | 2/2 | [5e09e98f8c60](configs/5e09e98f8c60.yaml) — *config since changed* | e155170f4c1d | 9 | 67% | 0 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.7 | — | — | — | 415 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | ? | 2/2 | [8b3cbca5d1b1](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 6.1 | 22.76 | 0 | — | 0 | — | ? | ? | ? | 35401 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | ? | — | [92c4b9be230e](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 614 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | — | 0.7 | instruct | n/a | 2/2 | [08e51e50397d](configs/08e51e50397d.yaml) — *config since changed* | e155170f4c1d | 8 | 12% | 0 | 22.4 | 79.16 | 0 | — | 0 | 11.5 | MLX 4-bit | cold | off | 2795 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | — | 0.7 | instruct | n/a | 1/2 | [08e51e50397d](configs/08e51e50397d.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | — | 0.80 | 0 | — | 0 | — | MLX 4-bit | cold | off | 2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | vllm-mlx | — | 0.7 | instruct | n/a | 2/2 | [fe9f7a44a702](configs/fe9f7a44a702.yaml) — *config since changed* | c17e058823c1 | 8 | 75% | 4 | — | n/a (proxied — not real TTFT) | 0 | — | 0 | 7.2 | — | — | — | 3289 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | — | [cea524483faf](configs/cea524483faf.yaml) — *config since changed* | 6a6d9f534804 | 6 | 83% | 2 | — | — | 0 | 10.5 | 3 | 0.9 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 2434 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [cea524483faf](configs/cea524483faf.yaml) — *config since changed* | de1d34279681 | 13 | 92% | 3 | 44.1 | 52.79 | 0 | 20.8 | 19 | 1.1 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 3325 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | — | [cea524483faf](configs/cea524483faf.yaml) — *config since changed* | e5e8e82cdeb9 | 3 | 100% | 0 | — | — | 0 | 7.0 | 0 | 0.7 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 840 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [cfb4a5d79008](configs/cfb4a5d79008.yaml) — *config since changed* | d2d191e25579 | 23 | 83% | 4 | 51.8 | 51.33 | 0 | 12.0 | 27 | 1.2 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 7205 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [e2770ac7d2c4](configs/e2770ac7d2c4.yaml) — *config since changed* | 3e8f2dbb5101+dirty | 23 | 87% | 2 | 47.6 | 44.55 | 0 | 9.5 | 14 | 1.2 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 5712 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | 0.6 | thinking | n/a | 2/2 | [e9d6db1b6675](configs/e9d6db1b6675.yaml) — *config since changed* | 39dae7a6ea44 | 0 | n/a (all harness errors) | 0 | 123.7 | 5.87 | 0 | — | 0 | 0.3 | MLX 4-bit affine g64 (mlx-community; qwen3_5_moe conditional-generation arch), 8-bit router gates | — | — | 14 |
| mlx-community/Qwen3.8-27B-4bit | mei | — | 1.0 | thinking | n/a | 2/2 | [c7f10a958b1e](configs/c7f10a958b1e.yaml) | 7f3de21dba70 | 23 | 87% | 19 | 14.6 | 294.05 | 0 | 11.8 | 9 | 2.0 | MLX 4-bit affine g64 (mlx-community, qwen3_5 arch) | — | — | 22412 |
| mlx-community/Qwen3.8-27B-4bit | mei | — | 1.0 | thinking | n/a | 2/2 | [d23c67ad6d2d](configs/d23c67ad6d2d.yaml) — *config since changed* | 3496bdf4e3aa | 11 | 55% | 6 | 15.0 | 293.24 | 2 | 5.7 | 1 | 1.8 | MLX 4-bit affine g64 (mlx-community, qwen3_5 arch) | — | — | 7441 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | ? | 2/2 | [152424abaa13](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 4.9 | 198.83 | 0 | — | 0 | — | ? | ? | ? | 4851 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | 1.0 | thinking | n/a | 2/2 | [968652aede2d](configs/968652aede2d.yaml) — *config since changed* | 69e4b1fd937f | 3 | 67% | 2 | 4.9 | 198.67 | 1 | — | 0 | 1.6 | — | — | — | 4616 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | ? | 2/2 | [bbaa3dfa1953](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 0 | n/a (all harness errors) | 0 | 12.6 | 3.76 | 0 | — | 0 | — | ? | ? | ? | 28 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | ? | — | [f894953f1f80](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0 | 3.7 | 337.71 | 0 | — | 0 | — | ? | ? | ? | 8985 |
| mlx-community/Qwen3.8-27B-4bit | omlx | — | 1.0 | thinking | n/a | 2/2 | [1eec0081c5d6](configs/1eec0081c5d6.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 0% | 0 | 8.5 | 5.65 | 0 | — | 0 | — | MLX 4-bit | cold | off | 814 |
| mlx-community/Qwen3.8-27B-4bit | omlx | — | 1.0 | thinking | n/a | 2/2 | [3fbfdcc4ec02](configs/3fbfdcc4ec02.yaml) — *config since changed* | 24d38de98cb4 | 8 | 0% | 0 | 8.5 | 4.97 | 0 | — | 0 | 9.1 | MLX 4-bit | cold | off | 1190 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | — | 1.0 | unspecified | n/a | 2/2 | [bc93f3cc55a1](configs/bc93f3cc55a1.yaml) | 06f997b70746 | 8 | 75% | 0 | 19.2 | 53.56 | 0 | — | 0 | 2.7 | MLX 4-bit affine g64 (mlx-community, gemma4 arch) | — | — | 612 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | — | 1.0 | unspecified | n/a | — | [bc93f3cc55a1](configs/bc93f3cc55a1.yaml) | a171c0999673 | 15 | 67% | 2 | — | — | 0 | 18.7 | 25 | 2.3 | MLX 4-bit affine g64 (mlx-community, gemma4 arch) | — | — | 8068 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | — | 1.0 | unspecified | n/a | 2/2 | [c9417ad40f57](configs/c9417ad40f57.yaml) — *config since changed* | b293b2de057f | 8 | 75% | 0 | 18.5 | 53.68 | 0 | — | 0 | 2.7 | MLX 4-bit affine g64 (mlx-community, gemma4 arch) | — | — | 615 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [7b0652d1fb9e](configs/7b0652d1fb9e.yaml) | 4fd562e5fb7b | 19 | 100% | 4 | 41.1 | 7.12 | 0 | 17.5 | 28 | 22.0 | — | — | — | 2670 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | — | 0.6 | unspecified | n/a | 4/4 | [7b0652d1fb9e](configs/7b0652d1fb9e.yaml) | 755dc7f4b2a3 | 30 | 93% | 2 | 41.1 | 7.11 | 0 | 16.1 | 34 | 20.8 | — | — | — | 3919 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [7b0652d1fb9e](configs/7b0652d1fb9e.yaml) | 9df216e99cd9 | 23 | 87% | 3 | 33.3 | 10.29 | 0 | 15.3 | 28 | 18.9 | — | — | — | 4419 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | — | 0.6 | unspecified | n/a | — | [7b0652d1fb9e](configs/7b0652d1fb9e.yaml) | 9df216e99cd9+dirty | 13 | 92% | 3 | — | — | 0 | 16.1 | 29 | 20.3 | — | — | — | 3664 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [73c161a87535](configs/73c161a87535.yaml) — *config since changed* | 0adb046c1c3e+dirty | 23 | 91% | 4 | 39.5 | 7.16 | 0 | 14.2 | 27 | 24.4 | — | — | — | 3355 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | — | 1.0 | unspecified | n/a | 2/2 | [0b31098f54f7](configs/0b31098f54f7.yaml) | b17cb6e405c0 | 23 | 74% | 1 | 44.9 | 10.16 | 0 | 22.9 | 48 | 23.0 | — | — | — | 3447 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | — | 1.0 | unspecified | n/a | 2/2 | [49ec38e05e0c](configs/49ec38e05e0c.yaml) | 0adb046c1c3e+dirty | 23 | 87% | 3 | 42.9 | 10.67 | 0 | 20.2 | 34 | 23.8 | — | — | — | 5398 |
| openai/gpt-5.6-luna | api | — | ? | ? | ? | 2/2 | [1f7b55bd4401](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 27.3 | 4.30 | 0 | — | 0 | — | ? | ? | ? | 226 |
| openai/gpt-5.6-luna | api | — | ? | ? | ? | — | [bc97807766bc](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 89 |
| openai/gpt-5.6-luna | openrouter | — | None | unspecified | n/a | 2/2 | [f1e3043189f3](configs/f1e3043189f3.yaml) | 1e67356823c2 | 9 | 100% | 0 | 120.0 | 4.80 | 0 | — | 0 | — | — | — | — | 310 |
| openai/gpt-5.6-luna | openrouter | — | None | unspecified | n/a | — | [f1e3043189f3](configs/f1e3043189f3.yaml) | 20ce58c43993+dirty | 17 | 94% | 0 | 39.6 | 3.35 | 0 | 11.8 | 17 | — | — | — | — | 893 |
| openai/gpt-5.6-luna | openrouter | — | None | unspecified | n/a | 2/2 | [f1e3043189f3](configs/f1e3043189f3.yaml) | 9d8c6a3619ec+dirty | 2 | 100% | 0 | 25.8 | 2.15 | 0 | — | 0 | — | — | — | — | 22 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | — | 1.0 | thinking | n/a | 2/2 | [40fbffd03a95](configs/40fbffd03a95.yaml) | 0e516aa414aa | 23 | 70% | 16 | 19.3 | 304.51 | 0 | 9.2 | 7 | 2.1 | MLX 4-bit affine g64 (orcarouter repack of heretic-org abliteration, qwen3_5 arch) | — | — | 26902 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | — | 1.0 | thinking | n/a | 2/2 | [40fbffd03a95](configs/40fbffd03a95.yaml) | ab5fe7ef2281 | 0 | n/a (all harness errors) | 0 | 25.0 | 7.32 | 0 | — | 0 | 0.4 | MLX 4-bit affine g64 (orcarouter repack of heretic-org abliteration, qwen3_5 arch) | — | — | 19 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | — | 1.0 | thinking | n/a | — | [9a0bccfab07b](configs/9a0bccfab07b.yaml) — *config since changed* | 952f3df59606 | 20 | 65% | 13 | 22.7 | 379.91 | 1 | 10.7 | 12 | 2.3 | MLX 4-bit affine g64 (orcarouter repack of heretic-org abliteration, qwen3_5 arch) | — | — | 20416 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | — | 1.0 | thinking | n/a | 2/2 | [9a0bccfab07b](configs/9a0bccfab07b.yaml) — *config since changed* | b293b2de057f | 3 | 33% | 1 | 14.1 | 218.79 | 0 | — | 0 | 2.0 | MLX 4-bit affine g64 (orcarouter repack of heretic-org abliteration, qwen3_5 arch) | — | — | 2304 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [3047922de5b7](configs/Ornith-1.5-35B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 44.7 | 1.90 | 0 | — | 0 | — | ? | ? | ? | 41489 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 0adb046c1c3e | 23 | 96% | 3 | 42.2 | 6.96 | 0 | 15.5 | 22 | 23.5 | — | — | — | 3052 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 0b3a2a523049 | 9 | 89% | 0 | 42.3 | 6.96 | 0 | — | 0 | 22.8 | — | — | — | 694 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 319b144e6b0b | 5 | 100% | 0 | 43.3 | 8.67 | 0 | — | 0 | 22.5 | — | — | — | 152 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | — | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 319b144e6b0b+dirty | 13 | 100% | 2 | 39.7 | 2.98 | 0 | 16.9 | 24 | 22.8 | — | — | — | 2641 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 6cc8b646db2e | 19 | 95% | 2 | 42.2 | 6.96 | 0 | 17.7 | 20 | 23.9 | — | — | — | 2876 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | n/a | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) — *config since changed* | 9df216e99cd9 | 23 | 96% | 3 | 40.1 | 7.70 | 0 | 15.6 | 20 | 6.7 | — | — | — | 3207 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | thinking | medium | 2/2 | [f51c7e72e2ad](configs/f51c7e72e2ad.yaml) | 0adb046c1c3e+dirty | 23 | 96% | 3 | 42.4 | 7.01 | 0 | 16.8 | 28 | 23.6 | — | — | — | 3504 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [0a4370d3d909](configs/0a4370d3d909.yaml) | 6642492d4afd | 9 | 89% | 1 | 39.6 | 7.01 | 0 | 39.0 | 14 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 819 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [0a4370d3d909](configs/0a4370d3d909.yaml) | 7678bd71d022 | 20 | 65% | 2 | 38.2 | 10.75 | 0 | 12.5 | 17 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 3281 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [0a4370d3d909](configs/0a4370d3d909.yaml) | 8f1c03e85311 | 5 | 100% | 0 | 44.9 | 12.47 | 0 | — | 0 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 589 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 4/4 | [22dac305d46e](configs/22dac305d46e.yaml) — *config since changed* | 622d0ad7d2bd | 31 | 84% | 3 | 40.9 | 51.04 | 4 | 13.5 | 26 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 4287 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | 3165ebcc2e95 | 1 | 100% | 0 | 35.2 | 19.05 | 0 | — | 0 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 85 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | 3e8f2dbb5101+dirty | 10 | 100% | 1 | — | — | 0 | 8.2 | 5 | 0.9 | MLX 4-bit (ornith-ai official) | — | — | 2207 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | 5720fa988c0f | 22 | 91% | 0 | 43.9 | 53.98 | 0 | 10.9 | 17 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 2259 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | e21e81b1c0f9 | 10 | 100% | 0 | 42.9 | 43.39 | 0 | 11.5 | 2 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 994 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | e21e81b1c0f9+dirty | 0 | n/a (all harness errors) | 0 | — | — | 0 | — | 0 | — | MLX 4-bit (ornith-ai official) | — | — | 213 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [25f5a326d3b6](configs/25f5a326d3b6.yaml) — *config since changed* | ed0d851d6515 | 23 | 96% | 4 | 42.9 | 43.42 | 0 | 11.1 | 19 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 4754 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [3c10e74e125a](configs/3c10e74e125a.yaml) | 0d0686e785c5 | 47 | 89% | 0 | 47.5 | 5.20 | 0 | 9.4 | 12 | 1.4 | MLX 4-bit (ornith-ai official) | — | — | 2923 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 6/6 | [77d7ab43a6ee](configs/77d7ab43a6ee.yaml) — *config since changed* | 41307afcd611 | 7 | 29% | 0 | 39.9 | 9.01 | 0 | — | 0 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 745 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [77d7ab43a6ee](configs/77d7ab43a6ee.yaml) — *config since changed* | 84e884b96aee | 23 | 96% | 2 | 39.6 | 39.13 | 0 | 12.3 | 19 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 2964 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [865cf72cd70a](configs/865cf72cd70a.yaml) — *config since changed* | 210be56724fd | 4 | 100% | 0 | 39.0 | 37.29 | 0 | — | 0 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 289 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [865cf72cd70a](configs/865cf72cd70a.yaml) — *config since changed* | a5fc733bff47 | 4 | 25% | 0 | 43.7 | 55.48 | 0 | — | 0 | 1.1 | MLX 4-bit (ornith-ai official) | — | — | 107 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [958c5dde67bf](configs/958c5dde67bf.yaml) — *config since changed* | bb597e73b694 | 23 | 91% | 4 | 34.1 | 7.13 | 0 | 14.1 | 52 | 0.9 | MLX 4-bit (ornith-ai official) | — | — | 6378 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [c5171b0bd6e9](configs/c5171b0bd6e9.yaml) — *config since changed* | 643f7007d269 | 23 | 91% | 2 | 39.7 | 7.02 | 0 | 11.1 | 18 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 3580 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [c5171b0bd6e9](configs/c5171b0bd6e9.yaml) — *config since changed* | 89f2c911aa61 | 23 | 91% | 0 | 36.5 | 7.34 | 0 | 8.9 | 11 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 1861 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | — | [c5171b0bd6e9](configs/c5171b0bd6e9.yaml) — *config since changed* | ba5990e22812 | 5 | 100% | 0 | 42.1 | 12.80 | 0 | — | 0 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 623 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [cef5c7989663](configs/cef5c7989663.yaml) — *config since changed* | d2d191e25579 | 23 | 96% | 1 | 43.6 | 49.79 | 0 | 8.5 | 9 | 1.2 | MLX 4-bit (ornith-ai official) | — | — | 4317 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | 0.6 | unspecified | n/a | 2/2 | [dc3e7e62a965](configs/dc3e7e62a965.yaml) — *config since changed* | b293b2de057f | 23 | 87% | 1 | 41.9 | 50.92 | 2 | 8.2 | 11 | 1.3 | MLX 4-bit (ornith-ai official) | — | — | 3710 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | — | 0.6 | unspecified | n/a | 2/2 | [76414c6ab37c](configs/76414c6ab37c.yaml) — *config since changed* | 0620219fd55e | 8 | 38% | 0 | 11.8 | 41.53 | 2 | — | 0 | 2.1 | — | — | — | 1055 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | — | 0.6 | unspecified | n/a | 2/2 | [76414c6ab37c](configs/76414c6ab37c.yaml) — *config since changed* | dd3232d96137 | 8 | 62% | 1 | 12.0 | 41.50 | 2 | — | 0 | 2.4 | — | — | — | 1226 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | n/a | 2/2 | [d0d250e59d4e](configs/d0d250e59d4e.yaml) — *config since changed* | 9235ceaef852 | 1 | 100% | 0 | 14.1 | 31.46 | 0 | — | 0 | 8.2 | — | — | — | 198 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | n/a | 1/2 | [d0d250e59d4e](configs/d0d250e59d4e.yaml) — *config since changed* | bb858f72fc84 | 0 | n/a (all harness errors) | 0 | 29.9 | 1.11 | 0 | — | 0 | 0.7 | — | — | — | 17 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | n/a | — | [d0d250e59d4e](configs/d0d250e59d4e.yaml) — *config since changed* | dd3232d96137 | 7 | 71% | 4 | 6.8 | 92.83 | 0 | — | 0 | 5.5 | — | — | — | 6628 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 1/2 | [e427e7a50b14](configs/Laguna-XS-2.1/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 0 | n/a (all harness errors) | 0 | — | 11.96 | 0 | — | 0 | — | ? | ? | ? | 19 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [644ba3997136](configs/644ba3997136.yaml) | 9df216e99cd9 | 23 | 74% | 2 | — | n/a (proxied — not real TTFT) | 1 | 25.3 | 30 | 24.1 | — | — | — | 2840 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [644ba3997136](configs/644ba3997136.yaml) | e23570ec40be | 19 | 74% | 1 | — | n/a (proxied — not real TTFT) | 1 | 24.5 | 22 | 23.1 | — | — | — | 2167 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | 0.7 | unspecified | n/a | 2/2 | [2152fbd9febb](configs/2152fbd9febb.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 4 | 6.3 | 155.61 | 1 | — | 0 | 7.8 | — | — | — | 8261 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | ? | ? | ? | — | [8e85abe37e32](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 573 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | ? | 2/2 | [21faf0240ec3](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 8.3 | 117.18 | 0 | — | 0 | — | ? | ? | ? | 2420 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | ? | 2/2 | [c2576cd6b385](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 0 | 10.2 | 97.84 | 0 | — | 0 | — | ? | ? | ? | 1023 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | — | 0.7 | unspecified | n/a | 2/2 | [40462ce69e01](configs/40462ce69e01.yaml) — *config since changed* | e155170f4c1d | 8 | 88% | 6 | 21.9 | 162.80 | 0 | — | 0 | 8.7 | native ternary 2-bit | cold | off | 13914 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | — | 0.7 | unspecified | n/a | 2/2 | [40462ce69e01](configs/40462ce69e01.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 100% | 0 | 5.0 | 119.62 | 0 | — | 0 | — | native ternary 2-bit | cold | off | 1796 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [520aba6e3536](configs/520aba6e3536.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 43.9 | 1.38 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | ssd | off | 5 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [520aba6e3536](configs/520aba6e3536.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 44.5 | 1.38 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | ssd | off | 5 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [73b0cf925fea](configs/73b0cf925fea.yaml) — *config since changed* | 509bd4b35f4a | 0 | n/a (all harness errors) | 0 | 38.9 | 1.26 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | hot | off | 5 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [7bceae5b4c3c](configs/7bceae5b4c3c.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 44.7 | 1.39 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | hot | off | 6 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [7bceae5b4c3c](configs/7bceae5b4c3c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 43.8 | 1.38 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | hot | off | 5 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [a97504c7845e](configs/a97504c7845e.yaml) — *config since changed* | cf3789b0b88a | 1 | 100% | 1 | 23.0 | 19.60 | 0 | — | 0 | 7.3 | oQ4e-fp16 mixed precision | cold | off | 1283 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [ab16f8d988bf](configs/ab16f8d988bf.yaml) — *config since changed* | e0efff5679a7 | 0 | n/a (all harness errors) | 0 | 40.6 | 1.26 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | ssd | off | 5 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [afecbd0a9f5f](configs/afecbd0a9f5f.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 3 | 20.3 | 46.77 | 2 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | cold | off | 5392 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | n/a | 2/2 | [afecbd0a9f5f](configs/afecbd0a9f5f.yaml) — *config since changed* | fc71ba2c66f8+dirty | 4 | 75% | 0 | 12.0 | 35.28 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | cold | off | 15308 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [891242963db5](configs/891242963db5.yaml) | 0adb046c1c3e | 1 | 100% | 1 | — | — | 0 | 22.0 | 3 | 24.1 | — | — | — | 1896 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [891242963db5](configs/891242963db5.yaml) | 0adb046c1c3e+dirty | 23 | 87% | 16 | 11.1 | 49.89 | 0 | 13.6 | 17 | 24.2 | — | — | — | 22074 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 4/4 | [891242963db5](configs/891242963db5.yaml) | be370d5982b4+dirty | 16 | 94% | 7 | 10.9 | 49.90 | 0 | — | 0 | 24.7 | — | — | — | 10375 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [d6a1d4a8db43](configs/d6a1d4a8db43.yaml) — *config since changed* | b17cb6e405c0 | 8 | 88% | 3 | 11.1 | 49.90 | 0 | — | 0 | 23.7 | — | — | — | 3484 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [d6a1d4a8db43](configs/d6a1d4a8db43.yaml) — *config since changed* | be370d5982b4 | 23 | 83% | 14 | 11.1 | 49.91 | 0 | 11.3 | 19 | 24.3 | — | — | — | 15635 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [d6a1d4a8db43](configs/d6a1d4a8db43.yaml) — *config since changed* | be370d5982b4+dirty | 14 | 86% | 11 | — | — | 0 | 12.3 | 15 | 23.9 | — | — | — | 14704 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | 0.15 | n/a | n/a | 2/2 | [ffa862c18cff](configs/ffa862c18cff.yaml) | 3959bd7a0f56+dirty | 23 | 65% | 8 | 10.0 | 28.10 | 0 | 27.9 | 52 | 26.5 | — | — | — | 15872 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | 0.15 | n/a | n/a | 2/2 | [ffa862c18cff](configs/ffa862c18cff.yaml) | 63c1cbdae938 | 19 | 74% | 6 | 10.0 | 28.07 | 0 | 19.8 | 27 | 27.0 | — | — | — | 9310 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | 0.15 | n/a | n/a | 2/2 | [ffa862c18cff](configs/ffa862c18cff.yaml) | 711cf4da25b3 | 19 | 74% | 6 | 10.0 | 28.06 | 0 | 29.4 | 43 | 26.5 | — | — | — | 10470 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | instruct | n/a | 2/2 | [1fea08092fdc](configs/1fea08092fdc.yaml) — *config since changed* | e155170f4c1d | 9 | 67% | 0 | 26.1 | 9.51 | 1 | — | 0 | 23.9 | — | — | — | 872 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | ? | — | [840ac866adff](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? | 350 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [fe085c7fef30](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 29.8 | 18.49 | 0 | — | 0 | — | ? | ? | ? | 128 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | n/a | 2/2 | [644415678c37](configs/644415678c37.yaml) | 520355356ee0 | 19 | 74% | 2 | 26.1 | 9.50 | 1 | 29.5 | 50 | 24.5 | — | — | — | 3626 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | n/a | 2/2 | [644415678c37](configs/644415678c37.yaml) | 9df216e99cd9 | 23 | 83% | 6 | 26.1 | 9.50 | 1 | 27.5 | 45 | 25.1 | — | — | — | 5045 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | n/a | 2/2 | [644415678c37](configs/644415678c37.yaml) | bf1cd0ed7a6f | 9 | 67% | 1 | 26.3 | 9.51 | 1 | — | 0 | 23.4 | — | — | — | 4502 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | n/a | 2/2 | [644415678c37](configs/644415678c37.yaml) | db7724641d7e | 19 | 89% | 8 | 26.2 | 9.50 | 1 | 32.9 | 43 | 24.2 | — | — | — | 4331 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | — | 0.6 | thinking | n/a | 2/2 | [436d6d25d30c](configs/436d6d25d30c.yaml) — *config since changed* | 8d4f1f85f106 | 19 | 84% | 3 | 42.7 | 7.47 | 0 | — | 0 | 24.2 | — | — | — | 3491 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | UD-Q2_K_XL | ? | ? | ? | 2/2 | [2233edb1c4f2](configs/Qwen3.8-27B/gguf-unsloth-ud-q2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 10.8 | 55.08 | 0 | — | 0 | — | ? | ? | ? | 46175 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | — | ? | ? | ? | 2/2 | [89f4d8d04793](configs/Qwen3.8-27B/gguf-unsloth-ud-q4.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 10.4 | 55.57 | 0 | — | 0 | — | ? | ? | ? | 46233 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [340ca3032e6c](configs/340ca3032e6c.yaml) — *config since changed* | 24ac4057b970 | 9 | 89% | 3 | 11.6 | 46.40 | 0 | 17.0 | 2 | 24.8 | — | — | — | 4896 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [340ca3032e6c](configs/340ca3032e6c.yaml) — *config since changed* | 3959bd7a0f56+dirty | 12 | 92% | 10 | — | — | 0 | 11.0 | 9 | 24.6 | — | — | — | 11234 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [340ca3032e6c](configs/340ca3032e6c.yaml) — *config since changed* | b17cb6e405c0+dirty | 23 | 87% | 13 | 11.6 | 46.59 | 0 | 13.3 | 18 | 24.1 | — | — | — | 16645 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [340ca3032e6c](configs/340ca3032e6c.yaml) — *config since changed* | bfdc95c44bcb | 19 | 89% | 11 | 11.6 | 46.37 | 0 | 14.5 | 15 | 24.4 | — | — | — | 14279 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | xhigh | 2/2 | [41ee296edff9](configs/41ee296edff9.yaml) | 3f91f24193ba | 11 | 100% | 6 | 10.7 | 39.94 | 0 | 18.3 | 10 | 24.6 | — | — | — | 9230 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | xhigh | — | [41ee296edff9](configs/41ee296edff9.yaml) | f1ff19ce062d+dirty | 7 | 86% | 5 | — | — | 0 | 11.1 | 4 | 24.8 | — | — | — | 6470 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [6d148ccbfd2e](configs/6d148ccbfd2e.yaml) — *config since changed* | 1166272411af | 9 | 67% | 2 | 11.6 | 46.41 | 0 | — | 0 | 24.5 | — | — | — | 5487 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | n/a | 2/2 | [6d148ccbfd2e](configs/6d148ccbfd2e.yaml) — *config since changed* | 1b3350819dae | 5 | 80% | 1 | 8.9 | 45.73 | 0 | — | 0 | 24.6 | — | — | — | 2216 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | n/a | — | [6d148ccbfd2e](configs/6d148ccbfd2e.yaml) — *config since changed* | 53a9cfb2edfe | 14 | 93% | 10 | 17.0 | 47.78 | 0 | 10.9 | 9 | 24.1 | — | — | — | 10222 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | 2/2 | [8fb930e92b1b](configs/8fb930e92b1b.yaml) | 0adb046c1c3e | 3 | 100% | 1 | 9.4 | 58.58 | 0 | — | 0 | 24.6 | — | — | — | 598 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | medium | — | [8fb930e92b1b](configs/8fb930e92b1b.yaml) | 0adb046c1c3e+dirty | 20 | 95% | 14 | 13.4 | 34.17 | 0 | 13.5 | 18 | 25.7 | — | — | — | 15447 |

## Best overall (gate, then weighted composite score)

**Eligibility** — a group must have run sanity plus the FULL suite on both
hermes_ops (8 tasks) and coding (15 tasks)
to appear here at all — a partial run (even a lucky 1-task 100%) is excluded
outright, not scored on whichever axes it happens to have. A group's own
`runner_git_sha` must also be `benchmark-v2` or a later commit — data graded
under pre-v2 methodology (the broken Swift-fixture toolchain, the too-tight
1500s coding timeout) doesn't compete against current data regardless of
suite coverage. **Usefulness gate** (pass/fail tier, not a weighted input) — hermes_ops
pass rate must be ≥50% (majority-pass, same concept as run_bench.py's sanity
fail-fast gate); every gate-passing group ranks above every gate-failing one
regardless of the score below. **Score** among gate-passers is a weighted
composite over four axes — combined pass rate (45%,
hermes_ops + coding tasks together, not coding alone — a 50%-hermes_ops record
no longer scores identically to a 100% one once both clear the gate above),
decode speed (25%), time to first token (20%),
and turns used (10%) — each normalized 0.0-1.0 against
the best value seen among this run's gate-passing groups (see
`build_leaderboard.py`'s own comment for the exact formula and why). A slow
but eventually-correct model is no longer disqualified outright (coding-suite
timeouts were bumped alongside this change specifically so it can finish) —
it simply scores lower on speed/time than a faster model with the same pass
rate. Dedup rule: each model+engine+quant appears at most once, preferring
whichever of its own config_hash/runner_sha fragments is full-suite-complete
(over one that merely has more raw evidence but is missing an axis), then the
most total coding+hermes_ops evidence, then recency.

| rank | model | engine | quant | reasoning⁶ | config | usefulness gate | score | coding | decode speed | avg TTFT | total runtime (s)⁷ | avg turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | — | unspecified | 3c10e74e125a | PASS (88%, 32) | 0.895 | 93% (15) | 47.5 tok/s | 5.20s | 2923 | 9.4 |
| 2 | ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | thinking (medium) | f51c7e72e2ad | PASS (100%, 8) | 0.811 | 93% (15) | 42.4 tok/s | 7.01s | 3504 | 16.8 |
| 3 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | — | thinking | d39c29f2d74b | PASS (100%, 8) | 0.804 | 93% (15) | 57.9 tok/s | 43.49s | 2976 | 8.2 |
| 4 | mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | — | unspecified | 73c161a87535 | PASS (88%, 8) | 0.784 | 93% (15) | 39.5 tok/s | 7.16s | 3355 | 14.2 |
| 5 | HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | thinking | 98fbff8ca864 | PASS (75%, 8) | 0.759 | 87% (15) | 43.4 tok/s | 7.05s | 2767 | 15.7 |
| 6 | mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | — | unspecified | 49ec38e05e0c | PASS (88%, 8) | 0.714 | 87% (15) | 42.9 tok/s | 10.67s | 5398 | 20.2 |
| 7 | mlx-community/Qwen3.6-35B-A3B-4bit | mei | — | thinking | e2770ac7d2c4 | PASS (88%, 8) | 0.706 | 87% (15) | 47.6 tok/s | 44.55s | 5712 | 9.5 |
| 8 | mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | — | unspecified | 7b0652d1fb9e | PASS (100%, 8) | 0.690 | 80% (15) | 33.3 tok/s | 10.29s | 4419 | 15.3 |
| 9 | bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | thinking | a2d241742068 | PASS (75%, 8) | 0.665 | 87% (15) | 31.9 tok/s | 9.34s | 4215 | 18.7 |
| 10 | mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | — | unspecified | 0b31098f54f7 | PASS (75%, 8) | 0.665 | 73% (15) | 44.9 tok/s | 10.16s | 3447 | 22.9 |
| 11 | unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | instruct | 644415678c37 | PASS (75%, 8) | 0.624 | 87% (15) | 26.1 tok/s | 9.50s | 5045 | 27.5 |
| 12 | mlx-community/Qwen3.8-27B-4bit | mei | — | thinking | c7f10a958b1e | PASS (75%, 8) | 0.527 | 93% (15) | 14.6 tok/s | 294.05s | 22412 | 11.8 |
| 13 | unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | thinking (medium) | 340ca3032e6c | PASS (88%, 8) | 0.526 | 87% (15) | 11.6 tok/s | 46.59s | 16645 | 13.3 |
| 14 | trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | thinking (medium) | 891242963db5 | PASS (100%, 8) | 0.513 | 80% (15) | 11.1 tok/s | 49.89s | 22074 | 15.4 |
| 15 | orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | — | thinking | 40fbffd03a95 | PASS (62%, 8) | 0.453 | 73% (15) | 19.3 tok/s | 304.51s | 26902 | 15.3 |
| 16 | unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | n/a | ffa862c18cff | PASS (75%, 8) | 0.403 | 60% (15) | 10.0 tok/s | 28.10s | 15872 | 27.9 |
| 17 | poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | — | thinking | 644ba3997136 | PASS (50%, 8) | 0.365 | 87% (15) | — | — | 2840 | 25.3 |
| 18 | mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | — | thinking | d9be6d0097ea | FAIL (12%, 8) | — | 27% (15) | — | — | 5440 | 11.3 |

![Best overall composite score by model](score_chart.png)

## Flaky tasks (mixed pass/fail under identical conditions)

Any task with the SAME (model, inference_engine, quant, config_hash,
runner_git_sha, suite, task_id) that comes back with SOME passes and
some fails is not "probably fine" — it's proof this one task's result
isn't safe to treat as a boolean for this model — temperature=0
measurably does not make MLX/Metal generation deterministic across
runs. This catches flakiness from an explicit
`--trials N` run AND from two separate invocations that happen to share
every one of those fields (found live: a real historical entry below
came from two independent runs, not --trials, which didn't exist yet).
Tasks run only once never appear here — that is NOT the same as
confirmed-stable, just untested for flakiness.

| model | engine | quant | config | suite | task | pass/trials |
|---|---|---|---|---|---|---|
| mlx-community/Qwen3.8-27B-4bit | mlx | — | f894953f1f80 | hermes_ops | hermes_ops-selection | 1/2 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | — | 891242963db5 | hermes_ops | hermes_ops-targeted-edit | 1/2 |

## By suite

| model | engine | config | runner | suite | pass rate |
|---|---|---|---|---|---|
| AtomicChat/Laguna-XS-2.1-MLX-5bit | mei | d65c8f880447 | 3e8f2dbb5101+dirty | hermes_ops | 2/8 |
| AtomicChat/Laguna-XS-2.1-MLX-5bit | mei | d65c8f880447 | 3e8f2dbb5101+dirty | sanity | 2/2 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 5fc289161e34 | hermes_ops | 6/8 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 5fc289161e34 | sanity | 2/2 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 6bb085a043fe | hearth_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 6bb085a043fe | hermes_ops | 6/8 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 6bb085a043fe | kiem_mini | 4/5 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 6bb085a043fe | kipclip_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 6bb085a043fe | sanity | 2/2 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | hearth_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | kiem_mini | 5/5 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | kipclip_mini | 2/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654 | hermes_ops | 1/1 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654 | sanity | 2/2 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654+dirty | hearth_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654+dirty | hermes_ops | 5/7 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654+dirty | kiem_mini | 5/5 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | d60debfa3654+dirty | kipclip_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | hermes_ops | 6/8 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | kiem_mini | 4/5 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | kipclip_mini | 3/4 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 98fbff8ca864 | 0adb046c1c3e+dirty | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 18b93c687e8d+dirty | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 18b93c687e8d+dirty | kiem_mini | 1/1 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 18b93c687e8d+dirty | kipclip_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 7336e84ce111 | hermes_ops | 6/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 7336e84ce111 | kiem_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 32924ffd3dd9 | 7336e84ce111 | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | 2477ca2ba371 | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | 2477ca2ba371 | hermes_ops | 6/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | 2477ca2ba371 | kiem_mini | 4/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | 2477ca2ba371 | kipclip_mini | 2/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | 2477ca2ba371 | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | hermes_ops | 5/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | kiem_mini | 5/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | kipclip_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | 7103a8c7677c | ba9bffb50e12+dirty | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | 7103a8c7677c | ba9bffb50e12+dirty | hermes_ops | 5/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | 7103a8c7677c | ba9bffb50e12+dirty | kiem_mini | 3/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | 7103a8c7677c | ba9bffb50e12+dirty | kipclip_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | 7103a8c7677c | ba9bffb50e12+dirty | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 1dbc371640ce | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 1dbc371640ce | hermes_ops | 5/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 1dbc371640ce | kiem_mini | 4/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 1dbc371640ce | kipclip_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 1dbc371640ce | sanity | 2/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 24ac4057b970 | hearth_full | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 24ac4057b970 | kipclip_mini | 1/2 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 9df216e99cd9 | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 9df216e99cd9 | hermes_ops | 5/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 9df216e99cd9 | kiem_mini | 4/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 9df216e99cd9 | kipclip_mini | 1/1 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | b03fc3f2b8f8 | 9df216e99cd9 | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 3618a30940bc | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 3618a30940bc | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 6f8f1c7b8d48 | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 6f8f1c7b8d48 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | e155170f4c1d | hermes_ops | 0/8 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | kiem_mini | 0/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b6112a82c243 | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b6112a82c243 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | e155170f4c1d | hermes_ops | 0/8 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | kiem_mini | 0/1 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | f9648093327f | e155170f4c1d | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | f9648093327f | fc71ba2c66f8+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 2c7b7c47693c | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 2c7b7c47693c | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 2c7b7c47693c+dirty | hermes_ops | 4/4 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 314e422cc5ac | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 314e422cc5ac | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 314e422cc5ac | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 6a6b4bcf6907 | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 6a6b4bcf6907 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 6a6b4bcf6907 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 937328228de2 | hermes_ops | 7/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 937328228de2 | kiem_mini | 1/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | 937328228de2 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | c30b4df69e53 | hearth_mini | 2/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | c30b4df69e53 | hermes_ops | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | c30b4df69e53 | kiem_mini | 1/5 |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | 26670d622de5 | c30b4df69e53 | kipclip_mini | 1/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 011816a7d0df | *(predates tracking)* | kiem_mini | 1/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 1d65d14c63a8 | 3182238013a3 | hermes_ops | 1/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 1d65d14c63a8 | 3182238013a3 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 1d65d14c63a8 | 3182238013a3 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | 5f0b7d975f67 | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | 5f0b7d975f67 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | 5f0b7d975f67 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | fa0046f3b929 | hearth_mini | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | fa0046f3b929 | hermes_ops | 7/8 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | fa0046f3b929 | kiem_mini | 0/5 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | fa0046f3b929 | kipclip_mini | 1/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | 0840d8e3ee87 | fa0046f3b929 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 57734ec83d1b | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | hermes_ops | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | b2dc92c2ed56 | 65bb6d23192e | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | b2dc92c2ed56 | 65bb6d23192e | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | b2dc92c2ed56 | 65bb6d23192e+dirty | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | 65bb6d23192e+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | e155170f4c1d | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | fc71ba2c66f8+dirty | hermes_ops | 2/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | fc71ba2c66f8+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 6be3287df228 | e0571a8c6ad8 | hermes_ops | 4/5 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 6be3287df228 | e0571a8c6ad8 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | c1a7fd5d3135 | 937328228de2 | hermes_ops | 1/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | c1a7fd5d3135 | 937328228de2 | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | c1a7fd5d3135 | c32555007281 | hermes_ops | 7/8 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | c1a7fd5d3135 | c32555007281 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | c1a7fd5d3135 | c32555007281 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 1370f3a3609d | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 1370f3a3609d | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 1370f3a3609d | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 6a6b4bcf6907 | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 6a6b4bcf6907 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | 6a6b4bcf6907 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | a5743c4a242c | hearth_mini | 0/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | a5743c4a242c | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | a5743c4a242c | kiem_mini | 0/5 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | a5743c4a242c | kipclip_mini | 0/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | a148c29637e6 | a5743c4a242c | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 5f50ca6ebdf3 | 3182238013a3 | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 5f50ca6ebdf3 | 3182238013a3 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 5f50ca6ebdf3 | 3182238013a3 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | f4620fe8538d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 13be39c4b506 | hearth_mini | 0/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 13be39c4b506 | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 13be39c4b506 | kiem_mini | 0/5 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 13be39c4b506 | kipclip_mini | 0/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 13be39c4b506 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 50298bcbe02d | hearth_mini | 0/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 50298bcbe02d | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 50298bcbe02d | kiem_mini | 0/5 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 50298bcbe02d | kipclip_mini | 1/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | 05a5098cf4c6 | 50298bcbe02d | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | f6bb65acb160 | 3182238013a3 | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | f6bb65acb160 | 3182238013a3 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | f6bb65acb160 | 3182238013a3 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | 4f8641aa7094 | f12e3bae97e9 | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | 4f8641aa7094 | f12e3bae97e9 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | 4f8641aa7094 | f12e3bae97e9 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | 5fd02e54bb9d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | da00492c3b46 | e155170f4c1d | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | da00492c3b46 | e155170f4c1d | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | da00492c3b46 | e155170f4c1d | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | e9ea1ba1fe73 | 3db0c69f5007 | hermes_ops | 5/8 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | e9ea1ba1fe73 | 3db0c69f5007 | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | e155170f4c1d | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | e155170f4c1d | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | fc71ba2c66f8+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | 9693319bc3a1 | 798e2f07f493 | hermes_ops | 6/8 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | 9693319bc3a1 | 798e2f07f493 | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | 9693319bc3a1 | 798e2f07f493 | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | 65bb6d23192e | hermes_ops | 6/8 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | 65bb6d23192e | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | hermes_ops | 4/6 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | kiem_mini | 0/3 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | sanity | 4/4 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 8c159510d3a5 | 65bb6d23192e | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 8c159510d3a5 | fc71ba2c66f8+dirty | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | b060a851140f | a19512e1c13a | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | b4a63fbb6a67 | d0165994ca07 | hermes_ops | 6/8 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | b4a63fbb6a67 | d0165994ca07 | kiem_mini | 0/1 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | b4a63fbb6a67 | d0165994ca07 | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | c1ed322cee8c | 65bb6d23192e | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | c1ed322cee8c | fc71ba2c66f8+dirty | sanity | 2/2 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | hearth_full | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | hearth_mini | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | hermes_ops | 8/8 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | kiem_mini | 3/5 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | kipclip_mini | 4/4 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 0e7c3d44eade | d2d191e25579 | sanity | 2/2 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | hearth_full | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | hearth_mini | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | hermes_ops | 8/8 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | kiem_mini | 5/5 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | kipclip_mini | 4/4 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 2e8b1d29956e | 3e8f2dbb5101+dirty | sanity | 2/2 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 0869b8310378 | hearth_full | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 0869b8310378 | hearth_mini | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 0869b8310378 | hermes_ops | 6/6 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 0869b8310378 | kiem_mini | 4/5 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 0869b8310378 | kipclip_mini | 4/4 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 244380d4563e+dirty | hermes_ops | 2/2 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | 3421f91401ab | 244380d4563e+dirty | sanity | 2/2 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | hearth_full | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | hearth_mini | 3/3 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | hermes_ops | 8/8 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | kiem_mini | 4/5 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | kipclip_mini | 4/4 |
| Tostibrown/Qwen3.6-35B-A3B-4bit-textonly | mei | d39c29f2d74b | 19250cc2f87b | sanity | 2/2 |
| anthropic/claude-haiku-4.5 | openrouter | 6cc890a25129 | 6474518120ce+dirty | hearth_mini | 3/3 |
| anthropic/claude-haiku-4.5 | openrouter | 6cc890a25129 | 6474518120ce+dirty | hermes_ops | 8/8 |
| anthropic/claude-haiku-4.5 | openrouter | 6cc890a25129 | 6474518120ce+dirty | kiem_mini | 3/5 |
| anthropic/claude-haiku-4.5 | openrouter | 6cc890a25129 | 6474518120ce+dirty | kipclip_mini | 3/3 |
| anthropic/claude-haiku-4.5 | openrouter | 6cc890a25129 | 6474518120ce+dirty | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 3f3368f78d8d | *(predates tracking)* | hermes_ops | 2/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 3f3368f78d8d | *(predates tracking)* | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 413f324b943c | 3182238013a3 | hermes_ops | 4/8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 413f324b943c | 3182238013a3 | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | hermes_ops | 1/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | kiem_mini | 1/1 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 141399e74bd0 | hearth_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 141399e74bd0 | hermes_ops | 5/8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 141399e74bd0 | kiem_mini | 3/5 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 141399e74bd0 | kipclip_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 141399e74bd0 | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 3959bd7a0f56+dirty | hermes_ops | 3/5 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 3959bd7a0f56+dirty | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 75f452b3bab1 | hearth_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 75f452b3bab1 | hermes_ops | 5/8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 75f452b3bab1 | kiem_mini | 3/5 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 75f452b3bab1 | kipclip_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | 75f452b3bab1 | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | b17cb6e405c0+dirty | hearth_full | 2/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | b17cb6e405c0+dirty | hearth_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | b17cb6e405c0+dirty | hermes_ops | 2/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | b17cb6e405c0+dirty | kiem_mini | 4/5 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | b17cb6e405c0+dirty | kipclip_mini | 4/4 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | cf45f7655a7c | hearth_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | cf45f7655a7c | hermes_ops | 4/8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | cf45f7655a7c | kiem_mini | 2/5 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | cf45f7655a7c | kipclip_mini | 3/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | 38ccea45c281 | cf45f7655a7c | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | 5e61e8c02089 | 3182238013a3 | hermes_ops | 1/1 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | 5e61e8c02089 | 3182238013a3 | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | 5e61e8c02089 | 3182238013a3+dirty | hermes_ops | 0/7 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | fd29e9c067f8 | *(predates tracking)* | hermes_ops | 1/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | fd29e9c067f8 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | 17768c195364 | 0ca55f47516d | hermes_ops | 1/8 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | 17768c195364 | 1ab13d3b7d57 | sanity | 1/1 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | 17768c195364 | 1ab13d3b7d57+dirty | sanity | 1/1 |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | gguf | 0a014488283a | e155170f4c1d | sanity | 1/2 |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | llama.cpp | e54758f4db2f | 97f629ff59e1 | sanity | 1/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | 0686abeab746 | *(predates tracking)* | hermes_ops | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | 0686abeab746 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | e6a0628476cc | *(predates tracking)* | hermes_ops | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | e6a0628476cc | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | *(predates tracking)* | hermes_ops | 4/4 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | *(predates tracking)* | sanity | 4/4 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | 307dc5a146b4+dirty | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | b0cc46113de8+dirty | hermes_ops | 1/1 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | de366070023d | hearth_mini | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | de366070023d | hermes_ops | 7/7 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | de366070023d | kiem_mini | 4/5 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | 5149cbc5a1b1 | de366070023d | kipclip_mini | 2/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c02615b57f21 | 9756e52a1739 | hearth_mini | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c02615b57f21 | 9756e52a1739 | hermes_ops | 7/8 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c02615b57f21 | 9756e52a1739 | kiem_mini | 4/5 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c02615b57f21 | 9756e52a1739 | kipclip_mini | 2/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c02615b57f21 | 9756e52a1739 | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c7eb832ac1e8 | 8bf29fca2f15 | hearth_mini | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c7eb832ac1e8 | 8bf29fca2f15 | hermes_ops | 7/8 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c7eb832ac1e8 | 8bf29fca2f15 | kiem_mini | 2/5 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c7eb832ac1e8 | 8bf29fca2f15 | kipclip_mini | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | c7eb832ac1e8 | 8bf29fca2f15 | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | *(predates tracking)* | hermes_ops | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 29ed581f7054 | *(predates tracking)* | kiem_mini | 1/1 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 2e56f8121142 | hermes_ops | 6/8 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 2e56f8121142 | kiem_mini | 0/1 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 2e56f8121142 | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 38836484bab4 | hearth_mini | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 38836484bab4 | hermes_ops | 6/8 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 38836484bab4 | kiem_mini | 2/5 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 38836484bab4 | kipclip_mini | 3/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 38836484bab4 | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | hearth_full | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | hearth_mini | 3/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | hermes_ops | 6/8 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | kiem_mini | 4/5 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | kipclip_mini | 4/4 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | 9df216e99cd9 | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | c8d9bde5c6d6 | hearth_mini | 3/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | c8d9bde5c6d6 | hermes_ops | 6/8 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | c8d9bde5c6d6 | kiem_mini | 2/5 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | c8d9bde5c6d6 | kipclip_mini | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | a2d241742068 | c8d9bde5c6d6 | sanity | 2/2 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | hermes_ops | 1/3 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | kiem_mini | 1/1 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | sanity | 2/2 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | d135df9d860f | e155170f4c1d | hermes_ops | 5/8 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | d135df9d860f | e155170f4c1d | sanity | 2/2 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | 7b1d82c8abab | a58bee1684ac | hearth_mini | 3/3 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | 7b1d82c8abab | a58bee1684ac | hermes_ops | 5/8 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | 7b1d82c8abab | a58bee1684ac | kiem_mini | 5/5 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | 7b1d82c8abab | a58bee1684ac | kipclip_mini | 3/3 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | 7b1d82c8abab | a58bee1684ac | sanity | 2/2 |
| gpt-5.6-luna | api | 86cbe69b94ae | *(predates tracking)* | kiem_mini | 1/1 |
| gpt-5.6-luna | api | dc55dd82a2c3 | e155170f4c1d | kiem_mini | 0/1 |
| mlx-community/Devstral-Small-2507-4bit-DWQ | mlx | 54b39a32dd69 | 65bb6d23192e | sanity | 1/2 |
| mlx-community/Devstral-Small-2507-4bit-DWQ | vllm-mlx | 8d60440a81e5 | 8aec9f8f6135 | sanity | 1/2 |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | 662a015ba0e6 | 4f0aad77c3ab | sanity | 0/2 |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | 662a015ba0e6 | 6a6b4bcf6907 | sanity | 0/2 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | mlx | 509fe12b4b1a | e155170f4c1d | sanity | 1/2 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | 6a6b4bcf6907 | hermes_ops | 5/8 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | 6a6b4bcf6907 | kiem_mini | 0/1 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | 6a6b4bcf6907 | sanity | 2/2 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | dd3232d96137 | sanity | 1/2 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | e9a7e8ddd7d5 | hermes_ops | 6/8 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | e9a7e8ddd7d5 | kiem_mini | 0/1 |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | 00878f13621f | e9a7e8ddd7d5 | sanity | 2/2 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | 9f649cd3051f | 9f1a9e467900 | hermes_ops | 2/3 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | 9f649cd3051f | 9f1a9e467900 | sanity | 2/2 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | 65bb6d23192e | hermes_ops | 4/8 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | 65bb6d23192e | sanity | 2/2 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | hermes_ops | 2/3 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | kiem_mini | 0/2 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | sanity | 2/2 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | hearth_full | 1/3 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | hearth_mini | 0/3 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | hermes_ops | 1/8 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | kiem_mini | 0/5 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | kipclip_mini | 3/4 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | d9be6d0097ea | 0869b8310378 | sanity | 2/2 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | e7a6209b765d | cd2ddc279af0 | hermes_ops | 1/8 |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | e7a6209b765d | cd2ddc279af0 | sanity | 2/2 |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | mlx | c6d10ac83efc | e155170f4c1d | sanity | 1/2 |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | vllm-mlx | 389d88115d2d | 3bca29f0ff7c | sanity | 1/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 5e09e98f8c60 | e155170f4c1d | hermes_ops | 6/8 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 5e09e98f8c60 | e155170f4c1d | kiem_mini | 0/1 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 5e09e98f8c60 | e155170f4c1d | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | hermes_ops | 2/3 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 92c4b9be230e | *(predates tracking)* | kiem_mini | 1/1 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | 08e51e50397d | e155170f4c1d | hermes_ops | 1/8 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | 08e51e50397d | e155170f4c1d | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | 08e51e50397d | fc71ba2c66f8+dirty | sanity | 1/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | vllm-mlx | fe9f7a44a702 | c17e058823c1 | hermes_ops | 6/8 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | vllm-mlx | fe9f7a44a702 | c17e058823c1 | sanity | 2/2 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | 6a6d9f534804 | hearth_full | 3/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | 6a6d9f534804 | kipclip_mini | 2/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | de1d34279681 | hermes_ops | 7/8 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | de1d34279681 | kiem_mini | 5/5 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | de1d34279681 | sanity | 2/2 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | e5e8e82cdeb9 | hearth_mini | 2/2 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cea524483faf | e5e8e82cdeb9 | kipclip_mini | 1/1 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | hearth_full | 2/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | hearth_mini | 3/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | hermes_ops | 7/8 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | kiem_mini | 3/5 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | kipclip_mini | 4/4 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | cfb4a5d79008 | d2d191e25579 | sanity | 2/2 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | hearth_full | 3/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | hearth_mini | 3/3 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | hermes_ops | 7/8 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | kiem_mini | 3/5 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | kipclip_mini | 4/4 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e2770ac7d2c4 | 3e8f2dbb5101+dirty | sanity | 2/2 |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | e9d6db1b6675 | 39dae7a6ea44 | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | hearth_full | 3/3 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | hearth_mini | 3/3 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | hermes_ops | 6/8 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | kiem_mini | 4/5 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | kipclip_mini | 4/4 |
| mlx-community/Qwen3.8-27B-4bit | mei | c7f10a958b1e | 7f3de21dba70 | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mei | d23c67ad6d2d | 3496bdf4e3aa | hermes_ops | 4/8 |
| mlx-community/Qwen3.8-27B-4bit | mei | d23c67ad6d2d | 3496bdf4e3aa | kiem_mini | 2/3 |
| mlx-community/Qwen3.8-27B-4bit | mei | d23c67ad6d2d | 3496bdf4e3aa | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | hermes_ops | 3/3 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 968652aede2d | 69e4b1fd937f | hermes_ops | 2/3 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 968652aede2d | 69e4b1fd937f | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | bbaa3dfa1953 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | f894953f1f80 | *(predates tracking)* | hermes_ops | 3/4 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 1eec0081c5d6 | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 1eec0081c5d6 | fc71ba2c66f8+dirty | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 3fbfdcc4ec02 | 24d38de98cb4 | hermes_ops | 0/8 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 3fbfdcc4ec02 | 24d38de98cb4 | sanity | 2/2 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | 06f997b70746 | hermes_ops | 6/8 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | 06f997b70746 | sanity | 2/2 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | a171c0999673 | hearth_full | 3/3 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | a171c0999673 | hearth_mini | 2/3 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | a171c0999673 | kiem_mini | 1/5 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | bc93f3cc55a1 | a171c0999673 | kipclip_mini | 4/4 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | c9417ad40f57 | b293b2de057f | hermes_ops | 6/8 |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | c9417ad40f57 | b293b2de057f | sanity | 2/2 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 4fd562e5fb7b | hearth_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 4fd562e5fb7b | hermes_ops | 8/8 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 4fd562e5fb7b | kiem_mini | 5/5 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 4fd562e5fb7b | kipclip_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 4fd562e5fb7b | sanity | 2/2 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | hearth_full | 2/2 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | hearth_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | hermes_ops | 16/16 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | kiem_mini | 3/5 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | kipclip_mini | 4/4 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 755dc7f4b2a3 | sanity | 4/4 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | hearth_full | 2/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | hearth_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | hermes_ops | 8/8 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | kiem_mini | 3/5 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | kipclip_mini | 4/4 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9 | sanity | 2/2 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9+dirty | hearth_full | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9+dirty | hearth_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9+dirty | kiem_mini | 2/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | 7b0652d1fb9e | 9df216e99cd9+dirty | kipclip_mini | 4/4 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | hermes_ops | 7/8 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | kiem_mini | 4/5 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | kipclip_mini | 4/4 |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-I-Quality | llama.cpp | 73c161a87535 | 0adb046c1c3e+dirty | sanity | 2/2 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | hearth_full | 3/3 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | hearth_mini | 3/3 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | hermes_ops | 6/8 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | kiem_mini | 2/5 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | kipclip_mini | 3/4 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Compact | llama.cpp | 0b31098f54f7 | b17cb6e405c0 | sanity | 2/2 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | hermes_ops | 7/8 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | kiem_mini | 3/5 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | kipclip_mini | 4/4 |
| mudler/gemma-4-26B-A4B-it-APEX-GGUF:APEX-I-Quality | llama.cpp | 49ec38e05e0c | 0adb046c1c3e+dirty | sanity | 2/2 |
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | hermes_ops | 3/3 |
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | sanity | 2/2 |
| openai/gpt-5.6-luna | api | bc97807766bc | *(predates tracking)* | kiem_mini | 1/1 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | hermes_ops | 8/8 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | kiem_mini | 1/1 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | sanity | 2/2 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 20ce58c43993+dirty | hearth_mini | 3/3 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 20ce58c43993+dirty | hermes_ops | 6/6 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 20ce58c43993+dirty | kiem_mini | 4/5 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 20ce58c43993+dirty | kipclip_mini | 3/3 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 9d8c6a3619ec+dirty | hermes_ops | 2/2 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 9d8c6a3619ec+dirty | sanity | 2/2 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | hearth_full | 2/3 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | hearth_mini | 3/3 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | hermes_ops | 5/8 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | kiem_mini | 2/5 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | kipclip_mini | 4/4 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | 0e516aa414aa | sanity | 2/2 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 40fbffd03a95 | ab5fe7ef2281 | sanity | 2/2 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | 952f3df59606 | hearth_full | 3/3 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | 952f3df59606 | hearth_mini | 3/3 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | 952f3df59606 | hermes_ops | 1/5 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | 952f3df59606 | kiem_mini | 3/5 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | 952f3df59606 | kipclip_mini | 3/4 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | b293b2de057f | hermes_ops | 1/3 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (subdir 4-bit) | mei | 9a0bccfab07b | b293b2de057f | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | hermes_ops | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0adb046c1c3e | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b | hermes_ops | 5/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b+dirty | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b+dirty | hermes_ops | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b+dirty | kiem_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 319b144e6b0b+dirty | kipclip_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | kipclip_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 9df216e99cd9 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | f51c7e72e2ad | 0adb046c1c3e+dirty | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 6642492d4afd | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 6642492d4afd | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 6642492d4afd | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 7678bd71d022 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 7678bd71d022 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 7678bd71d022 | hermes_ops | 1/6 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 7678bd71d022 | kiem_mini | 2/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 7678bd71d022 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 0a4370d3d909 | 8f1c03e85311 | hermes_ops | 5/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | hermes_ops | 12/16 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 22dac305d46e | 622d0ad7d2bd | sanity | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 3165ebcc2e95 | hermes_ops | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 3165ebcc2e95 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 3e8f2dbb5101+dirty | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 3e8f2dbb5101+dirty | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 3e8f2dbb5101+dirty | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 5720fa988c0f | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 5720fa988c0f | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 5720fa988c0f | hermes_ops | 7/7 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 5720fa988c0f | kiem_mini | 3/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | 5720fa988c0f | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | e21e81b1c0f9 | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | e21e81b1c0f9 | kiem_mini | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | e21e81b1c0f9 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 25f5a326d3b6 | ed0d851d6515 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | hermes_ops | 28/32 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 3c10e74e125a | 0d0686e785c5 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 41307afcd611 | hermes_ops | 2/7 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 41307afcd611 | sanity | 6/6 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 77d7ab43a6ee | 84e884b96aee | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 865cf72cd70a | 210be56724fd | hermes_ops | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 865cf72cd70a | 210be56724fd | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 865cf72cd70a | a5fc733bff47 | hermes_ops | 1/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | 958c5dde67bf | bb597e73b694 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 643f7007d269 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | 89f2c911aa61 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | c5171b0bd6e9 | ba5990e22812 | hermes_ops | 5/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | cef5c7989663 | d2d191e25579 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | hearth_full | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | hermes_ops | 6/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | kipclip_mini | 4/4 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | dc3e7e62a965 | b293b2de057f | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | 0620219fd55e | hermes_ops | 3/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | 0620219fd55e | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | dd3232d96137 | hermes_ops | 5/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | dd3232d96137 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | 9235ceaef852 | hermes_ops | 1/1 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | 9235ceaef852 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | bb858f72fc84 | sanity | 1/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | dd3232d96137 | hermes_ops | 5/7 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | e427e7a50b14 | *(predates tracking)* | sanity | 1/2 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | hearth_full | 3/3 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | hearth_mini | 3/3 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | hermes_ops | 4/8 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | kiem_mini | 3/5 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | kipclip_mini | 4/4 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | 9df216e99cd9 | sanity | 2/2 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | e23570ec40be | hearth_mini | 3/3 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | e23570ec40be | hermes_ops | 4/8 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | e23570ec40be | kiem_mini | 4/5 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | e23570ec40be | kipclip_mini | 3/3 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | llama.cpp | 644ba3997136 | e23570ec40be | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2152fbd9febb | e155170f4c1d | hermes_ops | 5/8 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2152fbd9febb | e155170f4c1d | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 21faf0240ec3 | *(predates tracking)* | hermes_ops | 3/3 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 21faf0240ec3 | *(predates tracking)* | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 8e85abe37e32 | *(predates tracking)* | kiem_mini | 0/1 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | *(predates tracking)* | hermes_ops | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | *(predates tracking)* | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | e155170f4c1d | hermes_ops | 7/8 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | e155170f4c1d | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 520aba6e3536 | e155170f4c1d | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 520aba6e3536 | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 73b0cf925fea | 509bd4b35f4a | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 7bceae5b4c3c | e155170f4c1d | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 7bceae5b4c3c | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | a97504c7845e | cf3789b0b88a | hermes_ops | 1/1 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | a97504c7845e | cf3789b0b88a | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | ab16f8d988bf | e0efff5679a7 | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | e155170f4c1d | hermes_ops | 5/8 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | e155170f4c1d | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | kiem_mini | 0/1 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | sanity | 2/2 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e | kiem_mini | 1/1 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | hermes_ops | 8/8 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | kiem_mini | 3/5 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | kipclip_mini | 3/4 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | 0adb046c1c3e+dirty | sanity | 2/2 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | be370d5982b4+dirty | hermes_ops | 15/16 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | 891242963db5 | be370d5982b4+dirty | sanity | 4/4 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | b17cb6e405c0 | hermes_ops | 7/8 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | b17cb6e405c0 | sanity | 2/2 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | hearth_full | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | hearth_mini | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | hermes_ops | 7/8 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | kiem_mini | 3/5 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | kipclip_mini | 3/4 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4 | sanity | 2/2 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4+dirty | hearth_full | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4+dirty | hearth_mini | 3/3 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4+dirty | kiem_mini | 3/4 |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | d6a1d4a8db43 | be370d5982b4+dirty | kipclip_mini | 3/4 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | hearth_full | 3/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | hearth_mini | 2/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | hermes_ops | 6/8 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | kiem_mini | 2/5 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | kipclip_mini | 2/4 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 3959bd7a0f56+dirty | sanity | 2/2 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | hearth_mini | 3/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | hermes_ops | 6/8 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | kiem_mini | 3/5 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | kipclip_mini | 2/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | sanity | 2/2 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 711cf4da25b3 | hearth_mini | 3/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 711cf4da25b3 | hermes_ops | 6/8 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 711cf4da25b3 | kiem_mini | 4/5 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 711cf4da25b3 | kipclip_mini | 1/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 711cf4da25b3 | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 1fea08092fdc | e155170f4c1d | hermes_ops | 5/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 1fea08092fdc | e155170f4c1d | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 1fea08092fdc | e155170f4c1d | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 840ac866adff | *(predates tracking)* | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 520355356ee0 | hearth_mini | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 520355356ee0 | hermes_ops | 6/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 520355356ee0 | kiem_mini | 2/5 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 520355356ee0 | kipclip_mini | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 520355356ee0 | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | hearth_full | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | hearth_mini | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | hermes_ops | 6/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | kiem_mini | 3/5 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | kipclip_mini | 4/4 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | 9df216e99cd9 | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | hermes_ops | 5/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | db7724641d7e | hearth_mini | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | db7724641d7e | hermes_ops | 6/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | db7724641d7e | kiem_mini | 5/5 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | db7724641d7e | kipclip_mini | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | db7724641d7e | sanity | 2/2 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | hearth_mini | 3/3 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | hermes_ops | 6/8 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | kiem_mini | 5/5 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | kipclip_mini | 2/3 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 24ac4057b970 | hermes_ops | 7/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 24ac4057b970 | kiem_mini | 1/1 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 24ac4057b970 | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 3959bd7a0f56+dirty | hearth_full | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 3959bd7a0f56+dirty | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 3959bd7a0f56+dirty | kiem_mini | 2/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | 3959bd7a0f56+dirty | kipclip_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | hearth_full | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | hermes_ops | 7/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | kiem_mini | 3/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | kipclip_mini | 4/4 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | b17cb6e405c0+dirty | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | bfdc95c44bcb | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | bfdc95c44bcb | hermes_ops | 7/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | bfdc95c44bcb | kiem_mini | 5/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | bfdc95c44bcb | kipclip_mini | 2/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 340ca3032e6c | bfdc95c44bcb | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | 3f91f24193ba | hermes_ops | 8/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | 3f91f24193ba | kiem_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | 3f91f24193ba | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | f1ff19ce062d+dirty | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | f1ff19ce062d+dirty | kiem_mini | 1/1 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 41ee296edff9 | f1ff19ce062d+dirty | kipclip_mini | 2/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | hermes_ops | 6/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | kiem_mini | 0/1 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1b3350819dae | hermes_ops | 4/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1b3350819dae | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 53a9cfb2edfe | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 53a9cfb2edfe | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 53a9cfb2edfe | kiem_mini | 4/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 53a9cfb2edfe | kipclip_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e+dirty | hearth_full | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e+dirty | hearth_mini | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e+dirty | hermes_ops | 5/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e+dirty | kiem_mini | 4/5 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 8fb930e92b1b | 0adb046c1c3e+dirty | kipclip_mini | 4/4 |

## Harness errors (excluded from every table above)

43 row(s) where the harness itself crashed (e.g. a network blip during `npm ci`, a malformed task spec) rather than the model producing a graded result — shown separately so they don't deflate pass rates or masquerade as model flakiness.

| model | engine | suite | task | grade_output (truncated) |
|---|---|---|---|---|
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-debug | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-debug | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-feature | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-feature | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-parse-note | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-rename | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-rename | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-testwrite | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-parse-note | [...truncated...] ✘ Test malformedInputThrowsRatherThanCrashingOrGuessing() failed after 0.001 seconds with 1 issue. ✘ T |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q5_K_M | llama.cpp | kipclip_mini | kipclip_mini-debug | [...truncated...] [0m[32mCheck[0m src/types.ts [0m[32mCheck[0m src/url_utils.ts [0m[32mCheck[0m tests/bookmarks |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and created repository-root src/lib.rs; result invalidated a |
| mlx-community/Qwen3.6-35B-A3B-4bit | mei | hearth_mini | hearth_mini-feature | [...truncated...]  > hearth-mini@0.1.0 test > vitest run    RUN  v2.1.9 /Users/tijs/projects/local-model-bench/runner/ru |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | hearth_full | hearth_full-feature | [...truncated...]  > hearth-full@0.1.0 test > vitest run    RUN  v2.1.9 /Users/tijs/projects/local-model-bench/runner/ru |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | kiem_mini | kiem_mini-feature | [...truncated...]      Running unittests src/lib.rs (target/debug/deps/notekeep-49d36e61ba6dd38e)      Running unittests |
| mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact | llama.cpp | kiem_mini | kiem_mini-testwrite | HARNESS ERROR: agent escaped the disposable run root and edited the benchmark checkout; source bytes were restored. == b |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-feature | [...truncated...]      Running unittests src/lib.rs (target/debug/deps/notekeep-49d36e61ba6dd38e)      Running unittests |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_full | hearth_full-debug | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_full | hearth_full-feature | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_full | hearth_full-testwrite | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_mini | hearth_mini-debug | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_mini | hearth_mini-feature | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hearth_mini | hearth_mini-testwrite | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | hermes_ops | hermes_ops-chaining | HARNESS ERROR (not a graded model result): run_prompt.py produced no parseable output |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-debug | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-debug | [...truncated...] [1/7] Write sources [4/7] Write swift-version--58304C5D6DBC2206.txt [6/9] Compiling NoteKit NoteKit.sw |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-feature | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-parse-note | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-parse-note | [...truncated...] [1/7] Write sources [4/7] Write swift-version--58304C5D6DBC2206.txt [6/9] Compiling NoteKit NoteKit.sw |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-rename | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-testwrite | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kiem_mini | kiem_mini-testwrite | HARNESS ERROR: agent escaped the disposable run root and edited the benchmark checkout; source bytes were restored. == b |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kipclip_mini | kipclip_mini-debug | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kipclip_mini | kipclip_mini-feature | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kipclip_mini | kipclip_mini-merge | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | mei | kipclip_mini | kipclip_mini-testwrite | HARNESS ERROR: hermes could not start (unknown provider 'bench-mei'); no backend request was issued, task invalidated an |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | kiem_mini | kiem_mini-feature | [...truncated...]      Running unittests src/lib.rs (target/debug/deps/notekeep-49d36e61ba6dd38e)      Running unittests |
| trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5:Q5_K_M | llama.cpp | kiem_mini | kiem_mini-feature | [...truncated...]      Running unittests src/lib.rs (target/debug/deps/notekeep-49d36e61ba6dd38e)      Running unittests |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-feature | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | kiem_mini | kiem_mini-parse-note | [...truncated...] ✘ Test run with 5 tests in 0 suites failed after 0.001 seconds with 1 issue. [0/1] Planning build Buil |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | kiem_mini | kiem_mini-rename | [...truncated...]     Finished `test` profile [unoptimized + debuginfo] target(s) in 0.62s      Running unittests src/li |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | kipclip_mini | kipclip_mini-merge | [...truncated...] [0m[32mCheck[0m src/import_merge.ts [0m[32mCheck[0m src/tag_utils.ts [0m[32mCheck[0m src/type |

## Blocked configs (marked non-viable, excluded from every table above)

Scanned directly from `configs/**/*.yaml` (`orchestration.viable: blocked`),
not from log rows — a config can be blocked before it was ever run (e.g.
a whole quant ladder ruled out once one sibling engine's live pilot showed
the model too slow to be worth testing further), so it would otherwise
vanish from this file with no trace of why.

| model | engine | config | blocked_reason |
|---|---|---|---|
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | configs/Muse-Glimmer-30B/gguf-dflash2.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.943 tok/s across 8 real trials — well under the viability cutoff. Specific to the DFlash2 speculative-decoding variant — the plain (non-speculative) config for this same model is fine (configs/Muse-Glimmer-30B/gguf.yaml, ~8.25 tok/s), so DFlash2 is actively hurting throughput here, not helping (same pattern already seen on LiquidAI-LFM2.5-8B-A1B's DSpark variant). |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q5_K_M | llama.cpp | configs/Ornith-1.5-35B-A3B/gguf-q5.yaml | Excluded from consideration 2026-09-01 -- too large for this hardware, not a fixable bug or transient issue. Server crashed during model warmup (returncode=-6/SIGABRT) on its very first forward pass. Server log: 'ggml_metal_synchronize: error: command buffer 0 failed with status 5' / 'error: Insufficient Memory (00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)' / 'GGML_ASSERT(i02 >= 0 && i02 < n_as) failed' in src/ggml-cpu/repack.cpp. This header comment's own budget estimate (~26.9GB) was too optimistic in practice -- real llama.cpp runtime compute-buffer overhead (graph allocation, batch scratch space) costs more than simple weights+KV arithmetic accounts for. Confirmed not a transient/leftover-process issue: the very next config run in the same chain (gguf-apex-i-quality.yaml, a SMALLER 21.25GB quant) launched and ran cleanly seconds later on the same machine, same code path, no cleanup steps changed in between -- the only variable was quant size. Never reached sanity; zero real benchmark data produced. |

## Retired lanes (historical evidence only — no longer runnable current paths)

The oMLX and vllm-mlx engine lanes were retired from the active comparison
surface 2026-09-04 by user decision: future local comparisons use llama.cpp
variants and Mei only. These configs are kept in place (and historical log rows
for them remain visible in every table above) as reproducible evidence, but
`orchestration.viable: retired` means the runner skips them — they are not
advertised as runnable current paths.

| engine | models (retired configs) | expansion |
|---|---|---|
| omlx | 18 configs | configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx-hot.yaml; configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx-ssd.yaml; configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx.yaml; configs/Laguna-XS-2.1/omlx.yaml; configs/LiquidAI-LFM2.5-2.6B/omlx.yaml; configs/LiquidAI-LFM2.5-8B-A1B/omlx.yaml; configs/Ornith-1.5-9B-oQ4e-fp16/omlx-hot.yaml; configs/Ornith-1.5-9B-oQ4e-fp16/omlx-ssd.yaml; configs/Ornith-1.5-9B-oQ4e-fp16/omlx.yaml; configs/Qwen3-Coder-30B-A3B/omlx.yaml; configs/Qwen3.8-27B/omlx.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-context-balanced.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-hot.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp-xhigh.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-ssd.yaml; configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx.yaml; configs/Ternary-Bonsai-27B/omlx.yaml |
| vllm-mlx | 12 configs | configs/Devstral-Small-2507/mlx.yaml; configs/Laguna-XS-2.1/mlx.yaml; configs/LiquidAI-LFM2.5-2.6B/mlx-8bit.yaml; configs/LiquidAI-LFM2.5-2.6B/mlx.yaml; configs/LiquidAI-LFM2.5-8B-A1B/mlx-8bit.yaml; configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml; configs/Ornith-1.5-35B-A3B/mlx.yaml; configs/Ornith-1.5-9B/mlx.yaml; configs/Qwen2.5-Coder-14B/mlx.yaml; configs/Qwen3-Coder-30B-A3B/mlx.yaml; configs/Qwen3.8-27B/mlx.yaml; configs/Ternary-Bonsai-27B/mlx.yaml |

## Speed-gated configs (stopped early — too slow to be practical)

`run_bench.py` runs a config's full hermes_ops suite as normal, then checks
the average tokens_per_second across every task it just ran — the same
number the main table's `avg tok/s` column reports. Below threshold, it
skips the coding suite (typically far more expensive: real builds +
multi-turn agentic loops) rather than spend that time confirming an outcome
hermes_ops already answered. The hermes_ops rows themselves ARE still real
log.jsonl rows (visible in every table above) — this section just makes the
*reason the coding suite didn't run* explicit rather than something a reader
has to infer from a config missing coding rows.

| model | engine | config | avg tok/s | per-task tok/s | threshold | timestamp |
|---|---|---|---|---|---|---|
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | /Users/tijs/projects/local-model-bench/configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx.yaml | 9.62 | 6.86, 11.06, 3.06, 7.40, 10.63, 21.83, 7.00, 9.09 | 10.0 | 2026-08-22T20:08:16Z |
| mlx-community/Laguna-XS-2.1-4bit | omlx | /Users/tijs/projects/local-model-bench/configs/Laguna-XS-2.1/omlx.yaml | 2.13 | 1.83, 1.12, 0.79, 1.32, 1.61, 2.05, 1.47, 6.89 | 10.0 | 2026-08-22T21:48:59Z |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | /Users/tijs/projects/local-model-bench/configs/LiquidAI-LFM2.5-2.6B/omlx.yaml | 9.66 | 6.45, 6.54, 3.91, 16.51, 8.50, 6.88, 11.51, 16.98 | 10.0 | 2026-08-22T22:57:35Z |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | /Users/tijs/projects/local-model-bench/configs/LiquidAI-LFM2.5-8B-A1B/omlx.yaml | 9.13 | 3.82, 8.50, 5.71, 6.32, 6.14, 15.85, 12.92, 13.76 | 10.0 | 2026-08-22T23:20:34Z |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | /Users/tijs/projects/local-model-bench/configs/Ornith-1.5-9B-oQ4e-fp16/omlx.yaml | 3.85 | 1.59, 1.97, 1.82, 3.93, 3.84, 2.32, 1.39, 13.94 | 10.0 | 2026-08-23T00:53:36Z |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | /Users/tijs/projects/local-model-bench/configs/Qwen3-Coder-30B-A3B/omlx.yaml | 0.75 | 0.21, 0.52, 0.86, 0.70, 0.41, 0.51, 0.37, 2.40 | 10.0 | 2026-08-23T02:10:35Z |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | /Users/tijs/projects/local-model-bench/configs/Qwen3.8-27B-Ridge/gguf.yaml | 5.82 | 3.27, 4.84, 6.54, 5.17, 6.42, 6.64, 6.84, 6.85 | 10.0 | 2026-08-23T02:30:20Z |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | /Users/tijs/projects/local-model-bench/configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp.yaml | 0.01 | 0.01, 0.00, 0.01, 0.00, 0.01, 0.01, 0.01, 0.01 | 10.0 | 2026-08-23T02:48:03Z |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | /Users/tijs/projects/local-model-bench/configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx.yaml | 0.01 | 0.01, 0.01, 0.01, 0.02, 0.02, 0.01, 0.01, 0.01 | 10.0 | 2026-08-23T03:07:12Z |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | /Users/tijs/projects/local-model-bench/configs/Ternary-Bonsai-27B/mlx.yaml | 0.67 | 0.27, 0.39, 0.25, 0.74, 0.75, 1.01, 0.35, 1.60 | 10.0 | 2026-08-23T05:25:12Z |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | /Users/tijs/projects/local-model-bench/configs/Ternary-Bonsai-27B/omlx.yaml | 0.63 | 0.24, 0.27, 0.36, 0.51, 0.72, 0.85, 0.37, 1.69 | 10.0 | 2026-08-23T09:17:32Z |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | configs/Muse-Glimmer-30B/gguf.yaml | 8.25 | 0.51, 9.00, 9.87, 9.32, 7.88, 9.07, 10.02, 10.33 | 10.0 | 2026-08-23T10:12:13Z |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | configs/Ornith-1.5-9B/mlx.yaml | 2.29 | 0.90, 0.73, 1.11, 2.12, 1.53, 3.66, 1.29, 6.94 | 10.0 | 2026-08-23T12:58:09Z |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | configs/Ornith-1.5-35B-A3B/mlx.yaml | 3.32 | 0.95, 1.72, 2.02, 0.99, 4.69, 3.55, 2.11, 10.52 | 4.0 | 2026-08-23T13:26:02Z |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | configs/Ornith-1.5-35B-A3B/mlx.yaml | 3.10 | 0.95, 1.72, 2.20, 0.90, 4.35, 2.59, 1.57, 10.52 | 4.0 | 2026-08-24T23:00:20Z |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | vllm-mlx | configs/Qwen3-Coder-30B-A3B/mlx.yaml | 0.68 | 0.22, 0.49, 0.58, 0.64, 0.54, 0.52, 0.48, 2.01 | 4.0 | 2026-08-25T00:08:49Z |
| mlx-community/Qwen3.8-27B-4bit | omlx | configs/Qwen3.8-27B/omlx.yaml | 0.01 | 0.00, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01 | 4.0 | 2026-08-25T07:28:30Z |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | configs/Gemma-4-26B-A4B/mei.yaml | 2.00 | 0.67, 1.08, 2.10, 1.54, 0.80, 0.17, 2.21, 7.44 | 4.0 | 2026-09-04T14:56:21Z |
| mlx-community/gemma-4-26b-a4b-it-4bit | mei | configs/Gemma-4-26B-A4B/mei.yaml | 2.01 | 0.68, 1.07, 2.12, 1.55, 0.80, 0.17, 2.25, 7.44 | 4.0 | 2026-09-05T10:20:48Z |
| mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit | mei | configs/NVIDIA-Nemotron-3.5-Lightning-30B-A3B/mei.yaml | 1.02 | 0.64, 0.31, 0.07, 0.27, 4.09, 0.27, 1.73, 0.78 | 4.0 | 2026-09-06T16:46:20Z |
| AtomicChat/Laguna-XS-2.1-MLX-5bit | mei | configs/Laguna-XS-2.1/mei.yaml | 0.94 | 1.06, 1.00, 0.33, 0.78, 1.80, 0.64, 0.42, 1.49 | 4.0 | 2026-09-09T09:25:15Z |

# Leaderboard

Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not
hand-edit rows below, edit the log and regenerate instead.

> **⚠ 138/1116 rows below predate 2026-08-21
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

**`avg tok/s` caveat**:
this is `completion_tokens / wall_seconds` across the ENTIRE multi-turn
loop, including every prefill of the suite's system prompt — it's a
prefill-dominated-workload throughput number, not a pure decode rate, and
it's averaged across `sanity` (tiny prompt) and `hermes_ops` (large,
repeated system prompt) rows in one cell. Treat it as a rough signal,
not a precise generation-speed comparison; a real prefill/decode split
is a follow-up, not yet implemented. `avg TTFT` is blanked instead of
silently mislabeled for proxied configs (see below), but is still a
single combined average across suites where it IS real.

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

| model | engine | quant | temp (coding only)¹ | reasoning | sanity gate⁴ | config | runner | tasks | pass rate⁴ | slow passes² | avg tok/s | avg TTFT (s) | hallucinated tools⁵ | avg coding turns³ | coding tool errors³ | peak RSS (GB) | quant family | cache | MTP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | 2/2 | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) | 5fc289161e34 | 8 | 75% | 0 | 30.1 | 7.05 | 0 | — | 0 | 23.1 | — | — | — |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | — | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) | 8e7b1897f7e8+dirty | 11 | 91% | 1 | — | — | 0 | — | 0 | 23.8 | — | — | — |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | — | 0.6 | thinking | — | [6fa6f52fdc56](configs/6fa6f52fdc56.yaml) | d39c9c37bb8c+dirty | 0 | n/a (all harness errors) | 0 | — | — | 0 | — | 0 | — | — | — | — |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [3a740261a79c](configs/3a740261a79c.yaml) | a04f5cd07f20 | 19 | 84% | 13 | 8.0 | 44.53 | 0 | — | 0 | 22.6 | — | — | — |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | xhigh | 2/2 | [3618a30940bc](configs/3618a30940bc.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 9.6 | 4.90 | 0 | — | 0 | 6.2 | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | xhigh | 2/2 | [3618a30940bc](configs/3618a30940bc.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 9.0 | 4.15 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [6f8f1c7b8d48](configs/6f8f1c7b8d48.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 10.4 | 3.52 | 0 | — | 0 | 8.0 | oQ4e-fp16 mixed precision + MTP tensors | ssd | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [6f8f1c7b8d48](configs/6f8f1c7b8d48.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 11.0 | 3.67 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | ssd | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [a7867bea182c](configs/a7867bea182c.yaml) — *config since changed* | e155170f4c1d | 8 | 0% | 0 | 1.9 | 3.84 | 0 | — | 0 | 6.9 | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [a7867bea182c](configs/a7867bea182c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 5 | 0% | 0 | 3.9 | 3.68 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [b6112a82c243](configs/b6112a82c243.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 10.5 | 3.52 | 0 | — | 0 | 6.6 | oQ4e-fp16 mixed precision + MTP tensors | hot | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [b6112a82c243](configs/b6112a82c243.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 10.6 | 3.50 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | hot | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [b7b32d0eb150](configs/b7b32d0eb150.yaml) — *config since changed* | e155170f4c1d | 8 | 0% | 0 | 2.1 | 3.52 | 0 | — | 0 | 7.0 | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [b7b32d0eb150](configs/b7b32d0eb150.yaml) — *config since changed* | fc71ba2c66f8+dirty | 4 | 0% | 0 | 4.4 | 3.50 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [f9648093327f](configs/f9648093327f.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 10.9 | 3.51 | 0 | — | 0 | 6.4 | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | 2/2 | [f9648093327f](configs/f9648093327f.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 11.0 | 3.49 | 0 | — | 0 | — | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 2c7b7c47693c | 3 | 100% | 0 | 41.9 | 6.40 | 0 | — | 0 | 7.2 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | — | [26670d622de5](configs/26670d622de5.yaml) | 2c7b7c47693c+dirty | 4 | 100% | 0 | 47.0 | 2.30 | 0 | — | 0 | 7.2 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 314e422cc5ac | 9 | 56% | 0 | 44.5 | 4.37 | 1 | — | 0 | 7.6 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 6a6b4bcf6907 | 9 | 56% | 0 | 44.6 | 4.36 | 1 | — | 0 | 7.6 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | 2/2 | [26670d622de5](configs/26670d622de5.yaml) | 937328228de2 | 9 | 89% | 1 | 44.5 | 4.37 | 1 | 38.0 | 7 | 8.0 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:BF16 | llama.cpp | — | 0.1 | n/a | — | [26670d622de5](configs/26670d622de5.yaml) | c30b4df69e53 | 12 | 33% | 2 | 47.0 | 2.38 | 1 | 23.5 | 57 | 10.4 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | — | [011816a7d0df](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | 0.1 | n/a | 2/2 | [1d65d14c63a8](configs/1d65d14c63a8.yaml) — *config since changed* | 3182238013a3 | 9 | 11% | 0 | 32.8 | 6.50 | 0 | — | 0 | 4.8 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | 2/2 | [aa5d02c11bba](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 55.8 | 5.54 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | — | 0.1 | n/a | 2/2 | [0840d8e3ee87](configs/0840d8e3ee87.yaml) | 5f0b7d975f67 | 9 | 56% | 0 | 62.5 | 3.77 | 1 | — | 0 | 5.8 | — | — | — |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | — | 0.1 | n/a | 2/2 | [0840d8e3ee87](configs/0840d8e3ee87.yaml) | fa0046f3b929 | 19 | 58% | 2 | 62.6 | 3.77 | 1 | 23.8 | 43 | 8.0 | — | — | — |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | — | [57734ec83d1b](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | 2/2 | [8dd47a586509](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 0 | 1.6 | 13.67 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | 2/2 | [a03394d84d27](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 1.7 | 15.56 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | 2/2 | [b2dc92c2ed56](configs/b2dc92c2ed56.yaml) — *config since changed* | 65bb6d23192e | 8 | 75% | 1 | 18.9 | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.7 | — | — | — |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | — | [b2dc92c2ed56](configs/b2dc92c2ed56.yaml) — *config since changed* | 65bb6d23192e+dirty | 1 | 0% | 0 | — | — | 0 | — | 0 | 5.8 | — | — | — |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | 2/2 | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | 65bb6d23192e+dirty | 0 | n/a (all harness errors) | 0 | 44.8 | 1.39 | 0 | — | 0 | 5.5 | BF16 | cold | off |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | — | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 0 | 9.7 | 23.25 | 1 | — | 0 | 5.5 | BF16 | cold | off |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | 2/2 | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 67% | 0 | 21.1 | 13.93 | 0 | — | 0 | — | BF16 | cold | off |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | 2/2 | [6be3287df228](configs/6be3287df228.yaml) | e0571a8c6ad8 | 5 | 80% | 1 | 18.0 | 16.74 | 0 | — | 0 | 5.5 | BF16 | cold | off |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | — | 0.1 | n/a | 2/2 | [c1a7fd5d3135](configs/c1a7fd5d3135.yaml) | 937328228de2 | 1 | 100% | 0 | 35.1 | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.7 | — | — | — |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | — | 0.1 | n/a | 2/2 | [c1a7fd5d3135](configs/c1a7fd5d3135.yaml) | c32555007281 | 9 | 78% | 2 | 19.3 | n/a (proxied — not real TTFT) | 0 | — | 0 | 5.8 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | 1370f3a3609d | 9 | 56% | 0 | 55.4 | 4.17 | 0 | — | 0 | 17.1 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | 6a6b4bcf6907 | 9 | 56% | 0 | 55.7 | 4.16 | 0 | — | 0 | 16.8 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | 0.2 | n/a | 2/2 | [a148c29637e6](configs/a148c29637e6.yaml) | a5743c4a242c | 19 | 32% | 0 | 55.3 | 4.16 | 0 | 12.1 | 36 | 18.8 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | 2/2 | [303eba1d5495](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 61.4 | 5.03 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | 0.2 | n/a | 2/2 | [5f50ca6ebdf3](configs/5f50ca6ebdf3.yaml) — *config since changed* | 3182238013a3 | 9 | 56% | 0 | 66.7 | 3.54 | 1 | — | 0 | 9.5 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | — | [f4620fe8538d](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | — | 0.2 | n/a | 2/2 | [05a5098cf4c6](configs/05a5098cf4c6.yaml) | 13be39c4b506 | 19 | 32% | 0 | 67.6 | 3.52 | 1 | 5.1 | 12 | 11.3 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | — | 0.2 | n/a | 2/2 | [05a5098cf4c6](configs/05a5098cf4c6.yaml) | 50298bcbe02d | 19 | 32% | 0 | 66.4 | 3.55 | 1 | — | 0 | 11.4 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | — | ? | ? | 2/2 | [85636a621ce0](configs/LiquidAI-LFM2.5-8B-A1B/gguf-dspark.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0 | 29.3 | 8.69 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | — | 0.2 | n/a | 2/2 | [f6bb65acb160](configs/f6bb65acb160.yaml) — *config since changed* | 3182238013a3 | 9 | 67% | 0 | 27.0 | 7.47 | 1 | — | 0 | 13.7 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | — | 0.2 | n/a | 2/2 | [4f8641aa7094](configs/4f8641aa7094.yaml) — *config since changed* | f12e3bae97e9 | 9 | 67% | 0 | 26.9 | 7.48 | 1 | — | 0 | 13.8 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | — | [5fd02e54bb9d](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | 2/2 | [b9bea7cd700c](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 2.4 | 11.62 | 0 | — | 0 | — | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | 0.2 | n/a | 2/2 | [da00492c3b46](configs/da00492c3b46.yaml) — *config since changed* | e155170f4c1d | 9 | 56% | 0 | 21.4 | n/a (proxied — not real TTFT) | 0 | — | 0 | 10.2 | — | — | — |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | 2/2 | [e9ea1ba1fe73](configs/e9ea1ba1fe73.yaml) | 3db0c69f5007 | 8 | 62% | 0 | 19.5 | 13.04 | 0 | — | 0 | 3.4 | BF16 | cold | off |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | 2/2 | [f3b91883da61](configs/f3b91883da61.yaml) — *config since changed* | e155170f4c1d | 8 | 75% | 0 | 19.5 | 13.26 | 0 | — | 0 | 12.2 | BF16 | cold | off |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | 2/2 | [f3b91883da61](configs/f3b91883da61.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 100% | 0 | 28.7 | 10.51 | 0 | — | 0 | — | BF16 | cold | off |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | — | 0.2 | n/a | 2/2 | [9693319bc3a1](configs/9693319bc3a1.yaml) | 798e2f07f493 | 9 | 67% | 0 | 20.7 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.5 | — | — | — |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [00fc47aef271](configs/00fc47aef271.yaml) — *config since changed* | 65bb6d23192e | 8 | 75% | 0 | 26.1 | 13.02 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | cold | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 4/4 | [00fc47aef271](configs/00fc47aef271.yaml) — *config since changed* | fc71ba2c66f8+dirty | 9 | 44% | 0 | 42.3 | 9.97 | 0 | — | 0 | — | oQ4-fp16 mixed precision | cold | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [8c159510d3a5](configs/8c159510d3a5.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | 98.2 | 1.05 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | ssd | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [8c159510d3a5](configs/8c159510d3a5.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 89.9 | 0.81 | 0 | — | 0 | — | oQ4-fp16 mixed precision | ssd | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [b060a851140f](configs/b060a851140f.yaml) | a19512e1c13a | 0 | n/a (all harness errors) | 0 | 85.2 | 0.71 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | hot | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [b4a63fbb6a67](configs/b4a63fbb6a67.yaml) | d0165994ca07 | 9 | 67% | 0 | 25.3 | 13.05 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | cold | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [c1ed322cee8c](configs/c1ed322cee8c.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | 92.7 | 0.99 | 0 | — | 0 | 5.1 | oQ4-fp16 mixed precision | hot | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | 2/2 | [c1ed322cee8c](configs/c1ed322cee8c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 105.5 | 1.57 | 0 | — | 0 | — | oQ4-fp16 mixed precision | hot | off |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | 2/2 | [3f3368f78d8d](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 7.7 | 58.80 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | 2/2 | [413f324b943c](configs/413f324b943c.yaml) — *config since changed* | 3182238013a3 | 8 | 50% | 1 | 8.5 | 35.49 | 0 | — | 0 | 21.2 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | 2/2 | [b0b30ac444da](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 50% | 0 | 8.0 | 57.94 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | 141399e74bd0 | 19 | 74% | 10 | 8.5 | 35.50 | 0 | 28.1 | 23 | 22.2 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [38ccea45c281](configs/38ccea45c281.yaml) | cf45f7655a7c | 19 | 63% | 9 | 8.5 | 35.47 | 0 | — | 0 | 21.8 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | 1.0 | thinking | 2/2 | [5e61e8c02089](configs/5e61e8c02089.yaml) — *config since changed* | 3182238013a3 | 1 | 100% | 0 | 7.2 | 89.00 | 0 | — | 0 | 23.4 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | 1.0 | thinking | — | [5e61e8c02089](configs/5e61e8c02089.yaml) — *config since changed* | 3182238013a3+dirty | 7 | 0% | 0 | 3.0 | 27.90 | 0 | — | 0 | 23.2 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | ? | ? | 2/2 | [fd29e9c067f8](configs/Muse-Glimmer-30B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 33% | 0 | 8.3 | 64.61 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | — | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 0ca55f47516d | 8 | 12% | 0 | 0.9 | 140.09 | 0 | — | 0 | 23.6 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | 1/1 | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 1ab13d3b7d57 | 0 | n/a (all harness errors) | 0 | 12.0 | 8.18 | 0 | — | 0 | 22.3 | — | — | — |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | — | 1.0 | thinking | 1/1 | [17768c195364](configs/17768c195364.yaml) — *config since changed* | 1ab13d3b7d57+dirty | 0 | n/a (all harness errors) | 0 | 9.2 | 14.39 | 0 | — | 0 | 22.9 | — | — | — |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | n/a | 1/2 | [0a014488283a](configs/0a014488283a.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 9.2 | 0.79 | 0 | — | 0 | 20.5 | — | — | — |
| bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | n/a | 1/2 | [e54758f4db2f](configs/e54758f4db2f.yaml) | 97f629ff59e1 | 0 | n/a (all harness errors) | 0 | 10.4 | 0.72 | 0 | — | 0 | 20.4 | — | — | — |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | 2/2 | [e6a0628476cc](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 7.8 | 8.98 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | 4/4 | [f6397d624011](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 6.2 | 52.74 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | Q4_K_M+DFlash2 | ? | ? | 2/2 | [0686abeab746](configs/Qwen3.8-27B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 5.8 | 55.96 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [c02615b57f21](configs/c02615b57f21.yaml) — *config since changed* | 9756e52a1739 | 19 | 84% | 11 | 7.9 | 38.00 | 0 | — | 0 | 23.7 | — | — | — |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [c7eb832ac1e8](configs/c7eb832ac1e8.yaml) — *config since changed* | 8bf29fca2f15 | 19 | 79% | 12 | 5.2 | 63.62 | 0 | — | 0 | 23.6 | — | — | — |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | 2/2 | [163fa63ffb83](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 20.2 | 15.45 | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | — | [29ed581f7054](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | 2e56f8121142 | 9 | 67% | 0 | 21.0 | 9.34 | 0 | — | 0 | 13.7 | — | — | — |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | 0.6 | thinking | 2/2 | [a2d241742068](configs/a2d241742068.yaml) | c8d9bde5c6d6 | 19 | 68% | 3 | 20.9 | 9.34 | 0 | 20.9 | 29 | 22.1 | — | — | — |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | ? | ? | 2/2 | [6a3700901e2b](configs/Qwen3.8-27B-Ridge/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 50% | 0 | 4.6 | 52.03 | 0 | — | 0 | — | ? | ? | ? |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | 0.7 | instruct | 2/2 | [d135df9d860f](configs/d135df9d860f.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 0 | 5.5 | 30.15 | 0 | — | 0 | 18.9 | — | — | — |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | — | 0.7 | instruct | 2/2 | [7b1d82c8abab](configs/7b1d82c8abab.yaml) — *config since changed* | a58bee1684ac | 19 | 84% | 8 | 5.5 | 30.14 | 0 | — | 0 | 20.8 | — | — | — |
| gpt-5.6-luna | api | — | ? | ? | — | [86cbe69b94ae](configs/Luna/api.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| gpt-5.6-luna | api | — | None | unspecified | — | [dc55dd82a2c3](configs/dc55dd82a2c3.yaml) — *config since changed* | e155170f4c1d | 1 | 0% | 0 | — | — | 0 | — | 0 | — | — | — | — |
| mlx-community/Devstral-Small-2507-4bit-DWQ | mlx | — | 0.15 | n/a | 1/2 | [54b39a32dd69](configs/54b39a32dd69.yaml) — *config since changed* | 65bb6d23192e | 0 | n/a (all harness errors) | 0 | 6.9 | 9.13 | 0 | — | 0 | 8.7 | — | — | — |
| mlx-community/Devstral-Small-2507-4bit-DWQ | vllm-mlx | — | 0.15 | n/a | 1/2 | [8d60440a81e5](configs/8d60440a81e5.yaml) | 8aec9f8f6135 | 0 | n/a (all harness errors) | 0 | 7.0 | 9.13 | 0 | — | 0 | 10.4 | — | — | — |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | — | 0.1 | n/a | 0/2 | [662a015ba0e6](configs/662a015ba0e6.yaml) | 4f0aad77c3ab | 0 | n/a (all harness errors) | 0 | 0.0 | n/a (proxied — not real TTFT) | 0 | — | 0 | 0.8 | — | — | — |
| mlx-community/LFM2.5-2.6B-8bit | vllm-mlx | — | 0.1 | n/a | 0/2 | [662a015ba0e6](configs/662a015ba0e6.yaml) | 6a6b4bcf6907 | 0 | n/a (all harness errors) | 0 | 0.0 | n/a (proxied — not real TTFT) | 0 | — | 0 | 0.8 | — | — | — |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | mlx | — | 0.2 | n/a | 1/2 | [509fe12b4b1a](configs/509fe12b4b1a.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 99.4 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | 2/2 | [00878f13621f](configs/00878f13621f.yaml) | 6a6b4bcf6907 | 9 | 56% | 0 | 26.4 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | 1/2 | [00878f13621f](configs/00878f13621f.yaml) | dd3232d96137 | 0 | n/a (all harness errors) | 0 | 98.9 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.0 | — | — | — |
| mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 0.2 | n/a | 2/2 | [00878f13621f](configs/00878f13621f.yaml) | e9a7e8ddd7d5 | 9 | 67% | 0 | 24.5 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.1 | — | — | — |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | 2/2 | [9f649cd3051f](configs/9f649cd3051f.yaml) | 9f1a9e467900 | 3 | 67% | 1 | 18.7 | 44.10 | 1 | — | 0 | 3.6 | MLX 4-bit | cold | off |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | 2/2 | [f1037eaa5995](configs/f1037eaa5995.yaml) — *config since changed* | 65bb6d23192e | 8 | 50% | 1 | 11.0 | 56.95 | 2 | — | 0 | 4.0 | MLX 4-bit | cold | off |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | 2/2 | [f1037eaa5995](configs/f1037eaa5995.yaml) — *config since changed* | fc71ba2c66f8+dirty | 5 | 40% | 0 | 18.8 | 42.82 | 1 | — | 0 | — | MLX 4-bit | cold | off |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | mlx | — | 0.7 | n/a | 1/2 | [c6d10ac83efc](configs/c6d10ac83efc.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 10.9 | 0.76 | 0 | — | 0 | 10.0 | — | — | — |
| mlx-community/Qwen2.5-Coder-14B-Instruct-4bit | vllm-mlx | — | 0.7 | n/a | 1/2 | [389d88115d2d](configs/389d88115d2d.yaml) | 3bca29f0ff7c | 0 | n/a (all harness errors) | 0 | 11.0 | 0.75 | 0 | — | 0 | 8.3 | — | — | — |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | 0.7 | instruct | 2/2 | [5e09e98f8c60](configs/5e09e98f8c60.yaml) — *config since changed* | e155170f4c1d | 9 | 67% | 0 | 12.9 | n/a (proxied — not real TTFT) | 0 | — | 0 | 9.7 | — | — | — |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | 2/2 | [8b3cbca5d1b1](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 67% | 0 | 4.6 | 22.76 | 0 | — | 0 | — | ? | ? | ? |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | — | [92c4b9be230e](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | — | 0.7 | instruct | 2/2 | [08e51e50397d](configs/08e51e50397d.yaml) — *config since changed* | e155170f4c1d | 8 | 12% | 0 | 2.9 | 79.16 | 0 | — | 0 | 11.5 | MLX 4-bit | cold | off |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | — | 0.7 | instruct | 1/2 | [08e51e50397d](configs/08e51e50397d.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 13.1 | 0.80 | 0 | — | 0 | — | MLX 4-bit | cold | off |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | vllm-mlx | — | 0.7 | instruct | 2/2 | [fe9f7a44a702](configs/fe9f7a44a702.yaml) | c17e058823c1 | 8 | 75% | 4 | 2.9 | n/a (proxied — not real TTFT) | 0 | — | 0 | 7.2 | — | — | — |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | 2/2 | [152424abaa13](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 3.1 | 198.83 | 0 | — | 0 | — | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | 1.0 | thinking | 2/2 | [968652aede2d](configs/968652aede2d.yaml) — *config since changed* | 69e4b1fd937f | 3 | 67% | 2 | 3.6 | 198.67 | 1 | — | 0 | 1.6 | — | — | — |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | 2/2 | [bbaa3dfa1953](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 0 | n/a (all harness errors) | 0 | 8.6 | 3.76 | 0 | — | 0 | — | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | — | [f894953f1f80](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0 | 0.3 | 337.71 | 0 | — | 0 | — | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | omlx | — | 1.0 | thinking | 2/2 | [1eec0081c5d6](configs/1eec0081c5d6.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 0% | 0 | 3.4 | 5.65 | 0 | — | 0 | — | MLX 4-bit | cold | off |
| mlx-community/Qwen3.8-27B-4bit | omlx | — | 1.0 | thinking | 2/2 | [3fbfdcc4ec02](configs/3fbfdcc4ec02.yaml) | 24d38de98cb4 | 8 | 0% | 0 | 1.7 | 4.97 | 0 | — | 0 | 9.1 | MLX 4-bit | cold | off |
| openai/gpt-5.6-luna | api | — | ? | ? | 2/2 | [1f7b55bd4401](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 15.2 | 4.30 | 0 | — | 0 | — | ? | ? | ? |
| openai/gpt-5.6-luna | api | — | ? | ? | — | [bc97807766bc](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| openai/gpt-5.6-luna | openrouter | — | None | unspecified | 2/2 | [f1e3043189f3](configs/f1e3043189f3.yaml) | 1e67356823c2 | 9 | 100% | 0 | 35.5 | 4.80 | 0 | — | 0 | — | — | — | — |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | ? | ? | 2/2 | [3047922de5b7](configs/Ornith-1.5-35B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 34.7 | 1.90 | 0 | — | 0 | — | ? | ? | ? |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) | 0b3a2a523049 | 9 | 89% | 0 | 31.0 | 6.96 | 0 | — | 0 | 22.8 | — | — | — |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 0.6 | unspecified | 2/2 | [48d75180adbc](configs/48d75180adbc.yaml) | 6cc8b646db2e | 19 | 95% | 2 | 30.9 | 6.96 | 0 | 17.7 | 20 | 23.9 | — | — | — |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | — | 0.6 | unspecified | 2/2 | [76414c6ab37c](configs/76414c6ab37c.yaml) | 0620219fd55e | 8 | 38% | 0 | 10.2 | 41.53 | 2 | — | 0 | 2.1 | — | — | — |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | — | 0.6 | unspecified | 2/2 | [76414c6ab37c](configs/76414c6ab37c.yaml) | dd3232d96137 | 8 | 62% | 1 | 10.5 | 41.50 | 2 | — | 0 | 2.4 | — | — | — |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | 2/2 | [d0d250e59d4e](configs/d0d250e59d4e.yaml) | 9235ceaef852 | 1 | 100% | 0 | 20.0 | 31.46 | 0 | — | 0 | 8.2 | — | — | — |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | 1/2 | [d0d250e59d4e](configs/d0d250e59d4e.yaml) | bb858f72fc84 | 0 | n/a (all harness errors) | 0 | 25.9 | 1.11 | 0 | — | 0 | 0.7 | — | — | — |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | — | 0.7 | instruct | — | [d0d250e59d4e](configs/d0d250e59d4e.yaml) | dd3232d96137 | 7 | 71% | 4 | 2.5 | 92.83 | 0 | — | 0 | 5.5 | — | — | — |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | — | ? | ? | 1/2 | [e427e7a50b14](configs/Laguna-XS-2.1/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 0 | n/a (all harness errors) | 0 | 0.1 | 11.96 | 0 | — | 0 | — | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | 0.7 | unspecified | 2/2 | [2152fbd9febb](configs/2152fbd9febb.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 4 | 4.1 | 155.61 | 1 | — | 0 | 7.8 | — | — | — |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | ? | ? | — | [8e85abe37e32](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | 2/2 | [21faf0240ec3](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 7.0 | 117.18 | 0 | — | 0 | — | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | 2/2 | [c2576cd6b385](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 0 | 9.0 | 97.84 | 0 | — | 0 | — | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | — | 0.7 | unspecified | 2/2 | [40462ce69e01](configs/40462ce69e01.yaml) — *config since changed* | e155170f4c1d | 8 | 88% | 6 | 4.5 | 162.80 | 0 | — | 0 | 8.7 | native ternary 2-bit | cold | off |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | — | 0.7 | unspecified | 2/2 | [40462ce69e01](configs/40462ce69e01.yaml) — *config since changed* | fc71ba2c66f8+dirty | 3 | 100% | 0 | 6.6 | 119.62 | 0 | — | 0 | — | native ternary 2-bit | cold | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [520aba6e3536](configs/520aba6e3536.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 32.3 | 1.38 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | ssd | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [520aba6e3536](configs/520aba6e3536.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 32.8 | 1.38 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | ssd | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [73b0cf925fea](configs/73b0cf925fea.yaml) | 509bd4b35f4a | 0 | n/a (all harness errors) | 0 | 32.0 | 1.26 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | hot | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [7bceae5b4c3c](configs/7bceae5b4c3c.yaml) — *config since changed* | e155170f4c1d | 0 | n/a (all harness errors) | 0 | 33.1 | 1.39 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | hot | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [7bceae5b4c3c](configs/7bceae5b4c3c.yaml) — *config since changed* | fc71ba2c66f8+dirty | 0 | n/a (all harness errors) | 0 | 32.3 | 1.38 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | hot | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [a97504c7845e](configs/a97504c7845e.yaml) | cf3789b0b88a | 1 | 100% | 1 | 22.4 | 19.60 | 0 | — | 0 | 7.3 | oQ4e-fp16 mixed precision | cold | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [ab16f8d988bf](configs/ab16f8d988bf.yaml) | e0efff5679a7 | 0 | n/a (all harness errors) | 0 | 33.0 | 1.26 | 0 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | ssd | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [afecbd0a9f5f](configs/afecbd0a9f5f.yaml) — *config since changed* | e155170f4c1d | 8 | 62% | 3 | 9.4 | 46.77 | 2 | — | 0 | 7.2 | oQ4e-fp16 mixed precision | cold | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | 2/2 | [afecbd0a9f5f](configs/afecbd0a9f5f.yaml) — *config since changed* | fc71ba2c66f8+dirty | 4 | 75% | 0 | 13.9 | 35.28 | 0 | — | 0 | — | oQ4e-fp16 mixed precision | cold | off |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | 0.15 | n/a | 2/2 | [ffa862c18cff](configs/ffa862c18cff.yaml) | 63c1cbdae938 | 19 | 74% | 6 | 7.7 | 28.07 | 0 | 19.8 | 27 | 27.0 | — | — | — |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | instruct | 2/2 | [1fea08092fdc](configs/1fea08092fdc.yaml) — *config since changed* | e155170f4c1d | 9 | 67% | 0 | 20.8 | 9.51 | 1 | — | 0 | 23.9 | — | — | — |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | — | [840ac866adff](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | 0 | — | ? | ? | ? |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | 2/2 | [fe085c7fef30](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 18.0 | 18.49 | 0 | — | 0 | — | ? | ? | ? |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | 2/2 | [644415678c37](configs/644415678c37.yaml) | 520355356ee0 | 19 | 74% | 2 | 20.8 | 9.50 | 1 | 29.5 | 50 | 24.5 | — | — | — |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 0.7 | instruct | 2/2 | [644415678c37](configs/644415678c37.yaml) | bf1cd0ed7a6f | 9 | 67% | 1 | 20.9 | 9.51 | 1 | — | 0 | 23.4 | — | — | — |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | — | 0.6 | thinking | 2/2 | [436d6d25d30c](configs/436d6d25d30c.yaml) — *config since changed* | 8d4f1f85f106 | 19 | 84% | 3 | 27.1 | 7.47 | 0 | — | 0 | 24.2 | — | — | — |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | UD-Q2_K_XL | ? | ? | 2/2 | [2233edb1c4f2](configs/Qwen3.8-27B/gguf-unsloth-ud-q2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 6.3 | 55.08 | 0 | — | 0 | — | ? | ? | ? |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | — | ? | ? | 2/2 | [89f4d8d04793](configs/Qwen3.8-27B/gguf-unsloth-ud-q4.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 3 | 100% | 0 | 6.4 | 55.57 | 0 | — | 0 | — | ? | ? | ? |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 1.0 | thinking | 2/2 | [6d148ccbfd2e](configs/6d148ccbfd2e.yaml) | 1166272411af | 9 | 67% | 2 | 6.7 | 46.41 | 0 | — | 0 | 24.5 | — | — | — |

## Best overall (gate-then-rank)

Not a blended score: a staged gate, then a lexicographic sort. **Eligibility**
— a group must have completed all three stages (sanity + hermes_ops +
coding, at least one row each) to appear here at all; a partial run is
excluded outright rather than scored on whichever axes it happens to have.
**Usefulness gate** (pass/fail tier, not a weighted input) — hermes_ops pass
rate must be ≥50% (majority-pass, same concept as run_bench.py's sanity
fail-fast gate); every gate-passing group ranks above every gate-failing one
regardless of coding or speed. **Primary sort** among gate-passers is
coding pass rate, descending — the actual discerning factor once basic
agent usefulness is established. **Tie-break** is avg tok/s, descending —
speed only decides between comparably-correct models, and can never outrank
better coding ability. Dedup rule unchanged from the prior ranking design:
each model+engine+quant appears at most once, using whichever of its own
config_hash/runner_sha fragments has the most total coding+hermes_ops
evidence.

| rank | model | engine | quant | config | usefulness gate | coding | speed |
|---|---|---|---|---|---|---|---|
| 1 | openai/gpt-5.6-luna | openrouter | — | f1e3043189f3 | PASS (100%, 8) | 100% (1) | 35.5 tok/s |
| 2 | ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | 3047922de5b7 | PASS (100%, 3) | 100% (1) | 34.7 tok/s |
| 3 | unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | 1fea08092fdc | PASS (62%, 8) | 100% (1) | 20.8 tok/s |
| 4 | JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | — | 3a740261a79c | PASS (62%, 8) | 100% (11) | 8.0 tok/s |
| 5 | empero-ai/Qwen3.8-27B-Ridge-GGUF | llama.cpp | — | 7b1d82c8abab | PASS (62%, 8) | 100% (11) | 5.5 tok/s |
| 6 | ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | — | 48d75180adbc | PASS (100%, 8) | 91% (11) | 30.9 tok/s |
| 7 | unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | — | 436d6d25d30c | PASS (75%, 8) | 91% (11) | 27.1 tok/s |
| 8 | bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | llama.cpp | — | 38ccea45c281 | PASS (62%, 8) | 82% (11) | 8.5 tok/s |
| 9 | bartowski/Qwen3.8-27B-GGUF:Q4_K_M | llama.cpp | — | c02615b57f21 | PASS (88%, 8) | 82% (11) | 7.9 tok/s |
| 10 | unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | — | 644415678c37 | PASS (75%, 8) | 73% (11) | 20.8 tok/s |
| 11 | unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | — | ffa862c18cff | PASS (75%, 8) | 73% (11) | 7.7 tok/s |
| 12 | bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | llama.cpp | — | a2d241742068 | PASS (75%, 8) | 64% (11) | 20.9 tok/s |
| 13 | LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | llama.cpp | — | 0840d8e3ee87 | PASS (88%, 8) | 36% (11) | 62.6 tok/s |
| 14 | LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | llama.cpp | — | 05a5098cf4c6 | PASS (75%, 8) | 0% (11) | 67.6 tok/s |
| 15 | LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | 5f50ca6ebdf3 | PASS (62%, 8) | 0% (1) | 66.7 tok/s |
| 16 | LiquidAI/LFM2.5-8B-A1B-GGUF:BF16 | llama.cpp | — | a148c29637e6 | PASS (75%, 8) | 0% (11) | 55.3 tok/s |
| 17 | RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 00fc47aef271 | PASS (67%, 6) | 0% (3) | 42.3 tok/s |
| 18 | LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | — | 85636a621ce0 | PASS (100%, 3) | 0% (1) | 29.3 tok/s |
| 19 | LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | gguf | — | f6bb65acb160 | PASS (75%, 8) | 0% (1) | 27.0 tok/s |
| 20 | LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF:F16 drafter) | llama.cpp-dspark | — | 4f8641aa7094 | PASS (75%, 8) | 0% (1) | 26.9 tok/s |
| 21 | mlx-community/LFM2.5-8B-A1B-MLX-8bit | vllm-mlx | — | 00878f13621f | PASS (62%, 8) | 0% (1) | 26.4 tok/s |
| 22 | LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | da00492c3b46 | PASS (62%, 8) | 0% (1) | 21.4 tok/s |
| 23 | LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | vllm-mlx | — | 9693319bc3a1 | PASS (75%, 8) | 0% (1) | 20.7 tok/s |
| 24 | LiquidAI/LFM2.5-2.6B-MLX-bf16 | vllm-mlx | — | c1a7fd5d3135 | PASS (88%, 8) | 0% (1) | 19.3 tok/s |
| 25 | mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | 5e09e98f8c60 | PASS (75%, 8) | 0% (1) | 12.9 tok/s |
| 26 | unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | — | 6d148ccbfd2e | PASS (75%, 8) | 0% (1) | 6.7 tok/s |
| 27 | LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | 1d65d14c63a8 | FAIL (12%, 8) | 0% (1) | 32.8 tok/s |

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

## By suite

| model | engine | config | runner | suite | pass rate |
|---|---|---|---|---|---|
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 5fc289161e34 | hermes_ops | 6/8 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 5fc289161e34 | sanity | 2/2 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | hearth_mini | 3/3 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | kiem_mini | 5/5 |
| HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M | llama.cpp | 6fa6f52fdc56 | 8e7b1897f7e8+dirty | kipclip_mini | 2/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | hearth_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | hermes_ops | 5/8 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | kiem_mini | 5/5 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | kipclip_mini | 3/3 |
| JonathanColetti/Qwen3.8-27B-Uncensored-GGUF:Q4_K_M | llama.cpp | 3a740261a79c | a04f5cd07f20 | sanity | 2/2 |
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
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | hermes_ops | 3/3 |
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | sanity | 2/2 |
| openai/gpt-5.6-luna | api | bc97807766bc | *(predates tracking)* | kiem_mini | 1/1 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | hermes_ops | 8/8 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | kiem_mini | 1/1 |
| openai/gpt-5.6-luna | openrouter | f1e3043189f3 | 1e67356823c2 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | hermes_ops | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | hermes_ops | 7/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 0b3a2a523049 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | hearth_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | hermes_ops | 8/8 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | kiem_mini | 4/5 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | kipclip_mini | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | llama.cpp | 48d75180adbc | 6cc8b646db2e | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | 0620219fd55e | hermes_ops | 3/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | 0620219fd55e | sanity | 2/2 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | dd3232d96137 | hermes_ops | 5/8 |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | vllm-mlx | 76414c6ab37c | dd3232d96137 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | 9235ceaef852 | hermes_ops | 1/1 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | 9235ceaef852 | sanity | 2/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | bb858f72fc84 | sanity | 1/2 |
| ornith-ai/Ornith-1.5-9B-MLX-4bit | vllm-mlx | d0d250e59d4e | dd3232d96137 | hermes_ops | 5/7 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | e427e7a50b14 | *(predates tracking)* | sanity | 1/2 |
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
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | hearth_mini | 3/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | hermes_ops | 6/8 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | kiem_mini | 3/5 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | kipclip_mini | 2/3 |
| unsloth/Devstral-Small-2507-GGUF:Q4_K_M | llama.cpp | ffa862c18cff | 63c1cbdae938 | sanity | 2/2 |
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
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | hermes_ops | 5/8 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | 644415678c37 | bf1cd0ed7a6f | sanity | 2/2 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | hearth_mini | 3/3 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | hermes_ops | 6/8 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | kiem_mini | 5/5 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | kipclip_mini | 2/3 |
| unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | llama.cpp | 436d6d25d30c | 8d4f1f85f106 | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | hermes_ops | 6/8 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | kiem_mini | 0/1 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q5_K_M | llama.cpp | 6d148ccbfd2e | 1166272411af | sanity | 2/2 |

## Harness errors (excluded from every table above)

12 row(s) where the harness itself crashed (e.g. a network blip during `npm ci`, a malformed task spec) rather than the model producing a graded result — shown separately so they don't deflate pass rates or masquerade as model flakiness.

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
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and created repository-root src/lib.rs; result invalidated a |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | llama.cpp | kiem_mini | kiem_mini-feature | HARNESS ERROR: PermissionError: [Errno 13] Permission denied: '/Users/tijs/projects/local-model-bench/runner/.dspark-hea |

## Blocked configs (marked non-viable, excluded from every table above)

Scanned directly from `configs/**/*.yaml` (`orchestration.viable: blocked`),
not from log rows — a config can be blocked before it was ever run (e.g.
a whole quant ladder ruled out once one sibling engine's live pilot showed
the model too slow to be worth testing further), so it would otherwise
vanish from this file with no trace of why.

| model | engine | config | blocked_reason |
|---|---|---|---|
| mlx-community/Laguna-XS-2.1-4bit | vllm-mlx | configs/Laguna-XS-2.1/mlx.yaml | (no blocked_reason set) |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | llama.cpp-dflash2 | configs/Muse-Glimmer-30B/gguf-dflash2.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.943 tok/s across 8 real trials — well under the viability cutoff. Specific to the DFlash2 speculative-decoding variant — the plain (non-speculative) config for this same model is fine (configs/Muse-Glimmer-30B/gguf.yaml, ~8.25 tok/s), so DFlash2 is actively hurting throughput here, not helping (same pattern already seen on LiquidAI-LFM2.5-8B-A1B's DSpark variant). |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | configs/Qwen3-Coder-30B-A3B/omlx.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.75 tok/s across 8 real trials — well under the viability cutoff. Specific to the oMLX serving path for this model — the same model+quant family is genuinely fast on its other two engines (configs/Qwen3-Coder-30B-A3B/gguf.yaml ~18.6 tok/s, configs/Qwen3-Coder-30B-A3B/mlx.yaml ~11.1 tok/s), so this blocks only this one config, not the model overall. |
| mlx-community/Qwen3.8-27B-4bit | vllm-mlx | configs/Qwen3.8-27B/mlx.yaml | Marked non-viable 2026-08-22: MLX leg (mlx.yaml, config_hash 968652aede2d) completed sanity + all 3 hermes_ops tasks (2/3 pass) but decode throughput collapsed as prompt size grew — 12.37 tok/s at 29 prompt tokens down to 0.18/0.36/0.83 tok/s at 43312/65273/177877 prompt tokens, taking 668s/1021s/2904s (~77 min combined) for those 3 hermes_ops tasks alone (~1.5h total wall clock incl. load+sanity). Every hermes_ops row is flagged within_budget: false. Pilot stopped before the coding suite (even larger prompts) or the GGUF/oMLX legs were reached. |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-context-balanced.yaml | Marked non-viable 2026-08-23 BY EXTENSION (not independently tested at hermes_ops scale — this variant is sanity_only so never reached hermes_ops): the same underlying artifact (Jundot/Qwen3.8-27B-oQ4e-fp16-mtp) is confirmed to collapse to 0.008-0.012 tok/s on hermes_ops-scale prompts on 2 sibling configs in this same directory (omlx.yaml, omlx-mtp.yaml), traced to a broken chat_template.jinja shared by every config that serves this exact repo. No reason to expect this variant behaves differently. |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-hot.yaml | Marked non-viable 2026-08-23 BY EXTENSION (not independently tested at hermes_ops scale — this variant is sanity_only so never reached hermes_ops): the same underlying artifact (Jundot/Qwen3.8-27B-oQ4e-fp16-mtp) is confirmed to collapse to 0.008-0.012 tok/s on hermes_ops-scale prompts on 2 sibling configs in this same directory (omlx.yaml, omlx-mtp.yaml), traced to a broken chat_template.jinja shared by every config that serves this exact repo. No reason to expect this variant behaves differently. |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp-xhigh.yaml | Marked non-viable 2026-08-23 BY EXTENSION (not independently tested at hermes_ops scale — this variant is sanity_only so never reached hermes_ops): the same underlying artifact (Jundot/Qwen3.8-27B-oQ4e-fp16-mtp) is confirmed to collapse to 0.008-0.012 tok/s on hermes_ops-scale prompts on 2 sibling configs in this same directory (omlx.yaml, omlx-mtp.yaml), traced to a broken chat_template.jinja shared by every config that serves this exact repo. No reason to expect this variant behaves differently. |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.008 tok/s across 11 real trials (harness-confirmed, not a single fluke) — same catastrophic-collapse pattern as configs/Qwen3.8-27B/*.yaml (already blocked): small sanity prompts work, but the ~23K+-token hermes_ops system prompt produces near-zero real output. Lightning MTP on/off makes no difference (the plain omlx.yaml sibling shows the same collapse). See this file's own investigation notes (chat_template.jinja on this repo is byte-identical to Qwen3.8-27B's pre-froggeric-fix broken template). |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-ssd.yaml | Marked non-viable 2026-08-23 BY EXTENSION (not independently tested at hermes_ops scale — this variant is sanity_only so never reached hermes_ops): the same underlying artifact (Jundot/Qwen3.8-27B-oQ4e-fp16-mtp) is confirmed to collapse to 0.008-0.012 tok/s on hermes_ops-scale prompts on 2 sibling configs in this same directory (omlx.yaml, omlx-mtp.yaml), traced to a broken chat_template.jinja shared by every config that serves this exact repo. No reason to expect this variant behaves differently. |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.012 tok/s across 11 real trials (harness-confirmed, not a single fluke) — same catastrophic-collapse pattern as configs/Qwen3.8-27B/*.yaml (already blocked): small sanity prompts work, but the ~23K+-token hermes_ops system prompt produces near-zero real output. See this file's own investigation notes (chat_template.jinja on this repo is byte-identical to Qwen3.8-27B's pre-froggeric-fix broken template). |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | vllm-mlx | configs/Ternary-Bonsai-27B/mlx.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.538 tok/s across 13 real trials — well under the viability cutoff, and this model has no GGUF config to fall back to (native 2-bit ternary training, not a post-hoc quant with a higher-precision GGUF sibling available). The omlx leg (configs/Ternary-Bonsai-27B/ omlx.yaml) is equally slow (0.534 tok/s) — not an MLX-specific issue. |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | configs/Ternary-Bonsai-27B/omlx.yaml | Marked non-viable 2026-08-23: hermes_ops averaged 0.534 tok/s across 11 real trials — well under the viability cutoff. The mlx leg (configs/Ternary-Bonsai-27B/mlx.yaml) is equally slow (0.538 tok/s) — not an oMLX-specific issue, and this model has no GGUF config to fall back to. |

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

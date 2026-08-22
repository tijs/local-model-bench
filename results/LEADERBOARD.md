# Leaderboard

Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not
hand-edit rows below, edit the log and regenerate instead.

> **⚠ 138/218 rows below predate the 2026-08-21
> adversarial-review grading fixes** (no `runner_git_sha` at all — that
> field didn't exist yet when they were produced). A second independent
> review found the first review's own fixes still left real bugs (see
> AGENTS.md), so **do not treat any pre-2026-08-21 PASS/FAIL as final
> signal** until re-run under current grading. Known-affected checks,
> confirmed to have changed real outcomes:
> - `kiem_mini-feature` (all rows before the C1 fix): graded only the
> library function, never the CLI wiring — one logged PASS is known to
> have a compiler warning proving the CLI half was never implemented.
> - `hermes_ops-error-recovery` (all rows before this session's fixes,
> including a since-fixed regression where the word "error" itself
> became an auto-fail): rewarded fabricated file contents as long as
> an unrelated word like "error" appeared anywhere in the answer.
> - `hermes_ops-selection` (all rows before the L4 fix): `response_contains:
> "18"` matched "18" as a substring of any number, including "2018".
> - `hermes_ops-chaining` (all rows before the L5 fix): only checked the
> written number appeared somewhere in the file, not that it was the
> ONLY content, despite the prompt saying "just that number".
> - `sanity-tool` (all rows): graded with multiset argument matching,
> not exact key/value matching — could pass wrong argument names.
> Re-running is the only way to get current, trustworthy rows for these
> tasks; regenerating this file alone does not re-grade anything.

Grouped by (model, backend, quant, config_hash, runner_git_sha) — never
averaged across different configs OR different harness/grading code
versions, even for the same model+backend, since either would mix
genuinely different experiments (e.g. before/after a settings fix, or
before/after a grading-bug fix). `config_hash` links to a verbatim
snapshot of the exact config content used (`results/configs/`), not the
live (possibly since-edited) config file — see `config_hash` values
flagged "config since changed" for rows predating that snapshot.
`runner_git_sha` rows marked `+dirty` were graded by uncommitted code.

**`avg tok/s` caveat** (adversarial review finding H6, not fully closed):
this is `completion_tokens / wall_seconds` across the ENTIRE multi-turn
loop, including every prefill of the suite's system prompt — it's a
prefill-dominated-workload throughput number, not a pure decode rate, and
it's averaged across `sanity` (tiny prompt) and `hermes_ops` (large,
repeated system prompt) rows in one cell. Treat it as a rough signal,
not a precise generation-speed comparison; a real prefill/decode split
is a follow-up, not yet implemented. `avg TTFT` is blanked instead of
silently mislabeled for proxied configs (see below), but is still a
single combined average across suites where it IS real.

**¹ `temp (coding only)`** (2nd adversarial review finding CR-3, a bug in
the H7 fix): the config's declared temperature is what the coding suite
(`hermes chat`, driven by `run_fixture_suite.py`) actually runs at, since
it respects the server's launch flags. `sanity`/`hermes_ops` (driven by
`run_prompt.py`) deliberately hardcode `temperature=0` for EVERY model,
always, regardless of this config value — a longstanding, documented
design choice (see `tasks/SCHEMA.md` "Temperature is deliberately fixed
at 0"), not a bug. The H7 fix originally displayed this value as if it
applied everywhere, which was false for 124 of 138 rows at the time.
Note also: `configs/Qwen3.8-27B-Ridge/gguf.yaml` is the only config that
sets `--presence-penalty` (1.5) — a third confound alongside temp/
reasoning-mode when comparing it against `configs/Qwen3.8-27B/gguf.yaml`,
not currently its own column since no other config sets this flag.

**² `slow passes`** (methodology review, finding F5): count of PASS rows
that took longer than `bench_common.py`'s `INTERACTIVE_BUDGET_SECONDS`
(300s) to complete — still correct, and still counted in `pass rate`
above, but not a practically usable result in a real interactive agentic
session. Deliberately separate from `timeout_seconds`/`--timeout`, which
exist to give a slow-but-alive model a fair chance to finish generating
without being cut off mid-response — a task can legitimately take up to
that much generous budget and still show up here if it's well past what
an interactive session would tolerate. 300s is a judgment call (see that
constant's own comment), not a hard spec.

| model | backend | quant | temp (coding only)¹ | reasoning | config | runner | tasks | pass rate | slow passes² | avg tok/s | avg TTFT (s) | hallucinated tools | peak RSS (GB) | framework | quant family | cache | MTP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | xhigh | [3618a30940bc](configs/3618a30940bc.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 9.0 | 4.15 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | [6f8f1c7b8d48](configs/6f8f1c7b8d48.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 11.0 | 3.67 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | ssd | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | [a7867bea182c](configs/a7867bea182c.yaml) | fc71ba2c66f8+dirty | 7 | 29% | 0 | 3.9 | 3.68 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | cold | lightning |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | [b6112a82c243](configs/b6112a82c243.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 10.6 | 3.50 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | hot | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | [b7b32d0eb150](configs/b7b32d0eb150.yaml) | fc71ba2c66f8+dirty | 6 | 33% | 0 | 4.4 | 3.50 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | — | 1.0 | medium | [f9648093327f](configs/f9648093327f.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 11.0 | 3.49 | 0 | — | omlx | oQ4e-fp16 mixed precision + MTP tensors | cold | off |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | [011816a7d0df](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | ? | ? | [aa5d02c11bba](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 55.8 | 5.54 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | [57734ec83d1b](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | [8dd47a586509](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 1.6 | 13.67 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | ? | ? | [a03394d84d27](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 1.7 | 15.56 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | — | 0.1 | n/a | [4ee1b9a806e5](configs/4ee1b9a806e5.yaml) | fc71ba2c66f8+dirty | 5 | 80% | 0 | 21.1 | 13.93 | 0 | — | omlx | BF16 | cold | off |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | [303eba1d5495](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 61.4 | 5.03 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | ? | ? | [f4620fe8538d](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | — | ? | ? | [85636a621ce0](configs/LiquidAI-LFM2.5-8B-A1B/gguf-dspark.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 83% | 0 | 29.3 | 8.69 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | [5fd02e54bb9d](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | ? | ? | [b9bea7cd700c](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 2.4 | 11.62 | 0 | — | ? | ? | ? | ? |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | — | 0.2 | n/a | [f3b91883da61](configs/f3b91883da61.yaml) | fc71ba2c66f8+dirty | 5 | 100% | 0 | 28.7 | 10.51 | 0 | — | omlx | BF16 | cold | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | [00fc47aef271](configs/00fc47aef271.yaml) | fc71ba2c66f8+dirty | 13 | 62% | 0 | 42.3 | 9.97 | 0 | — | omlx | oQ4-fp16 mixed precision | cold | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | [8c159510d3a5](configs/8c159510d3a5.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 89.9 | 0.81 | 0 | — | omlx | oQ4-fp16 mixed precision | ssd | off |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | — | 0.2 | n/a | [c1ed322cee8c](configs/c1ed322cee8c.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 105.5 | 1.57 | 0 | — | omlx | oQ4-fp16 mixed precision | hot | off |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | [3f3368f78d8d](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 0 | 7.7 | 58.80 | 0 | — | ? | ? | ? | ? |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | ? | ? | [b0b30ac444da](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 67% | 0 | 8.0 | 57.94 | 0 | — | ? | ? | ? | ? |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | ? | ? | [fd29e9c067f8](configs/Muse-Glimmer-30B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 60% | 0 | 8.3 | 64.61 | 0 | — | ? | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | [e6a0628476cc](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 7.8 | 8.98 | 0 | — | ? | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | ? | ? | [f6397d624011](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 8 | 100% | 0 | 6.2 | 52.74 | 0 | — | ? | ? | ? | ? |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | Q4_K_M+DFlash2 | ? | ? | [0686abeab746](configs/Qwen3.8-27B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 5.8 | 55.96 | 0 | — | ? | ? | ? | ? |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | [163fa63ffb83](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 0 | 20.2 | 15.45 | 0 | — | ? | ? | ? | ? |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | ? | ? | [29ed581f7054](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | ? | ? | [6a3700901e2b](configs/Qwen3.8-27B-Ridge/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 67% | 0 | 4.6 | 52.03 | 0 | — | ? | ? | ? | ? |
| gpt-5.6-luna | api | — | ? | ? | [86cbe69b94ae](configs/Luna/api.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| mlx-community/Laguna-XS-2.1-4bit | omlx | — | 1.0 | unspecified | [f1037eaa5995](configs/f1037eaa5995.yaml) | fc71ba2c66f8+dirty | 7 | 57% | 0 | 18.8 | 42.82 | 1 | — | omlx | MLX 4-bit | cold | off |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | [8b3cbca5d1b1](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 0 | 4.6 | 22.76 | 0 | — | ? | ? | ? | ? |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | ? | ? | [92c4b9be230e](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | — | 0.7 | instruct | [08e51e50397d](configs/08e51e50397d.yaml) | fc71ba2c66f8+dirty | 2 | 50% | 0 | 13.1 | 0.80 | 0 | — | omlx | MLX 4-bit | cold | off |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | [152424abaa13](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 3.1 | 198.83 | 0 | — | ? | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | [bbaa3dfa1953](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 0 | 8.6 | 3.76 | 0 | — | ? | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | ? | ? | [f894953f1f80](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0 | 0.3 | 337.71 | 0 | — | ? | ? | ? | ? |
| mlx-community/Qwen3.8-27B-4bit | omlx | — | 1.0 | thinking | [1eec0081c5d6](configs/1eec0081c5d6.yaml) | fc71ba2c66f8+dirty | 5 | 40% | 0 | 3.4 | 5.65 | 0 | — | omlx | MLX 4-bit | cold | off |
| openai/gpt-5.6-luna | api | — | ? | ? | [1f7b55bd4401](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 15.2 | 4.30 | 0 | — | ? | ? | ? | ? |
| openai/gpt-5.6-luna | api | — | ? | ? | [bc97807766bc](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | ? | ? | [3047922de5b7](configs/Ornith-1.5-35B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 100% | 0 | 34.7 | 1.90 | 0 | — | ? | ? | ? | ? |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | — | ? | ? | [e427e7a50b14](configs/Laguna-XS-2.1/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 50% | 0 | 0.1 | 11.96 | 0 | — | ? | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | ? | ? | [8e85abe37e32](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | [21faf0240ec3](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 7.0 | 117.18 | 0 | — | ? | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | ? | ? | [c2576cd6b385](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 0 | 9.0 | 97.84 | 0 | — | ? | ? | ? | ? |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | — | 0.7 | unspecified | [40462ce69e01](configs/40462ce69e01.yaml) | fc71ba2c66f8+dirty | 5 | 100% | 0 | 6.6 | 119.62 | 0 | — | omlx | native ternary 2-bit | cold | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | [520aba6e3536](configs/520aba6e3536.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 32.8 | 1.38 | 0 | — | omlx | oQ4e-fp16 mixed precision | ssd | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | [7bceae5b4c3c](configs/7bceae5b4c3c.yaml) | fc71ba2c66f8+dirty | 2 | 100% | 0 | 32.3 | 1.38 | 0 | — | omlx | oQ4e-fp16 mixed precision | hot | off |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | — | 0.7 | instruct | [afecbd0a9f5f](configs/afecbd0a9f5f.yaml) | fc71ba2c66f8+dirty | 6 | 83% | 0 | 13.9 | 35.28 | 0 | — | omlx | oQ4e-fp16 mixed precision | cold | off |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | [840ac866adff](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | 0 | — | — | 0 | — | ? | ? | ? | ? |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | ? | ? | [fe085c7fef30](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 18.0 | 18.49 | 0 | — | ? | ? | ? | ? |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | UD-Q2_K_XL | ? | ? | [2233edb1c4f2](configs/Qwen3.8-27B/gguf-unsloth-ud-q2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 6.3 | 55.08 | 0 | — | ? | ? | ? | ? |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | — | ? | ? | [89f4d8d04793](configs/Qwen3.8-27B/gguf-unsloth-ud-q4.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 0 | 6.4 | 55.57 | 0 | — | ? | ? | ? | ? |

## Flaky tasks (mixed pass/fail under identical conditions)

Any task with the SAME (model, backend, quant, config_hash,
runner_git_sha, suite, task_id) that comes back with SOME passes and
some fails is not "probably fine" — it's proof this one task's result
isn't safe to treat as a boolean for this model (adversarial review
finding C5: temperature=0 measurably does not make MLX/Metal generation
deterministic across runs). This catches flakiness from an explicit
`--trials N` run AND from two separate invocations that happen to share
every one of those fields (found live: a real historical entry below
came from two independent runs, not --trials, which didn't exist yet).
Tasks run only once never appear here — that is NOT the same as
confirmed-stable, just untested for flakiness.

| model | backend | quant | config | suite | task | pass/trials |
|---|---|---|---|---|---|---|
| mlx-community/Qwen3.8-27B-4bit | mlx | — | f894953f1f80 | hermes_ops | hermes_ops-selection | 1/2 |

## By suite

| model | backend | config | runner | suite | pass rate |
|---|---|---|---|---|---|
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 3618a30940bc | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | 6f8f1c7b8d48 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | kiem_mini | 0/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | a7867bea182c | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b6112a82c243 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | kiem_mini | 0/1 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | b7b32d0eb150 | fc71ba2c66f8+dirty | sanity | 2/2 |
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | f9648093327f | fc71ba2c66f8+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 011816a7d0df | *(predates tracking)* | kiem_mini | 1/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 57734ec83d1b | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | hermes_ops | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | fc71ba2c66f8+dirty | hermes_ops | 2/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | omlx | 4ee1b9a806e5 | fc71ba2c66f8+dirty | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | f4620fe8538d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | 5fd02e54bb9d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | omlx | f3b91883da61 | fc71ba2c66f8+dirty | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | hermes_ops | 4/6 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | kiem_mini | 0/3 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 00fc47aef271 | fc71ba2c66f8+dirty | sanity | 4/4 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | 8c159510d3a5 | fc71ba2c66f8+dirty | sanity | 2/2 |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | c1ed322cee8c | fc71ba2c66f8+dirty | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 3f3368f78d8d | *(predates tracking)* | hermes_ops | 2/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | 3f3368f78d8d | *(predates tracking)* | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | hermes_ops | 1/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | kiem_mini | 1/1 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | b0b30ac444da | *(predates tracking)* | sanity | 2/2 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | fd29e9c067f8 | *(predates tracking)* | hermes_ops | 1/3 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | fd29e9c067f8 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | 0686abeab746 | *(predates tracking)* | hermes_ops | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | 0686abeab746 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | e6a0628476cc | *(predates tracking)* | hermes_ops | 3/3 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | e6a0628476cc | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | *(predates tracking)* | hermes_ops | 4/4 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | f6397d624011 | *(predates tracking)* | sanity | 4/4 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | *(predates tracking)* | hermes_ops | 2/3 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 163fa63ffb83 | *(predates tracking)* | sanity | 2/2 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | 29ed581f7054 | *(predates tracking)* | kiem_mini | 1/1 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | hermes_ops | 1/3 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | kiem_mini | 1/1 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | 6a3700901e2b | *(predates tracking)* | sanity | 2/2 |
| gpt-5.6-luna | api | 86cbe69b94ae | *(predates tracking)* | kiem_mini | 1/1 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | hermes_ops | 2/3 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | kiem_mini | 0/2 |
| mlx-community/Laguna-XS-2.1-4bit | omlx | f1037eaa5995 | fc71ba2c66f8+dirty | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | hermes_ops | 2/3 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 92c4b9be230e | *(predates tracking)* | kiem_mini | 1/1 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | omlx | 08e51e50397d | fc71ba2c66f8+dirty | sanity | 1/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | hermes_ops | 3/3 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | bbaa3dfa1953 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | f894953f1f80 | *(predates tracking)* | hermes_ops | 3/4 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 1eec0081c5d6 | fc71ba2c66f8+dirty | hermes_ops | 0/3 |
| mlx-community/Qwen3.8-27B-4bit | omlx | 1eec0081c5d6 | fc71ba2c66f8+dirty | sanity | 2/2 |
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | hermes_ops | 3/3 |
| openai/gpt-5.6-luna | api | 1f7b55bd4401 | *(predates tracking)* | sanity | 2/2 |
| openai/gpt-5.6-luna | api | bc97807766bc | *(predates tracking)* | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | hermes_ops | 3/3 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | kiem_mini | 1/1 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | 3047922de5b7 | *(predates tracking)* | sanity | 2/2 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | e427e7a50b14 | *(predates tracking)* | sanity | 1/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 21faf0240ec3 | *(predates tracking)* | hermes_ops | 3/3 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 21faf0240ec3 | *(predates tracking)* | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 8e85abe37e32 | *(predates tracking)* | kiem_mini | 0/1 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | *(predates tracking)* | hermes_ops | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | c2576cd6b385 | *(predates tracking)* | sanity | 2/2 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | omlx | 40462ce69e01 | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 520aba6e3536 | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | 7bceae5b4c3c | fc71ba2c66f8+dirty | sanity | 2/2 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | hermes_ops | 3/3 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | kiem_mini | 0/1 |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | afecbd0a9f5f | fc71ba2c66f8+dirty | sanity | 2/2 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 840ac866adff | *(predates tracking)* | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | sanity | 2/2 |

## Harness errors (excluded from every table above)

3 row(s) where the harness itself crashed (e.g. a network blip during `npm ci`, a malformed task spec) rather than the model producing a graded result — added 2026-08-21 (3rd adversarial review, finding CR3-6) so these are visible instead of silently deflating pass rates or masquerading as model flakiness.

| model | backend | suite | task | grade_output (truncated) |
|---|---|---|---|---|
| Jundot/Qwen3.8-27B-oQ4e-fp16-mtp | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |
| RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and created repository-root src/lib.rs; result invalidated a |
| scottlowry/Ornith-1.5-9B-oQ4e-fp16 | omlx | kiem_mini | kiem_mini-feature | HARNESS ERROR: child agent escaped the disposable workspace and modified the source fixture; result invalidated and sour |

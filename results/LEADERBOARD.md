# Leaderboard

Regenerated from `log.jsonl` by `runner/build_leaderboard.py` — do not
hand-edit rows below, edit the log and regenerate instead.

> **⚠ 138/138 rows below predate the 2026-08-21
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

| model | backend | quant | temp | reasoning | config | runner | tasks | pass rate | avg tok/s | avg TTFT (s) | hallucinated tools |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | 0.1 | n/a | [011816a7d0df](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | — | 0.1 | n/a | [aa5d02c11bba](configs/LiquidAI-LFM2.5-2.6B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 55.8 | 5.54 | 0 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | [57734ec83d1b](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | — | — | 0 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | [8dd47a586509](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 1.6 | 13.67 | 0 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | — | 0.1 | n/a | [a03394d84d27](configs/LiquidAI-LFM2.5-2.6B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 1.7 | 15.56 | 0 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | 0.2 | n/a | [303eba1d5495](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 61.4 | 5.03 | 0 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | — | 0.2 | n/a | [f4620fe8538d](configs/LiquidAI-LFM2.5-8B-A1B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | — | — | 0 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | — | 0.2 | n/a | [85636a621ce0](configs/LiquidAI-LFM2.5-8B-A1B/gguf-dspark.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 83% | 29.3 | 8.69 | 0 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | 0.2 | n/a | [5fd02e54bb9d](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | — | — | 0 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | — | 0.2 | n/a | [b9bea7cd700c](configs/LiquidAI-LFM2.5-8B-A1B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 2.4 | 11.62 | 0 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | [3f3368f78d8d](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 7.7 | 58.80 | 0 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | [b0b30ac444da](configs/Muse-Glimmer-30B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 67% | 8.0 | 57.94 | 0 |
| bartowski/Muse-Glimmer-30B-GGUF:Q4_K_M (+ incoai/Muse-Glimmer-30B-DFlash2-GGUF:Q4_K_M drafter) | gguf | — | 1.0 | thinking | [fd29e9c067f8](configs/Muse-Glimmer-30B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 60% | 8.3 | 64.61 | 0 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | [e6a0628476cc](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 7.8 | 8.98 | 0 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | [f6397d624011](configs/Qwen3.8-27B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 8 | 100% | 6.2 | 52.74 | 0 |
| bartowski/Qwen3.8-27B-GGUF:Q4_K_M | gguf | Q4_K_M+DFlash2 | 1.0 | thinking | [0686abeab746](configs/Qwen3.8-27B/gguf-dflash2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 5.8 | 55.96 | 0 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | 0.6 | thinking | [163fa63ffb83](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 20.2 | 15.45 | 0 |
| bartowski/Qwen_Qwen3.5-9B-GGUF:Q8_0 | gguf | — | 0.6 | thinking | [29ed581f7054](configs/Qwen3.5-9B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| empero-ai/Qwen3.8-27B-Ridge-GGUF | gguf | — | 0.7 | instruct | [6a3700901e2b](configs/Qwen3.8-27B-Ridge/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 67% | 4.6 | 52.03 | 0 |
| gpt-5.6-luna | api | — | None | unspecified | [86cbe69b94ae](configs/Luna/api.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | 0.7 | instruct | [8b3cbca5d1b1](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 80% | 4.6 | 22.76 | 0 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | — | 0.7 | instruct | [92c4b9be230e](configs/Qwen3-Coder-30B-A3B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | 1.0 | instruct | [152424abaa13](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 3.1 | 198.83 | 0 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | 1.0 | instruct | [bbaa3dfa1953](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 100% | 8.6 | 3.76 | 0 |
| mlx-community/Qwen3.8-27B-4bit | mlx | — | 1.0 | instruct | [f894953f1f80](configs/Qwen3.8-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 75% | 0.3 | 337.71 | 0 |
| openai/gpt-5.6-luna | api | — | None | unspecified | [1f7b55bd4401](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 15.2 | 4.30 | 0 |
| openai/gpt-5.6-luna | api | — | None | unspecified | [bc97807766bc](configs/Luna/openrouter.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M | gguf | — | 1.0 | unspecified | [3047922de5b7](configs/Ornith-1.5-35B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 6 | 100% | 34.7 | 1.90 | 0 |
| poolside/Laguna-XS-2.1-GGUF:Q4_K_M | gguf | — | 1.0 | thinking | [e427e7a50b14](configs/Laguna-XS-2.1/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 2 | 50% | 0.1 | 11.96 | 0 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | — | 0.7 | unspecified | [8e85abe37e32](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 0% | — | — | 0 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | 0.7 | unspecified | [21faf0240ec3](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 7.0 | 117.18 | 0 |
| prism-ml/Ternary-Bonsai-27B-mlx-2bit | mlx | 2bit-native | 0.7 | unspecified | [c2576cd6b385](configs/Ternary-Bonsai-27B/mlx.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 4 | 100% | 9.0 | 97.84 | 0 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | instruct | [840ac866adff](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 1 | 100% | — | — | 0 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | — | 0.7 | instruct | [fe085c7fef30](configs/Qwen3-Coder-30B-A3B/gguf.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 18.0 | 18.49 | 0 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | UD-Q2_K_XL | 1.0 | thinking | [2233edb1c4f2](configs/Qwen3.8-27B/gguf-unsloth-ud-q2.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 6.3 | 55.08 | 0 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | — | 1.0 | thinking | [89f4d8d04793](configs/Qwen3.8-27B/gguf-unsloth-ud-q4.yaml) (unsnapshotted, predates 2026-08-21 fix — may not match) — *config since changed* | *(predates tracking)* | 5 | 100% | 6.4 | 55.57 | 0 |

## Flaky tasks (mixed pass/fail across trials)

A task run more than once (`--trials N`) under the identical
model/config/runner that comes back with SOME passes and some fails is
not "probably fine" — it's proof this one task's result isn't safe to
treat as a boolean for this model (adversarial review finding C5:
temperature=0 measurably does not make MLX/Metal generation
deterministic across runs). Tasks run only once never appear here —
that is NOT the same as confirmed-stable, just untested for flakiness.

| model | backend | config | suite | task | pass/trials |
|---|---|---|---|---|---|
| mlx-community/Qwen3.8-27B-4bit | mlx | f894953f1f80 | hermes_ops | hermes_ops-selection | 1/2 |

## By suite

| model | backend | config | runner | suite | pass rate |
|---|---|---|---|---|---|
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | 011816a7d0df | *(predates tracking)* | kiem_mini | 1/1 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-GGUF:Q8_0 | gguf | aa5d02c11bba | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 57734ec83d1b | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | hermes_ops | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | 8dd47a586509 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-2.6B-MLX-bf16 | mlx | a03394d84d27 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | 303eba1d5495 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 | gguf | f4620fe8538d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-GGUF:Q8_0 (+ DSpark F16 drafter) | gguf | 85636a621ce0 | *(predates tracking)* | sanity | 2/2 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | 5fd02e54bb9d | *(predates tracking)* | kiem_mini | 0/1 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | hermes_ops | 3/3 |
| LiquidAI/LFM2.5-8B-A1B-MLX-bf16 | mlx | b9bea7cd700c | *(predates tracking)* | sanity | 2/2 |
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
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | hermes_ops | 2/3 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 8b3cbca5d1b1 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit | mlx | 92c4b9be230e | *(predates tracking)* | kiem_mini | 1/1 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | hermes_ops | 3/3 |
| mlx-community/Qwen3.8-27B-4bit | mlx | 152424abaa13 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | bbaa3dfa1953 | *(predates tracking)* | sanity | 2/2 |
| mlx-community/Qwen3.8-27B-4bit | mlx | f894953f1f80 | *(predates tracking)* | hermes_ops | 3/4 |
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
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | 840ac866adff | *(predates tracking)* | kiem_mini | 1/1 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M | gguf | fe085c7fef30 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q2_K_XL | gguf | 2233edb1c4f2 | *(predates tracking)* | sanity | 2/2 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | hermes_ops | 3/3 |
| unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M | gguf | 89f4d8d04793 | *(predates tracking)* | sanity | 2/2 |

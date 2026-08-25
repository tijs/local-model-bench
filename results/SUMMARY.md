# Current top picks — hand-curated snapshot

**Hand-curated, not auto-regenerated** — unlike `LEADERBOARD.md` (rebuilt
from `log.jsonl` after every run; never hand-edit it), this is a
point-in-time reading of that data. Re-check against `LEADERBOARD.md` if
it's been a while — last updated **2026-08-23**, 522 log rows / 47
configs.

**The one caveat that matters most**: grading was fixed on 2026-08-21
(several real scoring bugs closed — see `LEADERBOARD.md`'s top warning).
Any row without a `runner_git_sha` predates that fix and isn't trustworthy
signal on its own. Several models that look like they "passed coding" in
raw log history only did so under that old, buggy grading, and haven't
been re-run since — this summary only counts a pass if it happened under
current grading.

## The one confirmed pick

**`Qwen3-Coder-30B-A3B` on `llama.cpp` (Q4_K_M)** —
`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M`,
`configs/Qwen3-Coder-30B-A3B/gguf.yaml`. This is the only model+engine
combination in the whole dataset with a coding-suite pass confirmed under
current (post-2026-08-21) grading:

| avg tok/s | hermes_ops pass rate | coding (kiem_mini) |
|---|---|---|
| 20.8 | 62% (5/8) | **1/1** |

Still n=1 on the coding task and 62% isn't a clean sweep on hermes_ops,
so treat this as "the strongest evidence we have," not "solved" — but
it's real, current-grading evidence, which nothing else below can claim.

## Fast, plausible, but not yet confirmed under current grading

These cleared the speed gate and *looked* good in the early history — but
their only coding-suite pass on record predates the grading fix (no
`runner_git_sha`), or they've never reached the coding suite under current
grading at all. Worth a re-run before trusting, not worth dismissing.

| Model | Engine | avg tok/s | Status |
|---|---|---|---|
| Ornith-1.5-35B-A3B | llama.cpp (Q4_K_M) | 34.7 | Fastest of the group; only coding evidence is pre-fix |
| Qwen3.5-9B | llama.cpp (Q8_0) | ~14 | Only coding evidence is pre-fix |
| Muse-Glimmer-30B | llama.cpp (Q4_K_M) | 8.5 | Only coding evidence is pre-fix |
| Qwen3.8-27B-Ridge | llama.cpp | 5.5 | Only coding evidence is pre-fix; also spent one earlier run speed-gated (5.8 tok/s, under the old 10 tok/s bar, before the cutoff was lowered) |

## One that looked good and didn't hold up

**`gpt-5.6-luna`** (hosted, via `openai-codex` OAuth — not a local model,
kept as a comparison point): the pre-fix history shows a pass, but the
only current-grading coding attempt (`configs/Luna/api.yaml`) is a
**fail**. Flagging this specifically because it's the clearest example of
why the pre/post-fix distinction matters — this one didn't just go
untested, it flipped.

## Fastest overall, regardless of coding status

Every config that cleared the ≥4 tok/s speed gate, sorted by raw
throughput. Most of these have no current-grading coding data at all yet
— this list is "candidates worth trying," not "confirmed good."

| avg tok/s | Model | Engine | Quant |
|---|---|---|---|
| 99.4 | LiquidAI/LFM2.5-8B-A1B | vllm-mlx | 8-bit |
| 66.7 | LiquidAI/LFM2.5-8B-A1B | llama.cpp | Q8_0 |
| 55.7 | LiquidAI/LFM2.5-8B-A1B | llama.cpp | BF16 |
| 44.6 | LiquidAI/LFM2.5-2.6B | llama.cpp | BF16 |
| 34.7 | Ornith-1.5-35B-A3B | llama.cpp | Q4_K_M |
| 32.8 | LiquidAI/LFM2.5-2.6B | llama.cpp | Q8_0 |
| 20.8 | Qwen3-Coder-30B-A3B | llama.cpp | Q4_K_M |
| 12.9 | Qwen3-Coder-30B-A3B | vllm-mlx | 4-bit |

(Full list, plus everything dismissed and why, in `LEADERBOARD.md`'s
"Speed-gated configs" / "Blocked configs" sections.)

## Decision (2026-08-25): MLX-backend investigation closed

**Plain llama.cpp/GGUF wins essentially every real speed comparison run
so far** — often several times faster than the same model on vllm-mlx or
oMLX, including at matched quantization (ruling out "it's just a
lower-precision quant" as the explanation). The isolated oMLX backend
additionally hung repeatedly (2+ hours, once 11+) in a non-convergent
tool-calling loop across multiple models. The gap was judged too large and
too consistent to close with config tuning, so further MLX investigation
is closed — GGUF/llama.cpp is the primary engine going forward. If you're
choosing a serving engine independent of model, start there; existing
MLX-backend rows below stay as historical record, not open questions.

## What to do next, if picking today

Use `Qwen3-Coder-30B-A3B` on `llama.cpp`. If you want a second option to
compare it against, re-run the coding suite (`kiem_mini`, ideally with
`--trials 3+`) against `Ornith-1.5-35B-A3B` on `llama.cpp` first — it's
the fastest candidate with a plausible-but-unconfirmed track record, so a
few current-grading trials would settle it either way.

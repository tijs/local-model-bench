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

## Decision (2026-08-25): retired near-duplicate configs

After the harness improvement plan landed (layered timeout/liveness
budgets, semantic error-recovery grading — see `AGENTS.md`), the surviving
GGUF candidate list was reviewed for near-duplicates: model families with
multiple fine-tune/quant variants where one variant already clearly
dominates (or ties) another. Retired configs are NOT marked
`viable: blocked` — they still work, they're just not being actively
retested going forward. Each carries its own inline retirement note; this
is the consolidated rationale.

**Qwen3.8-27B family** — `Qwen3.8-27B-Uncensored/gguf.yaml` is the clear
winner (11/11 coding, 8.0 tok/s) and is now the sole active representative
of this family. Retired:
- `Qwen3.8-27B/gguf.yaml` (base) — 9/11 coding, 7.9 tok/s, beaten outright.
- `Qwen3.8-27B-Ridge/gguf.yaml` — ties Uncensored's 11/11 coding but slower
  (5.5 vs 8.0 tok/s), strictly worse once pass rates tie.
- `Qwen3.8-27B/gguf-mtp-speed.yaml` — already a confirmed NEGATIVE result
  on its own terms (8/11 coding, 5.2 tok/s, 3 genuine timeouts vs the base
  config's 9/11 @ 7.9 tok/s) — the MTP+quantized-KV speed tactic doesn't
  help on this Mac.
- `Qwen3.8-27B/gguf-unsloth-ud-q2.yaml`, `gguf-unsloth-ud-q4.yaml`,
  `gguf-dflash2.yaml` — all `sanity_and_hermes_ops_only` (ctx-size
  structurally below hermes's 64K coding minimum), never real coding
  candidates regardless of this decision.
- Still active from this family: `gguf-unsloth-ud-q5-64k.yaml` (genuinely
  larger usable context at Q5, different enough to keep evaluating).

**Qwen3.6-35B-A3B family** — checked the real numbers and this one is a
**near-tie**, not a clear win: base and `Qwen3.6-35B-A3B-Uncensored/gguf.yaml`
both scored 10/11 coding (identical single failure,
`kipclip_mini-testwrite`), both 6/8 hermes_ops, both ~27 tok/s. Retired the
base config anyway per standing preference for the uncensored variant when
tied-or-better — flagging explicitly that this is preference-driven, not
evidence-driven, unlike the 27B family above.

**LiquidAI-LFM2.5-8B-A1B family** — `gguf-dspark.yaml` (DSpark speculative
decoding) measured slower (26.9 tok/s) than the plain `gguf.yaml` it
modifies (66.4 tok/s) — the same negative-speed-tactic pattern as the
Qwen3.8-27B MTP finding above. Only one coding data point on record so not
fully conclusive, but consistent enough to retire rather than spend a full
rerun on it.

**Model caches deleted** (2026-08-25, freeing disk space for the models
still queued to (re)test): `unsloth/Qwen3.6-35B-A3B-GGUF` (~22GB, base
quant, since the Uncensored variant is a separate HF repo — no overlap),
`LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF` (~633MB, the DSpark drafter only —
the shared Q8_0 base repo used by the kept `gguf.yaml` was left untouched).
`bartowski/Qwen3.8-27B-GGUF`, `empero-ai/Qwen3.8-27B-Ridge-GGUF`, and
`incoai/Qwen3.8-27B-DFlash2-GGUF` were already deleted in an earlier
disk-space cleanup. `unsloth/Qwen3.8-27B-GGUF` (~19GB) was deliberately
**not** deleted despite holding two retired quants (Q2/Q4), because it
also holds the Q5_K_M quant the still-active `gguf-unsloth-ud-q5-64k.yaml`
config needs, in the same repo snapshot.

## What to do next, if picking today

Use `Qwen3-Coder-30B-A3B` on `llama.cpp`. If you want a second option to
compare it against, re-run the coding suite (`kiem_mini`, ideally with
`--trials 3+`) against `Ornith-1.5-35B-A3B` on `llama.cpp` first — it's
the fastest candidate with a plausible-but-unconfirmed track record, so a
few current-grading trials would settle it either way.

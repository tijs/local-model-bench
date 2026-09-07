# Current top picks — final post-fix snapshot

**Hand-curated, not auto-regenerated** — unlike `LEADERBOARD.md` (rebuilt
from `log.jsonl` after every run; never hand-edit it), this is a
point-in-time reading of the saved benchmark rows. Last updated
**2026-09-07**. Everything from "Final eight: post-fix local comparison"
onward is retained for prior decisions and provenance.

## 2026-09-07 update: text-only Qwen 3.6 is the new top pick; Nemotron discarded

Two overnight full benchmark runs. Both are single-trial, 25 graded rows each
(2 sanity, 8 `hermes_ops`, 15 coding), zero `harness_error` rows.

| model | sanity | hermes_ops | coding | **total** |
|---|---|---|---|---|
| **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** (`3421f91401ab`) | 2/2 | **8/8** | 14/15 | **24/25** |
| ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit (`dc3e7e62a965`) | 2/2 | 6/8 | 14/15 | 22/25 |
| mlx-community/Qwen3.8-27B-4bit (`c7f10a958b1e`) | 2/2 | 6/8 | 14/15 | 22/25 |
| mlx-community/Qwen3.6-35B-A3B-4bit (stock, `cea524483faf`) | 2/2 | 7/8 | 13/15 | 22/25 |
| orcarouter/Qwen3.8-27B-Uncensored-MLX (`40fbffd03a95`) | 4/4 | 5/8 | 11/15 | 20/27 |
| mlx-community/gemma-4-26b-a4b-it-4bit (`bc93f3cc55a1`) | 2/2 | 6/8 | 10/15 | 18/25 |
| ~~NVIDIA-Nemotron-3.5-Lightning-30B-A3B~~ **DISCARDED** (`d9be6d0097ea`) | 2/2 | 1/8 | 4/15 | 7/25 |

### What the text-only build is

A Mei-produced derivative of `mlx-community/Qwen3.6-35B-A3B-4bit` with the
vision tower removed: 333 `vision_tower` tensors (851.8 MiB) and the
`vision_config` key stripped. **Every retained tensor is byte-identical to the
source** (per-tensor sha256 verified at build time, re-verified on a 50-tensor
random sample). Published at
<https://huggingface.co/Tostibrown/Qwen3.6-35B-A3B-4bit-textonly>; config at
`configs/Qwen3.6-35B-A3B-textonly/mei.yaml`.

Measured against stock, both runs **cold** (hermes_ops TTFT 62–66 s on both
sides, separate KV directories, each a first run):

- **Memory**: 19.551 GB loaded vs 20.444 GB — **−0.83 GiB**, exactly the vision tower.
- **Short decode**: 1.31–1.32x faster on the sanity rows (fixed prompt,
  near-fixed output), consistent with the isolated 61.85 vs 49.95 tok/s
  measurement. Removing `vision_config` also moves the bundle from vmlx's VLM
  load path to the LLM path, which is where the speed difference comes from.
- **Quality: unchanged.** The 24/25 vs 22/25 gap **is not a real difference** —
  the text weights are bit-identical, so it cannot be. It is single-trial
  variance, and a useful calibration of it: an 8-point swing at temperature 0.

**Recommendation: make text-only Qwen 3.6 the primary Mei candidate.** Top
score, lowest memory, fastest short decode, fully reproducible provenance.
Keep the stock config for history; run the text-only one.

### Nemotron-3.5-Lightning: discarded 2026-09-07

Scored **7/25** (hermes_ops 1/8). **Speed is not why.** Its decode is ~68–70
tok/s, the fastest in the Mei lineup. It fails because it does not emit tool
calls when the prompt carries Hermes's ~22k-token tool payload — it narrates
the intended call in prose and stops, so every task ends after one turn.

Ruled out with live evidence: chat template (the real 4,739-token Hermes system
prompt alone produces a valid call), tool count (22 tools fine), thinking mode
(`--enable-thinking false` gives byte-identical failures), raw prompt length
(6.3k tokens of repeated filler still works), and an explicit "you must call
tools" instruction. With realistic varied context the threshold is ~5–6k tokens.
Config marked `viable: non-viable`. Only untested lever: shrink the tool payload.

### Harness defect found — the speed gate is not reproducible

Nemotron was run twice against the **same persistent `--kv-cache-dir`**. Same
prompts, byte-identical outputs, and:

| run | avg hermes_ops tok/s | avg TTFT | 4.0 speed gate |
|---|---|---|---|
| first (cold KV cache) | **1.02** | 84.6 s | **failed** → coding skipped |
| second (warm from run 1) | **32.74** | 1.8 s | **passed** → coding ran |

`tokens_per_second = completion_tokens / wall_seconds` and this workload is
~99% prefill, so the metric moves **32x on cache state alone**. Every Mei config
uses a persistent KV dir, so this can affect any cross-run comparison.
**It did not corrupt the table above** — both Qwen 3.6 runs were verified cold.
Suggested fix: clear the KV dir before a gated run, or record cache state on the
gate row so cold and warm are never compared.

### Note on memory figures elsewhere in this file

`mei_memory_active_bytes` / `peak` are **MLX allocator** numbers, not OS memory
pressure. Measured 2026-09-07: a 19.5 GB mmap'd model shows only ~150 MB
`phys_footprint` and ~1.1 GB RSS, because the weights are clean file-backed
pages. Treat "peak 25.73 GB @ 65k"-style figures as allocator accounting.

## Final eight: post-fix local comparison

Each headline entry has **25 graded rows**: 2 sanity, 8 `hermes_ops`, and
15 coding tasks. The Gemma/Mei entry combines two explicitly pinned fragments
with the same model/config (10 sanity+Hermes rows plus 15 coding rows). All
eight have zero `harness_error` rows. The selected-eight score is a report
score, normalized only across these eight entries: 45% combined quality, 25%
decode speed, 20% recovered total runtime, 10% coding turns. Decode tok/s and
TTFT are model-speed metrics; coding token counts and wall/runtime are
end-to-end agent-task metrics.

| Family | Engine / selected artifact | Sanity | Hermes Ops | Coding | Combined | Decode tok/s | TTFT (s) | Runtime | Sanity+Hermes tokens in/out | Coding tokens in/out | Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ornith-1.5-35B | llama.cpp / Q4_K_M | 2/2 | 8/8 | 14/15 | **95.7%** | **30.0** | 7.0 | 0.97 h | 1,991,913 / 18,763 | 236,585 / 91,269 | **0.920** |
| Ornith-1.5-35B | Mei / MLX 4-bit | 2/2 | 8/8 | 14/15 | **95.7%** | 20.8 | 39.1 | **0.82 h** | 1,051,258 / 8,890 | 206,471 / 56,449 | **0.899** |
| Gemma 4 26B A4B | llama.cpp / APEX-I-Quality | 2/2 | 7/8 | 13/15 | **87.0%** | **29.9** | 10.7 | 1.50 h | 1,376,408 / 10,779 | 321,682 / 108,123 | **0.809** |
| Gemma 4 26B A4B | Mei / MLX 4-bit | 2/2 | 6/8 | 10/15 | **69.6%** | 4.2 | 53.6 | 2.72 h | 429,756 / 1,374 | 357,740 / 97,174 | **0.472** |
| Qwen3.8-27B base | llama.cpp / UD-Q5_K_M | 2/2 | 7/8 | 13/15 | **87.0%** | 6.7 | 46.6 | 4.62 h | 1,658,201 / 29,555 | 257,730 / 77,054 | **0.572** |
| Qwen3.8-27B base | Mei / MLX 4-bit | 2/2 | 6/8 | 14/15 | **87.0%** | 5.1 | 294.0 | 6.23 h | 1,700,331 / 32,270 | 265,176 / 101,695 | **0.560** |
| Qwen3.8-27B Uncensored | llama.cpp / Heretic Q5_K_M | 2/2 | 8/8 | 12/15 | **87.0%** | 6.5 | 49.9 | 6.13 h | 1,551,927 / 36,479 | 249,028 / 82,317 | **0.549** |
| Qwen3.8-27B Uncensored | Mei / MLX 4-bit | 2/2 | 5/8 | 11/15 | **69.6%** | 6.6 | 304.5 | 7.47 h | 3,557,407 / 53,478 | 173,362 / 46,915 | **0.467** |

### Outcome summary

- **Best overall quality:** Ornith reaches 95.7% on both engines. llama.cpp has
  the higher decode rate (30.0 vs 20.8 tok/s); Mei completes the recovered
  benchmark interval sooner (0.82 vs 0.97 h).
- **Gemma:** the llama.cpp APEX-I-Quality artifact is materially ahead of its
  Mei counterpart on quality (87.0% vs 69.6%), decode speed (29.9 vs 4.2
  tok/s), and recovered runtime (1.50 vs 2.72 h).
- **Qwen base:** quality is tied at 87.0%; llama.cpp is faster on decode and
  recovered runtime, while Mei has one more coding pass (14/15 vs 13/15).
- **Qwen Uncensored:** llama.cpp has higher quality (87.0% vs 69.6%) and is
  faster end-to-end; decode speed is effectively tied (6.5 vs 6.6 tok/s).
- **Failure taxonomy:** 28 model/task failures across the selected rows: 12
  task failures and 16 timeout/stall classifications; 0 malformed-tool and
  0 harness errors. See `failure_taxonomy.png`.
- **Not a universal engine win:** this final set supports a clear llama.cpp
  recommendation for Gemma and Qwen, while Mei remains competitive on
  Ornith quality and elapsed runtime.

### Final eight charts

![Selected-eight composite score](summary_score_chart.png)

![Quality vs recovered runtime](quality_vs_runtime.png)

![Mei vs llama.cpp deltas](engine_delta.png)

![Suite pass-rate heatmap](suite_heatmap.png)

![Recovered runtime breakdown](runtime_breakdown.png)

![Failure taxonomy](failure_taxonomy.png)

## Benchmark-v4 (2026-09-01): the hermes_ops real-answer fix, and the current active lineup

**What changed and why**: hermes_ops's one-shot `run_prompt.py` client had
no `finish_reason=length` continuation logic (unlike the coding suites'
real `hermes chat` agentic loop), so thinking-mode models were getting
truncated mid-answer at the default 4096-token cap — an artificial
ceiling, not a real capability gap. Fixed with a per-config
`hermes_ops_max_tokens` override (16384 for thinking-mode configs).
Raising the cap exposed a SECOND, previously-masked bug: `run_prompt.py`
never counted `reasoning_content` deltas as stream progress, so a
thinking model reasoning past the first_progress/stream_idle watchdogs
got misclassified as stalled even while actively generating — fixed by
counting `reasoning_content` as meaningful progress. Both fixes verified
live against the Heretic config, which reproduced both failures in
sequence as each landed (`hermes_ops-targeted-edit`: FAIL/truncation →
FAIL/stall → PASS). See git tag `benchmark-v4` and commit `0adb046` for
the full technical writeup.

**Full rerun results** (all under the new methodology, hermes_ops now
correctly measuring real capability instead of an artificial token
ceiling):

| Model | Sanity | hermes_ops | Coding | avg tok/s | hermes_ops tokens (prompt/completion) | Coding tokens (in/out) |
|---|---|---|---|---|---|---|
| Ornith-1.5-35B-A3B Q4_K_M (baseline, no thinking) | 2/2 | 8/8 | 14/15 | **29.4** | 1,665,372 / 10,698 | 229,237 / 84,413 |
| Qwen3.8-27B UD-Q5_K_M | 2/2 | 8/8 | 14/15 | 6.7 | 1,657,256 / 31,027 | 244,885 / 75,237 |
| Qwen3.8-27B-Uncensored (Heretic) Q5_K_M | 2/2 | 8/8 | 12/15 | 6.4 | 1,550,982 / 36,334 | 249,028 / 82,317 |
| Gemma 4 26B-A4B APEX-I-Quality | 2/2 | 7/8 | 13/15 | 28.1 | 1,376,115 / 10,609 | 321,682 / 108,123 |
| Qwen3.6-35B-A3B-Uncensored Q4_K_M | 2/2 | 6/8 | 13/15 | 27.1 | 2,194,585 / 9,395 | 341,649 / 61,240 |
| Ornith-1.5-35B-A3B Q5_K_M | **CRASHED (OOM)** | — | — | — | — | — |
| Ornith-1.5-35B-A3B APEX-I-Quality | 2/2 | 7/8 | 14/15 | 27.4 | 1,875,678 / 7,693 | 324,217 / 82,559 |
| Ornith-1.5-35B-A3B "thinking" attempt | 2/2 | 8/8 | 14/15 | 28.7 | 1,990,968 / 18,631 | 236,585 / 91,269 |

**Two findings worth flagging on their own**:

1. **Ornith Q5_K_M crashed on a genuine GPU/unified-memory OOM during
   model warmup** (`kIOGPUCommandBufferCallbackErrorOutOfMemory`, real
   Metal error, SIGABRT) — not a benchmark or config bug. The header
   comment's own estimate (~26.9GB, comfortably under 32GB) was too
   optimistic: real llama.cpp compute-buffer overhead costs more than
   weights+KV arithmetic accounts for. Confirmed not transient: the very
   next config (a *smaller* 21.25GB quant) launched and ran cleanly
   seconds later, same machine, same code path. Marked `viable: blocked`
   in `configs/Ornith-1.5-35B-A3B/gguf-q5.yaml`.
2. **The Ornith "thinking mode" fix attempt did not work.** Ornith 1.5 is
   genuinely built on the Qwen 3.5 MoE lineage and IS a reasoning model
   by design (confirmed via its own `config.json` and README), but every
   existing config launches its server without `--jinja`, silently
   falling back to llama.cpp's generic template instead of the model's
   real one — meaning every prior Ornith result in this benchmark ran
   without its native thinking behavior. Adding `--jinja` plus the same
   effort-aware template already used for the Qwen3.8-27B family DID load
   and run cleanly (8/8 hermes_ops, 14/15 coding) — but a direct
   transcript check across all 8 hermes_ops tasks found **zero
   `reasoning_content`, zero `<think>` tags** anywhere. Something about
   this template/model combination isn't actually activating visible
   reasoning, despite loading without error. **This needs real diagnosis
   before it's worth re-running** — the current config
   (`gguf-thinking.yaml`) doesn't demonstrate thinking mode actually
   works, it just demonstrates it doesn't crash.

**Pruning decision (user call, 2026-09-01)** — active lineup going
forward:
- **Keep**: Ornith Q4_K_M (baseline — best plain result, fastest,
  cleanest sweep), Qwen3.8-27B UD-Q5_K_M, Gemma 4 I-Quality.
- **Keep deliberately despite the lower score**: Qwen3.8-27B-Uncensored
  (Heretic) — kept specifically to have an uncensored option
  represented in the lineup, even though its speed (6.4 tok/s) and
  coding rate (80%) are near the bottom of this batch.
- **Dropped** (real, viable results — not marked non-viable, just not
  carried forward): Qwen3.6-35B-A3B-Uncensored, Ornith
  APEX-I-Quality.
- **Excluded — too large for this hardware, not a fixable bug**: Ornith
  Q5_K_M. This isn't "blocked pending a fix and worth retrying later" —
  the quant itself (23.6GB) doesn't fit this Mac's usable memory margin,
  a permanent size constraint on this specific hardware, not a transient
  or software issue.
- **Open, not re-queued**: Ornith "thinking mode" — needs the
  reasoning-activation gap above actually diagnosed first.

**Benchmark v2, in one paragraph**: two real methodology bugs were found
and fixed this round — a shared Swift fixture bug (`kiem_mini-parse-note`
failing on toolchain-agnostic grounds, not model capability — see
"Harness fixes" below) and coding-suite timeouts too tight to let a
slower-but-correct model finish (1500s → 3000s). The leaderboard's "Best
overall" ranking also moved from a hard pass/fail gate to a weighted
composite score (pass rate 45%, speed 25%, time 20%, turns 10%) so a
slow-but-correct model scores lower rather than being disqualified
outright. 10 of this benchmark's already-tested models were rerun end to
end under the fixed methodology, plus 4 new candidates added mid-session
(a reasoning-effort variant, a rebuilt-toolchain Laguna retest, and two
Ornith requant variants) — 14 configs total (one, an MTP variant, was
deliberately skipped — see below).

**Auto-table eligibility, tightened 2026-08-29**: `LEADERBOARD.md`'s "Best
overall" table now requires a group to have run the FULL suite on both
hermes_ops (8 tasks) and coding (11 tasks) — not just "at least one row
of each" — and to be graded under `benchmark-v2` or a later commit, not
pre-v2 methodology. This closed two real gaps found the same day: a
1-coding-task partial rerun had been ranking #1 over
`APEX-Compact`'s genuine 11/11 result on raw pass-rate alone, and a
dedup bug was silently erasing a model (Luna, via OpenRouter) from the
table entirely because the evidence-richest fragment happened to be
missing its sanity row — dedup now prefers a complete fragment over an
incomplete-but-richer one, not just the most evidence. Regenerating with
these fixes shrank the table from 31 rows to 8 and changed the top
ranking materially (see below).

**Still an open gap, not fixed by the above**: a model with NO single
`runner_git_sha` fragment that's complete on its own — only several
complementary partial ones (e.g. one fragment has full coding but no
sanity row, another has sanity but only partial coding) — still won't
appear, because merging evidence across fragments graded by different
harness code risks blending incompatible grading semantics. The
Qwen3.8-27B xhigh-effort row is exactly this case; its real data is
reconciled by hand below since the auto-table can't safely show it.

**"Pass rate" now means hermes_ops + coding combined, not coding alone**
(fixed same day, user request): `Laguna-XS-2.1` had briefly ranked #1 in
the auto-table (0.914) ahead of `APEX-Compact` (0.901) purely on
speed/time, because hermes_ops was only ever a pass/fail gate (≥50%) and
never affected score once past it — a bare 50% hermes_ops record scored
identically to a clean 100% sweep. The "pass" axis of the composite now
counts every hermes_ops AND coding task as one equal unit toward a single
combined rate, so a barely-gate-passing record costs real score even with
a speed/time edge. Regenerating: `APEX-Compact` is back to #1 (0.901),
`Laguna-XS-2.1` #2 (0.837) — matching this doc's actual recommendation
without needing a hand-curated caveat about the chart's top row. The
≥50% hermes_ops gate itself is unchanged; this only changed what happens
to score *above* it.

**Chart below is current as of benchmark-v4 (2026-09-01)**: the
benchmark-v4 rerun (see above) ran the 8-model lineup against the full
15-task coding suite (`hearth_full` included), so `LEADERBOARD.md`'s
"Best overall" table and this chart now reflect real v4 data — no longer
stale. Note the leaderboard's dedup logic keeps only one config per
model+engine+quant triple: `ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q4_K_M`
appears ONCE in that table (the more recent "thinking mode" attempt's
config_hash), silently superseding the plain baseline row even though
both are legitimate, differently-configured results — see the
benchmark-v4 section above for why that specific row's "reasoning:
thinking (medium)" label doesn't reflect actually-observed behavior.

![Best overall composite score by model — benchmark-v4](score_chart.png)

*Composite score = combined hermes_ops+coding pass rate 45% + speed 25% +*
*time taken 20% + turns used 10%, gate-passers only (hermes_ops ≥ 50%) —*
*see `LEADERBOARD.md`'s "Best overall" table for the exact per-model*
*numbers behind this chart.*
*Auto-regenerated by `runner/plot_leaderboard.py` after every benchmark*
*run; this image can go stale between SUMMARY.md's own hand-curated edits.*

## New standout: Ornith-1.5-35B-A3B on a third-party APEX quant

**`mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact`** — a third-party
mixed-precision quant (routed experts at lower precision since only 8 of
256 fire per token, always-active components kept high precision) —
landed a **perfect score**: hermes_ops **8/8**, coding **11/11**, at
28.6 tok/s. This genuinely beats the standard Q4_K_M baseline below (91%
coding, 100% hermes_ops) on coding pass rate specifically, at a smaller
file size (16.5GB vs Q4_K_M's ~21GB) and comparable speed. This is now
the clearest pick in the whole dataset if you're willing to use a
third-party quant rather than the model author's own.

A parallel run of the same technique bundled with MTP speculative
decoding (`APEX-MTP-Compact`) was deliberately **not run** — the user
chose to isolate APEX's quantization effect alone rather than re-test MTP
speculative decoding on this model, given this repo's existing negative
MTP result on a different model (Qwen3.8-27B, see "retired configs"
below). Whether MTP would help *this* model specifically remains
untested.

Config: `configs/Ornith-1.5-35B-A3B/gguf-apex.yaml`.

## The three-way tie on coding pass rate — pick by speed, then hermes_ops (author's-own-quant baseline)

Among models on their original author's own quant (not the third-party
APEX requant above), these three all landed **91% coding** (10/11 tasks)
on the full 11-task battery — the highest coding pass rate in that group.
Speed and hermes_ops reliability are what separate them:

| Model | Engine | hermes_ops | coding | avg tok/s |
|---|---|---|---|---|
| **Ornith-1.5-35B-A3B** (Q4_K_M) | llama.cpp | **100%** (8/8) | 91% (10/11) | **30.9** |
| Qwen3.6-35B-A3B-Uncensored (Q4_K_M) | llama.cpp | 75% (6/8) | 91% (10/11) | 30.2 |
| Qwen3.8-27B (UD-Q5_K_M, 64K ctx) | llama.cpp | 88% (7/8) | 91% (10/11) | 6.8 |

**Pick: `Ornith-1.5-35B-A3B` on `llama.cpp`.** It's the only one of the
three with a clean hermes_ops sweep (8/8 — no dropped tool-calling/agent-
op task), and it ties the other two on coding while running ~4.5x faster
than the Q5_K_M Qwen3.8-27B variant. `Qwen3.6-35B-A3B-Uncensored` is a
close, genuinely comparable second choice — same coding rate, same speed
tier, just two hermes_ops misses (`error-recovery`, `persistent-failure`)
Ornith didn't have.

Config: `configs/Ornith-1.5-35B-A3B/gguf.yaml`. First attempt at testing
this hit a false "backend never became healthy" report (~17.5min cold-
cache load exceeding the harness's old 600s health-check timeout) —
confirmed healthy via the server log and a live curl, recovered with a
plain relaunch. This exact incident is why the timeout was raised to 1800s
(see "Harness fixes" below) — worth knowing if you re-run this config and
the first load looks slow.

## Qwen3-Coder-30B-A3B — a second perfect coding score, on the standard quant

`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M` scored **coding 11/11**
under benchmark v2's rerun (up from a much weaker earlier result under
the pre-v2 methodology) — hermes_ops landed at 75% (6/8, missing
`multi-step-chain` and `no-tool-needed`). This is a standard-architecture
dense-GQA MoE model (confirmed via its HF `config.json`: `qwen3_moe`, no
hybrid/linear-attention layers) — notably, this is also the model used to
rule out "hybrid architecture is the whole explanation" in the ongoing
MLX-slowdown investigation (see that section below), since it showed the
same MLX slowdown pattern despite having no hybrid layers.

Config: `configs/Qwen3-Coder-30B-A3B/gguf.yaml`.

## Qwen3.8-27B family: quant and reasoning-effort tradeoffs, not a clean story

This session tested the base and Uncensored Qwen3.8-27B checkpoints at
both Q4_K_M and UD-Q5_K_M, plus a "quality-max" variant (min-p=0.0,
reasoning-effort=xhigh) of the base Q5 config. The results do **not**
point to a single simple rule:

| Variant | hermes_ops | coding | Note |
|---|---|---|---|
| base, Q4_K_M | 8/8 (100%) | 9/11 (82%) | |
| base, UD-Q5_K_M | 7/8 (88%) | **10/11 (91%)** | Q5 beat Q4 here |
| base, UD-Q5_K_M + xhigh effort | **8/8 (100%)** | 9/11 (82%) | see below |
| Uncensored, Q4_K_M | 8/8 (100%) | 10/11 (91%) | |
| Uncensored, Q5_K_M | 5/8 (62%) | 10/11 (91%) | Q5 regressed hermes_ops here |

**Quant-up doesn't uniformly help**: Q5 beat Q4 on the base model
(coding 82%→91%), but on the Uncensored fine-tune, Q5 *regressed*
hermes_ops (100%→62%) for the same coding pass rate — a real,
checkpoint-specific finding, not a general rule for this family.

**Reasoning-effort xhigh is a genuine mixed tradeoff, not a clean win**:
explicitly setting `--reasoning-effort xhigh` (overriding the chat
template's silent `medium` default every other result on this family
used) took hermes_ops from 7/8 to a perfect 8/8, but coding actually
*dropped* from 10/11 to 9/11 (two tasks config 4 passed — `kiem_mini-
parse-note` and `kipclip_mini-testwrite` — failed under xhigh). The cost
was steep: individual coding tasks ran roughly **1.8x longer** in
wall-clock time (e.g. one hermes_ops task went from 1506s to 2696s) at
essentially unchanged raw decode speed (~6-7 tok/s either way) — the
difference is entirely more reasoning tokens generated per turn, not
slower generation. Verdict: xhigh trades a coding regression for a
hermes_ops improvement at a steep time cost — not a straightforward
"more effort = better" result, and not clearly worth the wall-clock cost
for this benchmark's task mix.

Also discovered (and fixed, not just measured) during this investigation:
`--min-p` silently defaults to `0.05` in llama.cpp, not `0.0`/disabled as
Qwen's own sampler recipe specifies — see
[`docs/INFERENCE_ENGINES.md`](../docs/INFERENCE_ENGINES.md) for the full
gotcha. Every prior Qwen3.8-27B result on record ran with this filter
active without anyone having set it explicitly. The xhigh config fixes
this too, so its coding/hermes_ops numbers reflect BOTH changes
together, not reasoning effort in isolation.

Configs: `configs/Qwen3.8-27B/gguf.yaml`, `gguf-unsloth-ud-q5-64k.yaml`,
`gguf-unsloth-ud-q5-64k-xhigh.yaml`, `configs/Qwen3.8-27B-Uncensored/
gguf.yaml`, `gguf-q5.yaml`.

## Next tier — 73-82% coding

| Model | Engine | hermes_ops | coding | avg tok/s |
|---|---|---|---|---|
| Muse-Glimmer-30B (Q4_K_M) | llama.cpp | 62% (5/8) | 82% (9/11) | 8.5 |
| Devstral-Small-2507 (Q4_K_M) | llama.cpp | 75% (6/8) | 73% (8/11) | 7.7 |
| Qwen3.5-9B (Q8_0) | llama.cpp | 75% (6/8) | 64% (7/11) | 20.9 |

Muse-Glimmer is genuinely capable, held back mostly by speed (~8.5 tok/s)
and a rockier hermes_ops sweep (3 misses: `chaining`, `noisy-result`,
`multi-step-chain`) rather than coding correctness — every coding fail on
record is a real, on-topic wrong answer, not a harness artifact.
Qwen3.5-9B is the smallest model tested this session (9B vs 27-35B for
everything else) and scores accordingly — a real, expected
size-vs-capability tradeoff, not a surprise.

## Fast, but doesn't do agentic coding — a real, repeated finding

Every `LiquidAI/LFM2.5-8B-A1B` variant tested (GGUF Q8_0, GGUF BF16, MLX,
vllm-mlx, and two DSpark/speculative-decoding attempts) scored **0/11 or
1/11 on the coding suite** despite being the fastest models in the whole
benchmark (55-68 tok/s). This isn't an infra artifact — confirmed via
`hermes_turns`/`hermes_tool_calls` being populated (real, if weak, model
output) on every attempt, not the null/missing pattern that flags a
harness crash. The smaller `LiquidAI/LFM2.5-2.6B` (Q8_0) does somewhat
better (36%, 4/11) at a still-fast 62.6 tok/s, but nowhere near the coding
capability of the models above. **Speed alone doesn't make a model a
viable Hermes backend on this benchmark.**

## Resolved: Laguna-XS-2.1 — root-caused, fixed, and now has real results

Root cause found and fixed 2026-08-27: a Metal-specific `mul_mm_id` f16
overflow bug in llama.cpp, triggered by this model's unusually large MoE
layer activations. Full root-cause narrative (upstream PR discussion,
the CPU-only diagnostic that confirmed it, the custom-build fix and its
before/after numbers) now lives in
[`docs/INFERENCE_ENGINES.md`](../docs/INFERENCE_ENGINES.md) — this
section keeps just the benchmark results the fix unblocked. Wired in as
`configs/Laguna-XS-2.1/gguf-metal-fixed.yaml`.

**Full benchmark run, 2026-08-28 — first real results this model has ever
produced.** hermes_ops **4/8**, coding **10/11** (only `kiem_mini-parse-
note` failed — the task that trips up nearly every model this session),
at a genuinely fast **28-42 tok/s** (excluding one anomalous 1.6 tok/s
outlier on a short response) — among the quicker models tested despite
33B total parameters. None of the hermes_ops/coding failures relate to
the now-fixed Metal bug; they're real model-behavior issues, pulled
directly from grade output and transcripts:
- `kiem_mini-parse-note`: burned the full 40-turn budget, and partway
  through **removed its own correct validation guard** while iterating,
  regressing a check it had gotten right earlier, then ran out of turns
  before catching the regression. Its own final summary claimed all
  tests passed — that was false.
- `hermes_ops-targeted-edit`: used `read_file`+`write_file` to rewrite a
  whole file instead of the expected `patch` tool for a precise edit.
- `hermes_ops-multi-step-chain`: same turn-budget exhaustion pattern as
  the coding failure above.
- `hermes_ops-persistent-failure`: with all tools deliberately made
  unavailable, **fabricated a plausible-looking example** (`df -h`
  output with specific made-up numbers) instead of admitting it had no
  way to get real data — a genuine hallucination-under-pressure failure.
- `hermes_ops-no-tool-needed`: called a search tool for a question that
  should've gotten a direct answer — over-eager tool triggering.

Bottom line: the Metal fix did exactly what it was supposed to — it let
this model actually be evaluated on its own merits for the first time.
The result is a real, usable, fast model with some genuine agentic
reliability gaps (turn-budget management and honesty-under-pressure),
not an infrastructure failure.

## Hosted-model reference set (2026-08-26)

Two hosted models, run through the exact same full suite (sanity +
hermes_ops + all 11 coding tasks) via real, metered OpenRouter API keys —
included as a cost/quality reference point, **not** as a candidate to pick
instead of a local model. The whole point of this benchmark is finding the
best *local* Hermes backend; these two exist so a reader can see what
paying for a hosted model actually buys, in the same units as everything
above.

| Model | hermes_ops | coding | avg tok/s¹ | real cost (sanity+hermes_ops) |
|---|---|---|---|---|
| `openai/gpt-5.6-luna` (OpenRouter) | 100% (8/8) | 91% (10/11) | 20.5 | $0.0235 |
| `anthropic/claude-haiku-4.5` (OpenRouter) | 100% (8/8) | 82% (9/11) | 36.3 | $0.82 |

¹ Hosted-model tok/s is a network-latency-inclusive API measurement, not a
pure decode rate the way local `avg tok/s` is elsewhere in this doc — not
strictly apples-to-apples with the local models' numbers, but still a
useful relative signal.

**Luna genuinely ties the best local models** (91% coding, matching the
three-way tie above) with a clean 100% hermes_ops sweep, at a real cost of
about 2 cents for the sanity+hermes_ops portion of a full run — this is
the old FAIL-under-old-single-task-grading result flipping to a strong
PASS once retested under the current full 11-task battery. **Haiku** lands
respectably at 82% (matching the "next tier" local models) but costs
roughly 35x more than Luna for the same sanity+hermes_ops slice ($0.82 vs
$0.0235) — consistent with its higher per-token OpenRouter pricing ($1/$5
vs Luna's $0.20/$1.20 per 1M input/output tokens). Neither hosted model's
coding-suite cost is tracked (hermes chat's CLI has no simple per-run
usage export — see each config's own `known_gaps`), so the real full-run
cost is higher than the sanity+hermes_ops figure shown, by an unknown
amount.

Configs: `configs/Luna/openrouter.yaml`, `configs/Haiku/openrouter.yaml`.
Both need `OPENROUTER_API_KEY` set as an environment variable — never
committed to this repo.

## MLX-backend investigation: closed 2026-08-25, reopened 2026-08-28, ongoing

Plain llama.cpp/GGUF won essentially every direct speed comparison
against vllm-mlx and oMLX (often several times faster at matched
quantization), and MLX investigation was closed 2026-08-25. Reopened
2026-08-28 following a public discussion (Sandeep Das, sdas86.bsky.social)
that led to real findings: two upstream `mlx-lm` bugs partially explain
hybrid-architecture models' slowdown (mlx-lm#1162, #1152), but a
confirmed *non*-hybrid model (`Qwen3-Coder-30B-A3B`) shows the same
collapse, so that's not the whole story. Live diagnostics since then
refuted the continuous-batching hypothesis and pointed the likely fault
at `vllm_mlx.server`'s own serving layer rather than `mlx-lm`/`mlx-core`
itself. Two more independently-implemented Python MLX serving wrappers
were tested and show the same order-of-magnitude collapse: oMLX
(0.75 tok/s average on real hermes_ops trials) and `jjang-ai/vmlx`
(0.2 tok/s at 30K tokens, a hard Metal OOM crash at 80K) — the latter
sharpening the theory further, since its own code comments admit its
long-context prefill for hybrid architectures is a known-incomplete
one-shot (non-chunked) implementation. A third-party Swift-native
alternative (Osaurus/vmlx-swift) is a promising but still-untested
candidate, currently blocked by a headless-Mac install issue.

**Full investigation, all findings, and current status**: see
[`docs/INFERENCE_ENGINES.md`](../docs/INFERENCE_ENGINES.md)'s "The MLX
slowdown investigation" section.

If you're choosing a serving engine today, GGUF/llama.cpp is still the
safe, proven choice; MLX is an open, promising question again, not a
closed one.

## Decision (2026-08-25): retired near-duplicate configs

After the harness improvement plan landed (layered timeout/liveness
budgets, semantic error-recovery grading — see `AGENTS.md`), the surviving
GGUF candidate list was reviewed for near-duplicates: model families with
multiple fine-tune/quant variants where one variant already clearly
dominates (or ties) another. Retired configs are NOT marked
`viable: blocked` — they still work, they're just not being actively
retested going forward. Each carries its own inline retirement note; this
is the consolidated rationale.

**Qwen3.8-27B family** — `Qwen3.8-27B-Uncensored/gguf.yaml` and
`gguf-unsloth-ud-q5-64k.yaml` (see the three-way tie above) are the
active representatives of this family. Retired at the time (2026-08-25):
- `Qwen3.8-27B/gguf.yaml` (base) — 82% coding, beaten by the Uncensored
  variant on coding pass rate with comparable speed. **Note: this
  retirement decision predates benchmark v2 and was re-tested anyway as
  part of the v2 rerun batch (see "quant and reasoning-effort tradeoffs"
  above) — it's no longer clearly dominated once quant variants and the
  new composite score are considered, so treat this specific retirement
  line as historical context, not a still-current recommendation.**
- `Qwen3.8-27B-Ridge/gguf.yaml` — ties on coding but slower.
- `Qwen3.8-27B/gguf-mtp-speed.yaml` — confirmed NEGATIVE result on its
  own terms (the MTP+quantized-KV speed tactic doesn't help on this Mac).
- `Qwen3.8-27B/gguf-unsloth-ud-q2.yaml`, `gguf-unsloth-ud-q4.yaml`,
  `gguf-dflash2.yaml` — all `sanity_and_hermes_ops_only` (ctx-size
  structurally below hermes's 64K coding minimum), never real coding
  candidates regardless of this decision.

**Qwen3.6-35B-A3B family** — checked the real numbers and this one is a
**near-tie**, not a clear win: base and `Qwen3.6-35B-A3B-Uncensored/gguf.yaml`
both landed 91% coding this round (base: 10/11 per the earlier retirement
note's 2026-08-25 check), both similar hermes_ops/speed. Retired the base
config anyway per standing preference for the uncensored variant when
tied-or-better — flagging explicitly that this is preference-driven, not
evidence-driven, unlike the 27B family above.

**LiquidAI-LFM2.5-8B-A1B family** — `gguf-dspark.yaml` (DSpark speculative
decoding) measured slower (26.9 tok/s) than the plain `gguf.yaml` it
modifies (66.4 tok/s) — the same negative-speed-tactic pattern as the
Qwen3.8-27B MTP finding above. The whole 8B-A1B family also scores 0/11 on
coding regardless of engine or speed tactic (see "Fast, but doesn't do
agentic coding" above) — the speed-tactic question is somewhat moot given
that underlying finding.

## Harness fixes shipped 2026-08-26 (round 1)

- **"Best overall" ranking redesigned to gate-then-rank** (replacing a
  weighted blend): a group must have completed all three stages (sanity +
  hermes_ops + coding) to appear at all; hermes_ops pass rate ≥50% is a
  hard pass/fail usefulness gate, not a weighted input; coding pass rate
  is the primary sort among gate-passers; avg tok/s is only a tie-break.
- **Backend health-check timeout raised from 600s to 1800s**
  (`bench_common.BACKEND_HEALTH_TIMEOUT_SECONDS`): a large GGUF's
  cold-cache first load can genuinely take 15-20+ minutes on this
  hardware — confirmed twice this session (`LiquidAI/LFM2.5-8B-A1B-GGUF:BF16`
  and `Ornith-1.5-35B-A3B`) as false "backend never became healthy"
  reports on servers that were actually loading fine.

## Harness fixes shipped 2026-08-27 — 2026-08-28 (benchmark v2)

- **Swift fixture toolchain bug fixed**: `fixtures/kiem_mini/swift/
  Package.swift` had no `platforms:` key, so SwiftPM defaulted to a
  conservative old deployment target regardless of the actual installed
  toolchain — any model using a macOS-13+-only API (a completely
  idiomatic, correct choice) hit a hard compile error, uniformly docking
  every model tested on this fixture. Added `platforms: [.macOS(.v13)]`;
  confirmed live (before/after `swift build` reproduction) that this
  flipped `kiem_mini-parse-note` from FAIL to PASS for multiple models
  that had genuinely correct code.
- **Coding-suite timeouts raised 1500s → 3000s**: a slow-but-eventually-
  correct model was being hard-killed before finishing rather than being
  allowed to complete and simply score lower on speed.
- **Weighted composite "Best overall" score** (replacing the round-1
  gate-then-rank-by-coding-alone design): pass rate 45%, speed 25%, time
  taken 20%, turns used 10% — see `runner/build_leaderboard.py`'s own
  comments for the full history (an initial equal-weights version was
  caught distorting rankings by over-rewarding speed, corrected per user
  feedback).
- **Reasoning-effort labeling**: every config now explicitly records
  `reasoning_effort` (previously silently defaulting to the chat
  template's hardcoded `medium` for 8 configs, discovered this session).
- **Score chart auto-generation**: `runner/plot_leaderboard.py`, wired
  into `run_bench.py` to regenerate `results/score_chart.png` after every
  run, embedded in both `LEADERBOARD.md` and this file.
- **Leaderboard dedup tie-break bug fixed**: an exact evidence-count tie
  between an old partial run and a fresh complete rerun of the same
  config was picking the stale one by accident of dict iteration order,
  not by any real criterion — found while reviewing this session's own
  final results (a genuine Qwen3-Coder-30B-A3B perfect-11/11 rerun lost a
  tie to an older 74%-pass partial). Now breaks ties by recency. Full
  regression test added.

## What to do next, if picking today

**Use `mudler/Ornith-1.5-35B-A3B-APEX-GGUF:APEX-Compact`** —
`configs/Ornith-1.5-35B-A3B/gguf-apex.yaml`. Perfect score (hermes_ops
8/8, coding 11/11) at 28.6 tok/s, the strongest result in the whole
dataset. If you'd rather stick to the model author's own quant rather
than a third-party requant, `Ornith-1.5-35B-A3B` on `llama.cpp` (Q4_K_M,
`configs/Ornith-1.5-35B-A3B/gguf.yaml`) is the next best choice — clean
100% hermes_ops sweep, 91% coding, 30.9 tok/s. `Qwen3-Coder-30B-A3B`
(`configs/Qwen3-Coder-30B-A3B/gguf.yaml`) is a close third if memory
footprint matters — also a perfect 11/11 coding score, smaller than the
Ornith models, though hermes_ops is a bit weaker (75%). For context: the
hosted `openai/gpt-5.6-luna` (via OpenRouter) ties the author's-own-quant
Ornith result for about 2 cents per full sanity+hermes_ops run — worth
knowing as a reference point, but Ornith (either quant) beats it locally,
for free, at comparable or better speed.

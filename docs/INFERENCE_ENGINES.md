# Inference engines on Mac (Apple Silicon) — research index

This is the canonical home for this project's research on the inference
engines themselves — their bugs, quirks, version-specific behavior, and
the ongoing MLX-vs-GGUF speed investigation. `results/SUMMARY.md` and
`AGENTS.md` link here instead of duplicating this content; keep it here
so it doesn't drift between multiple copies. Two kinds of content
deliberately live *elsewhere* and are only cross-referenced from this
file:

- **Per-model benchmark results** (pass rates, tok/s, task-level
  failures) — that's `results/SUMMARY.md` and `results/LEADERBOARD.md`.
- **oMLX per-model settings/provenance matrix** (recommended sampling,
  exact revisions, sequential test matrix) — that's
  [`docs/OMLX_MODEL_MATRIX.md`](OMLX_MODEL_MATRIX.md), a companion
  document with a narrower, model-settings-specific purpose.

## Engine landscape

Four engines have been evaluated on this project's hardware (Mac Studio,
M1 Max, 32GB unified memory):

| Engine | What it is | Port | Tool-calling |
|---|---|---|---|
| **llama.cpp** (GGUF) | `llama-server`, Homebrew-installed, OpenAI-compatible | 8016 | Native `tool_calls`, no proxy needed |
| **vllm-mlx** | Raw `mlx-lm` serving via `vllm_mlx.server` | 8012 | None in 0.4.0 (needs this repo's proxy); native parsers in 0.4.1+, with caveats — see below |
| **oMLX** | Third-party, isolated `mlx-lm` wrapper with its own patches | 8020 | Native, schema-validated | 
| **Osaurus / vmlx-swift** | Swift-native MLX stack, no Python `mlx-lm` at all | — | Native, OpenAI-compatible (evaluated, not yet benchmarked — see below) |

llama.cpp/GGUF is the primary, proven engine for this benchmark — it won
essentially every direct speed comparison against the MLX engines (see
"The MLX slowdown investigation" below). The MLX engines remain in the
repo and under active investigation because the *reason* they're slower
turned out to be more specific and interesting than "MLX is just slower
on this hardware."

## llama.cpp / GGUF

### Native tool-calling, no proxy
`llama-server` (Homebrew, build 10470) returns proper `tool_calls`
natively — confirmed live for LFM — plus real streaming usage counts
(`usage_estimated: false`), so hermes's `local-gguf` provider points
straight at it with no proxy in front. Still worth spot-checking a new
model family's raw output before trusting results, since "native for
LFM" isn't a guarantee for every family.

### `--min-p` silently defaults to 0.05
Discovered while investigating the Qwen3.8-27B family's quant/reasoning
tradeoffs (see `results/SUMMARY.md`): llama.cpp's `--min-p` is **not**
disabled by default — it silently defaults to `0.05`, not the `0.0` that
Qwen's own official thinking-mode sampler recipe specifies. Every
Qwen3.8-27B result on record before this was found ran with this filter
active without anyone having set it explicitly. This is a generic
llama.cpp gotcha, not model-specific — worth checking explicitly for any
model whose card specifies `min_p: 0` as part of its recommended sampler
settings.

### The Laguna-XS-2.1 Metal `mul_mm_id` f16 overflow bug
Laguna-XS-2.1 originally failed at the sanity-tool stage in a way that
looked like a reasoning-mode or harness-probe issue (empty content at
temp=0, a hallucinated unrelated response at temp=1.0). Reading the
upstream llama.cpp PR discussion (`ggml-org/llama.cpp#25165`, the
model's own support PR) found the real cause: Laguna XS 2.1 produces
unusually large activations in its later MoE layers, and on **Metal**
specifically, `mul_mm_id`'s f16 operand narrowing overflows above 65504
into NaN, surfacing as empty or incoherent output. A first attempted fix
(PR #25442) was closed as "not the right fix"; the real fix, PR #26223
("metal: fix NaN in mul_mm_id when activations exceed f16 range"), was
still open/unmerged when found.

Confirmed via a CPU-only diagnostic (`-ngl 0`, disabling the Metal path
entirely): 9/9 clean results where the GPU path had failed — strongly
confirming the Metal NaN diagnosis (CPU-only is not itself a viable
benchmark config, just a diagnostic). Then built llama.cpp from PR
#26223's branch (`mdegans:fix/metal-mul-mm-id-f16-overflow`, commit
`e6a3398`, confirmed to include fix commit `94fa2fc`) and retested with
full GPU/Metal offload restored: **both failure modes gone at full
speed**, decode throughput ~65 tok/s (roughly double the CPU-only
diagnostic's ~30-45 tok/s). The custom binary is kept separate from the
Homebrew build every other config uses
(`~/.local/share/local-model-bench/llama-cpp-laguna-fix/`), wired in as
`configs/Laguna-XS-2.1/gguf-metal-fixed.yaml`. See
`results/SUMMARY.md`'s "Resolved: Laguna-XS-2.1" section for the actual
benchmark results this unblocked.

### DFlash2 speculative decoding (Inco AI/z-lab)
The Homebrew-installed llama.cpp has the `--spec-type draft-dflash` CLI
flag but **not** the actual DFlash2 tensor-loading logic — that only
exists in PR #27342 (`ggml-org/llama.cpp#27342`, still open/unmerged),
whose real code lives in the author's own fork:
`z-lab/llama.cpp-fork`, branch `dflash2`. This was originally
misdiagnosed as an upstream/checkpoint bug (a "expected 81, got 58"
tensor-count error reproduced identically across two unrelated
checkpoints, which looked like strong evidence against a per-checkpoint
cause) — the correct diagnosis needed checking the *installed build's*
feature-merge status, not just ruling out a per-model cause. Built the
fork from source (cmake + Ninja + Metal, ~2 min build), kept entirely
separate from the Homebrew install. One more issue on the way to a
working request: the first real request hit a Metal OOM, caused by the
server's default 4 parallel slots quadrupling KV-cache memory across
both the target and draft models at once — fixed with `--parallel 1`.

Confirmed live: `bartowski/Qwen3.8-27B-GGUF:Q4_K_M` +
`incoai/Qwen3.8-27B-DFlash2-GGUF` (Q4_K_M drafter), `--spec-draft-n-max
7` per the PR's own benchmark command. Real completion: draft_n=791,
draft_n_accepted=389 (~49% acceptance), 9.32 tok/s vs. this benchmark's
own non-spec Qwen3.8-27B GGUF baseline (~6.5 tok/s) — a real ~1.4x
speedup (less than the PR's cited 1.85x on a 64GB M5 Pro, plausibly this
being a 32GB machine plus `<think>` reasoning tokens counted in the
total). To reproduce: run `runner/setup_dflash2_fork.sh` (builds into
`runner/.dflash2-fork/`, gitignored), then launch
`runner/.dflash2-fork/build/bin/llama-server` with `--spec-type
draft-dflash --spec-draft-hf <drafter-repo> --spec-draft-n-max 7
--parallel 1`.

**Lesson generalized from this investigation**: a bug reproducing
identically across multiple models is strong evidence against a
per-model cause, but does not by itself rule out a shared-tooling
cause — check the tool's own version/build provenance against a
feature's actual merge status before concluding "upstream broken,"
especially for a flag that exists in the CLI but whose implementing PR
is still open.

## vllm-mlx

### No tool-call parser in 0.4.0; real parsers (with caveats) in 0.4.1
`vllm_mlx.server --model <candidate>` is the raw engine. In the
originally-installed **0.4.0**, there is no server-side tool-call
parsing at all (no `--tool-call-parser` flag exists, only
`--reasoning-parser` for `<think>`-style extraction) — it returns tool
calls as raw text in `content`, not a real `tool_calls` array. This
repo's own proxy, `runner/bench_local_proxy.py` (started via
`runner/start_bench_proxy.sh`, port 8015), exists specifically to parse
this. It's pluggable per model family (`BENCH_TOOL_PARSER`) — every new
MLX candidate needs its actual raw tool-call format researched from the
model card and a matching parser registered.

**This turned out not to be a fundamental vllm-mlx limitation** — it's a
stale-dependency artifact. **0.4.1** ships a real `vllm-mlx` CLI
(`vllm-mlx serve <model> --enable-auto-tool-choice --tool-call-parser
<name>`, a different, richer entry point than the bare `python -m
vllm_mlx.server` module invocation) with native parsers for `qwen`,
`qwen3_coder`, `mistral`, `llama`, `hermes`, `deepseek`, `harmony`/
`gpt-oss`, `granite`, `nemotron`, `xlam`, `functionary`, `gemma4`,
`glm47`, `minimax`, plus `auto` (tries all). There's also a
`poolside_v1` parser registered internally — an exact name match for
Laguna-XS-2.1's undocumented tool-call format — but it's **missing from
`vllm-mlx serve`'s hardcoded `--tool-call-parser` argparse `choices=`
list** even though the parser class exists and IS in
`--reasoning-parser`'s choices. Workaround: use `--tool-call-parser
auto` for Laguna, not the direct name, to reach it without patching
vendor code.

### Critical caveat: the native `qwen3_coder` parser has a real streaming bug
Confirmed via a controlled A/B test on Qwen3-Coder-30B-A3B MLX: the
exact same request (identical prompt, `temperature=0`, everything else
equal) produces a clean, correct tool call every time under `stream:
false`, but produces malformed `tool_calls` — empty function `name`,
truncated/garbled `arguments`, sometimes a stray literal `<tool_call>`
token leaking into an argument value — under `stream: true`, which this
benchmark's `run_prompt.py` always uses (deliberately, to measure real
TTFT). This is why the qwen3_coder MLX numbers in this benchmark use
`bench_local_proxy.py`'s own custom parser, not the new native one — the
proxy always parses the complete non-streaming response before faking
SSE back to the client, so it structurally cannot hit this
streaming-specific bug.

**Lesson**: for any model where a native vllm-mlx parser exists, verify
it against BOTH a streaming and non-streaming request before trusting
it — "native support exists" does not imply "native support works
safely under streaming." The custom-proxy approach, while more manual,
turned out to be the *safer* default for models with complex
multi-parameter tool-call formats, not just a workaround for a missing
feature. Simpler single-JSON-blob formats (plain `qwen`, `hermes`/
`nous`) were not re-tested for this same bug and may or may not be
affected.

## The MLX slowdown investigation

**Original decision (2026-08-25, closed)**: plain llama.cpp/GGUF won
essentially every real speed comparison to that point — often several
times faster than the same model on vllm-mlx or oMLX, including at
matched quantization (ruling out "it's just a lower-precision quant" as
the explanation). The isolated oMLX backend additionally hung repeatedly
(2+ hours, once 11+) in a non-convergent tool-calling loop across
multiple models. The gap was judged too large and too consistent to
close with config tuning, so further MLX investigation was closed.

**Reopened 2026-08-28** with a public discussion (Sandeep Das,
sdas86.bsky.social, replying to a post about this benchmark's findings)
and follow-up research:
- Confirmed both `oMLX` and `vllm-mlx` in this repo pin the *identical*
  `mlx-lm==0.31.3` / `mlx==0.32.0` — the slowdown sits in the shared
  library both wrap, not either wrapper's own config.
- Two real upstream `mlx-lm` bugs found that plausibly explain part of
  the gap for hybrid-architecture models (Qwen3.8-27B/Qwen3.6/Ornith/
  Laguna's Gated-DeltaNet + attention mix): a prompt-cache bug that
  silently reprocesses the full prompt every turn instead of reusing
  cache (mlx-lm#1162), and SSM/DeltaNet decode speed that isn't
  context-length-constant as the architecture should allow (mlx-lm#1152).
- **But this isn't the whole story**: `Qwen3-Coder-30B-A3B` — a
  confirmed *non*-hybrid, standard dense-attention model (`qwen3_moe`,
  no linear-attention layers, verified via its HF `config.json`) — also
  showed the same slowdown, so there's at least one more general cause
  beyond the hybrid-specific bugs.

**Live diagnostics, 2026-08-28** (Qwen3.8-27B-4bit and
Qwen3-Coder-30B-A3B-4bit, both against the previously-recorded
catastrophic-collapse baselines in their own `mlx.yaml`/`omlx.yaml`
`blocked_reason` fields):

- **Continuous-batching hypothesis — refuted.** Removing
  `--continuous-batching` from `vllm_mlx.server` (an opt-in,
  off-by-default flag for concurrent users; this benchmark only ever
  sends one request at a time) did not help: short-prompt speed actually
  got slightly *worse* (7.32 vs 12.37 tok/s), and the large-prompt
  collapse was unchanged (666.83s / 0.18 tok/s at ~43K tokens, versus the
  original 668s/0.18 tok/s baseline).
- **Prefill/decode split — the key reframe.** Calling `mlx_lm.generate`
  directly, bypassing `vllm_mlx.server` entirely, on Qwen3.8-27B-4bit at
  80,432 tokens of context gave a full, non-degenerate 20-token
  completion at **10.75 tok/s decode** — nowhere near the 0.18 tok/s
  collapse the *server* showed at half that context length (43K
  tokens). This points at `vllm_mlx.server`'s own serving/scheduling
  layer as the likely fault, not mlx-lm/mlx-core's generation loop or
  the SSM/DeltaNet decode kernel as first theorized. (A same-prompt
  server-side verification attempt was inconclusive — the model
  degenerated to a 3-token reply on the synthetic filler prompt — so
  treat this as a strong working conclusion, not a fully closed case.)
- **oMLX comparison (does the second wrapper show the same bug?).** Ran
  the same direct-vs-server methodology on `Qwen3-Coder-30B-A3B-4bit`
  (the confirmed non-hybrid model, so this also bears on the
  "hybrid-cache-bug can't be the whole story" question above):
  - Bare `mlx_lm.generate` at 80,430 tokens: 107.5 tok/s prefill, 15.7
    tok/s decode (generation was only 3 tokens before EOS on the
    synthetic filler prompt, so treat the decode number as indicative,
    not precise) — again, fast, consistent with the direct-library
    result for Qwen3.8-27B above.
  - oMLX's own server (`omlx.yaml`'s `blocked_reason`) already recorded
    hermes_ops averaging **0.75 tok/s across 8 real trials** — a
    collapse of the same order of magnitude as vllm_mlx's, independently
    observed on the harness's real coding-agent workload, not just a
    synthetic long-prompt probe.
  - Live retest hit a *different*, more immediate wall before speed was
    even in question: oMLX's own preflight memory guard rejected
    prompts above ~20-25K tokens on this 32GB M1 Max at both `safe` and
    `aggressive` guard tiers ("predicted peak would require ~22-26GB
    but the Metal wired-memory ceiling is ~24GB") — meaning oMLX can't
    even *attempt* the 50-80K-token contexts that vllm_mlx and bare
    `mlx_lm` ran without incident. Bare `mlx_lm.generate` used 25.72GB
    peak on the identical 80K-token prompt with no guard and no crash,
    so this ceiling is oMLX-specific caution, not a hard hardware
    limit. Raising it further requires a system-wide
    `iogpu.wired_limit_mb` kernel change, which wasn't made (out of
    scope for a per-process diagnostic).
  - **Net read**: two independently-implemented MLX serving wrappers
    (`vllm_mlx.server` and `oMLX`) both show severe decode-speed
    collapse relative to bare `mlx_lm`, on two different models (one
    hybrid, one not). That's consistent with a shared root cause in how
    both wrap `mlx-lm` for serving, rather than two unrelated
    coincidental bugs — but the exact shared mechanism is still
    unidentified.

**Working conclusion**: if you're choosing a serving engine today,
GGUF/llama.cpp is still the safe, proven choice. But the evidence points
specifically at the Python serving layer both `vllm_mlx.server` and
`oMLX` build on top of `mlx-lm` — not `mlx-lm`/`mlx-core` itself — which
is why a *third*, differently-implemented serving layer on the same
`mlx-lm` dependency is worth testing (see "Other independent MLX
serving implementations" below).

## Osaurus / vmlx-swift

`osaurus-ai/osaurus` doesn't use the Python `mlx-lm` package at all — it
maintains its own Swift-native fork, `osaurus-ai/vmlx-swift`, with
specific, named fixes for the hybrid-architecture cache bugs found above
(e.g. `vmlx-swift#195`, "keeps Qwen 3.5/Ornith GatedDelta recurrent
state in float32 across cold and restored prefix partitions"; a
dedicated "Laguna S 2.1 revision"). It exposes a drop-in
OpenAI-compatible `/v1/chat/completions` API with full tool calling,
which would let it be added to this benchmark as `inference_engine:
osaurus` with no new harness code — a genuine new candidate, not just a
diagnostic reference. Its own docs (`MODEL_COMPATIBILITY_RESEARCH.md`)
confirm it reads directly from `~/.cache/huggingface/hub` without
copying, so testing it wouldn't require duplicate downloads of models
already cached for this benchmark's other engines.

**Blocked on this hardware, 2026-08-29.** Installed `osaurus` (0.24.1)
via `brew install --cask osaurus`; it passes Gatekeeper cleanly
(notarized, valid signature). But the project has grown substantially
since the original research above: it's now a full "AI agent harness"
(cryptographic identity, sandboxed VM/Seatbelt execution, MCP server,
plugin system), not the lightweight MLX inference server originally
scoped. More concretely, both `osaurus serve --port 1337` and `osaurus
--help` hang indefinitely on first run — zero CPU, zero output,
consistent with a blocked macOS permission dialog (Keychain/local-
network/notifications) that needs a GUI click. This Mac runs headless:
there's an active login session (`who`/`launchctl` confirm it), but no
physical or remote-desktop access to click through a dialog, and
`osascript`/System Events itself timed out ("AppleEvent time-out")
rather than giving a permission error, so scripted UI automation isn't
a path around it either. Left installed for a future retest if/when
remote-desktop access to this Mac is available.

## Other independent MLX serving implementations

Since Osaurus itself is blocked on this hardware, and the MLX slowdown
investigation points at the *serving layer* rather than `mlx-lm` core,
a third, independently-implemented serving layer on top of the same
`mlx-lm` dependency is a natural next test — same underlying library,
different server code, which cleanly separates "is it mlx-lm" from "is
it how vllm-mlx/oMLX specifically wrap it."

**`jjang-ai/vmlx`** (PyPI: `vmlx`) — **under active investigation as of
2026-08-29**. A live diagnostic test is running as this document is
being written; results are not yet in this file. Check this project's
Kiem notes for the latest findings before treating this section as
complete — the plan note's STATUS line names the current note IDs
(`kiem show <plan-note-id>`).

What's known so far: pure Python, pip/`uv tool install`-able (no GUI
app, so it doesn't hit the headless-Mac blocker Osaurus did), OpenAI +
Anthropic + Ollama-compatible HTTP API, actively maintained (833 stars,
near-daily releases as of this writing), depends on the same
`mlx-lm>=0.31.3` as vllm-mlx and oMLX but implements its own serving
layer with a "Hybrid SSM Scheduler," continuous batching, and paged KV
cache. The author, `jjang-ai`, is also a credited contributor to
`osaurus-ai/vmlx-swift` itself, so there's real cross-pollination
between the Swift and Python sides of this ecosystem rather than a
coincidental parallel project.

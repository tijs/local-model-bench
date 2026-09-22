# Run configs

One file per model+inference-engine combo: `configs/<model-slug>/<name>.yaml`,
where the filename (`mlx`, `gguf`, `omlx`, or a variant like `gguf-dflash2`)
is just a naming convention — the actual engine identity lives in the
`inference_engine:` field inside (`llama.cpp`, `vllm-mlx`, `omlx`, or a fork
variant like `llama.cpp-dflash2`/`llama.cpp-dspark`). This field went through
two renames in quick succession on 2026-08-23: a separate, coarser `backend:`
field (`mlx`/`gguf`/`omlx`/`api`) was retired in favor of the already-more-
precise `framework:` field being the sole identity — but "framework" itself
turned out not to be the right final name either, so it was renamed again to
`inference_engine:` (see build_leaderboard.py's `_row_inference_engine()` for
the backward-compat read of old log rows that still carry `backend` or
`framework` only). Documents the exact serving/inference settings used for
benchmark runs against that model — each setting with a citation, so results
are auditable and reproducible, and so a value is never just "chosen because
it seemed right" without saying so explicitly.

**Active lanes (as of 2026-09-04):** supported active local comparison engines
are **llama.cpp variants** (`llama.cpp` / `llama.cpp-dflash2` /
`llama.cpp-dspark`) and **Mei** (`inference_engine: mei`). The **oMLX** and
**vllm-mlx** lanes were retired by user decision (oMLX will not be revisited;
active local comparisons are llama.cpp + Mei only). Their config files remain
in place and their historical `results/log.jsonl` rows remain visible in the
leaderboard as reproducible evidence, but every retired config carries
`orchestration.viable: retired`, so the runner skips it and the lane is no
longer a runnable current path.

## Schema

```yaml
model: LiquidAI/LFM2.5-2.6B-MLX-bf16
# temperature/reasoning_mode: read by build_leaderboard.py and shown as
# their own columns (adversarial review finding H7 — two configs that
# differ in these, not just quant, used to look like a same-conditions
# comparison). Keep in sync with benchmark_launch_command by hand.
# NOTE: for sanity/hermes_ops specifically, temperature is IGNORED —
# run_prompt.py hardcodes temperature=0 for those two suites regardless of
# this value (see tasks/SCHEMA.md "Temperature is deliberately fixed at
# 0"); this field only reflects what the CODING suite (hermes chat)
# actually runs at.
temperature: 0.1
reasoning_mode: n/a   # thinking | instruct | n/a (no thinking-mode concept) | unspecified
inference_engine: llama.cpp  # llama.cpp | llama.cpp-dflash2 | llama.cpp-dspark |
                                  # mei (active lanes) | vllm-mlx | omlx | openrouter |
                                  # hermes-openai-codex — every engine is a grouping
                                  # key for build_leaderboard.py; vllm-mlx/omlx are
                                  # RETIRED active lanes (2026-09-04) but their
                                  # historical rows are still read backward-compatibly
benchmark_launch_command: |
  uv run --locked python -m vllm_mlx.server \
    --model LiquidAI/LFM2.5-2.6B-MLX-bf16 \
    --host 127.0.0.1 --port 8012 --max-request-tokens 4096 --max-tokens 4096

system_prompt_suffix: null   # optional — a model-specific operating
  # instruction appended (never replacing) the suite's fixed system prompt,
  # e.g. Muse-Glimmer's "Reasoning strength: high". NOT a way to hint at
  # task content. Applied to sanity/hermes_ops via a real system-prompt
  # append; applied to the coding suite by prepending to the task prompt
  # instead, since hermes chat's CLI has no system-prompt-append flag —
  # see configs/Muse-Glimmer-30B/gguf.yaml for the full reasoning.

# OPTIONAL — named request-time generation profiles (2026-09-22,
# task-specific generation settings). This is the REQUEST-TIME override
# layer: a profile's fields are forwarded onto the one-shot prompt-suite
# client (run_prompt.py) as per-request sampling/reasoning settings for the
# current backend. Server launch flags remain the coding/default baseline —
# the coding suites run through `hermes chat` and inherit them untouched;
# only the one-shot path can carry these overrides, and only when a profile
# is actually selected (see hermes_ops_generation_profile below). Each
# profile is EXPLICIT: a listed field is sent, an omitted field is NOT sent
# (the backend serves its own launch/default value for it). Supported
# fields: temperature, top_p, top_k, min_p, repetition_penalty,
# presence_penalty, frequency_penalty, reasoning_effort. Unknown field
# names and wrongly-typed values fail the run loudly at parse time — never
# silently dropped.
generation_profiles:
  capability:                 # capability/high lane: front-runners at high
    temperature: 1.0          #   effort, or xhigh where the model/vendor
    top_p: 0.95               #   supports/recommends it; new contenders
    top_k: 20                 #   are admitted high/xhigh first.
    min_p: 0
    presence_penalty: 1.5
    repetition_penalty: 1.0
    reasoning_effort: xhigh   # ONLY when the vendor/model actually declares
                              # a recommended effort. Never invented: a
                              # profile without this field sends NO
                              # reasoning_effort field — the harness does
                              # not silently assume 'medium'.
  practical:                  # practical/medium lane: medium effort for
    temperature: 0.8          #   models supporting it, to measure
    top_p: 0.9                #   lower-token behavior.
    reasoning_effort: medium

hermes_ops_generation_profile: capability  # OPTIONAL — which profile the
  # one-shot hermes_ops (general reasoning) suite uses for this model.
  # Absent = no request-time overrides at all (historic temperature=0
  # behavior preserved; old configs are untouched). A run can select a
  # DIFFERENT lane without editing the config via
  # `run_bench.py --generation-profile <name>` (hermes_ops stage only) or
  # `run_prompt_suite.py --generation-profile <name>`. Selection is
  # explicit: an undeclared profile name fails the run.

# OPTIONAL — coding profile (2026-09-22), SEPARATE from the general/Hermes
# Ops request profile above. `hermes chat` (the coding suites' agent loop)
# exposes only ONE per-invocation generation control — `--reasoning LEVEL`
# (vocabulary, from live `hermes chat --help`: none/minimal/low/medium/
# high/xhigh/max/ultra) — so the coding profile carries just that: the
# reasoning effort every coding task runs at. Sampling fields beyond effort
# are NOT passable at the `hermes chat` boundary and stay on the server
# launch flags (the coding/default baseline). Absent = the hermes/server
# default — never invented. CLI override for a run:
# `run_bench.py --reasoning <level>` / `run_fixture_suite.py --reasoning <level>`.
coding_reasoning_effort: xhigh   # validated against the vocabulary above;
  # an unknown level fails the run before any task launches.

# Machine-readable — this is what runner/run_bench.py actually reads to
# drive a run. Everything else in this file is human-facing documentation.
orchestration:
  raw_port: 8012          # port benchmark_launch_command binds to; null for
                           # a hosted/API model with no local server at all
  needs_proxy: true        # does bench_local_proxy.py need to sit in front?
  proxy_parser: lfm        # required if needs_proxy: true — must match a
                           # name in runner/bench_local_proxy.py's PARSERS
  proxy_port: 8015         # default; rarely needs changing
  hermes_provider: local-mlx   # must match an entry in
                               # ~/.hermes/profiles/bench/config.yaml,
                               # or null if no coding-suite spot-check
                               # was ever run for this config
  server_binary: null      # optional — a non-default binary path (e.g.
                           # runner/.dflash2-fork/build/bin/llama-server for
                           # a custom-built fork), documentation only; the
                           # actual path used is whatever
                           # benchmark_launch_command invokes
  api_base_url: null       # hosted/API models only (e.g. Luna) — the
                           # provider's base URL instead of a local raw_port
  api_key_env: null        # hosted/API models only — the NAME of an env var
                           # holding the key; the key itself is never written
                           # to this file or passed as a CLI arg anywhere
  viable: full             # full | sanity_and_hermes_ops_only |
                           # sanity_only | coding_only | blocked | retired
                           # — see runner/run_bench.py's docstring for
                           # exactly what each value skips and why. `retired`
                           # (2026-09-04) = engine lane no longer active
                           # (oMLX/vllm-mlx); skipped, kept as evidence.

# Required when inference_engine: omlx. These are first-class experiment factors,
# snapshotted with the config and rendered by build_leaderboard.py so cache /
# acceleration variants cannot be silently averaged or mislabeled.
# NOTE (2026-09-04): the oMLX lane is RETIRED. This schema block is kept for
# historical reproducibility only; no oMLX config is a runnable current path
# (`orchestration.viable: retired` — the runner skips it).
omlx_version: 0.6.2
omlx_commit: f2d36f3d25a7e7a2401a92eecafc28b8f8968ec7
source_revision: <full Hugging Face revision>
quant_family: oQ4e-fp16 mixed precision  # never shorten this to "FP16"
context_cap: 65536
cache_mode: cold                         # cold | hot | ssd
mtp_mode: off                            # off | lightning
tool_call_path: native_omlx_validated    # only after stream + non-stream probes
# orchestration.served_model_id is the exact local directory/API identity.
# oMLX does not necessarily expose the source repository ID in /v1/models.

settings:
  - name: max_tokens
    value: 4096
    source: "chosen at launch time, not model-card-derived — flagged as a
      possible bottleneck, revisit"
  - name: tool_call_parser
    value: lfm    # must match a parser registered in runner/bench_local_proxy.py's PARSERS dict
    source: "https://..."   # the model's raw tool-call text format, from its model
      card / creator docs. vllm-mlx 0.4.1+ does have native tool-call
      parsers (--enable-auto-tool-choice --tool-call-parser <name> via the
      `vllm-mlx serve` CLI), but this benchmark still uses its own proxy
      for models needing complex formats — the native qwen3_coder parser
      has a confirmed real bug in streaming mode specifically (see
      AGENTS.md), which the proxy structurally can't hit since it always
      parses the complete non-streaming response. Getting a parser wrong
      doesn't error — it just silently produces 0 tool calls or
      hallucinated ones, so verify against a real raw response from the
      loaded model before trusting a new parser (both streaming and
      non-streaming, if a native parser is ever used instead of the proxy).

last_updated: 2026-08-20
last_verified_against_docs: 2026-08-20   # bump when re-checked — configs go stale
```

### Request-time generation profiles: policy and compatibility notes

- **Request-time override, not a new baseline.** `generation_profiles` /
  `hermes_ops_generation_profile` only override sampling/reasoning settings
  on the one-shot prompt-suite path (sanity/hermes_ops's run_prompt.py
  client), and `coding_reasoning_effort` only sets `hermes chat
  --reasoning` on the coding path. The server launch flags in
  `benchmark_launch_command` remain the coding/default baseline. When a
  profile does not declare a field, that field is not sent and the backend
  uses its own launch/default value — including temperature: a selected
  profile without `temperature` sends NO temperature field (never a
  silent fallback to the historic temperature=0), while a run with NO
  profile selected keeps the historic deterministic temperature=0 exactly
  (run_prompt_suite.py passes `--temperature 0` explicitly in that case).
- **`max_tokens` is deliberately not a profile field.** `hermes_ops_max_tokens`
  remains the single config source for the one-shot client's completion cap
  (see above); a profile that contains `max_tokens` fails validation so
  there can never be two competing max-token sources.
- **No `enable_thinking` / `chat_template_kwargs` field.** Mei's
  `ChatRequest` has no arbitrary `chat_template_kwargs` and silently drops
  unknown JSON keys, so a top-level `enable_thinking` boolean could only be
  honored by llama.cpp — not representable safely for both active engines.
  The backend-neutral way to disable thinking per-request is
  `reasoning_effort: none` (Mei passes it into the chat template's
  additionalContext and disables thinking when `--enable-thinking` is
  unset; llama.cpp's exact handling depends on its chat template). For
  forcing thinking on, keep using the server-side `--enable-thinking`
  launch flag.
- **Sanity is never affected.** `run_bench.py --generation-profile` is
  forwarded to the hermes_ops stage only; the sanity suite (determinism
  gate) always runs at the historic defaults.
- **Coding rows record the effective effort.** `run_fixture_suite.py` log
  rows carry `reasoning_effort` = the exact `hermes chat --reasoning`
  level that row's agent ran at (or `null` when the hermes/server default
  applied), so an effort-lane change can never silently contaminate
  historical comparisons.
- **Backward compatibility is byte-level.** A config without these keys —
  or with profiles declared but none selected — produces exactly the same
  HTTP body it always has (temperature 0, max_tokens, nothing else), so old
  configs and old `results/log.jsonl` rows are unaffected. The capability/
  practical lane split is an evaluation-methodology choice for future runs;
  this schema change is infrastructure only.
- **Rows record the resolved lane immutably (2026-09-22).** Every prompt-suite
  row now carries `generation_profile` (the selected profile name, or
  `null` for the historic no-profile lane), `generation_overrides` (the
  exact profile fields resolved and forwarded to run_prompt.py, or `null`),
  and `generation` (the exact sampler/effort fields the backend actually
  received for the first turn — `{"temperature": 0}` on the no-profile
  lane). Coding-suite rows carry `reasoning_effort` (see above) and each
  transcript header shows the exact `hermes chat --reasoning` invocation.
  Together with `config_hash` (the immutable snapshot of the config that
  declared the profiles) a row can always be reconstructed to the exact
  operating point it ran at — never re-derived from possibly-edited live
  config state.

### Policy-enabled configs (front-runners, 2026-09-22)

The infrastructure above is exercised by explicit per-front-runner POLICY
(durable plan 7f5c67e7-b564-4df3-8209-14f7443b56e2: explicit general/vendor
defaults for Hermes Ops, model-specific coding profiles, explicit
high/xhigh capability-ceiling overlays, explicit medium comparison overlays,
never silently invent sampler or effort values). Each config below declares
`generation_profiles` (`capability` + `practical`), selects `capability` as
its `hermes_ops_generation_profile`, and declares `coding_reasoning_effort`
— every value cited to its vendor/model-card source in that config's own
`settings/generation_profiles_policy` entry:

| Config | Engine | capability lane (Hermes Ops default) | practical/medium lane | coding effort |
|---|---|---|---|---|
| `Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml` | llama.cpp-prism | card Thinking-Mode preset (1.0/0.95/20/0) + **xhigh** (card default) | same sampling + **medium** (card: supported) | xhigh (card default; coding gated pending hermes_provider) |
| `Ornith-1.5-35B-A3B/mei.yaml` | mei | card general preset (0.6/0.95/20) + **medium** (card silent on effort) | identical (card defines no second point) | medium |
| `Ornith-1.5-35B-A3B/gguf.yaml` | llama.cpp | card general preset (0.6/0.95/20) + **medium** | identical | medium |
| `Qwen3.6-35B-A3B/mei.yaml` | mei | unsloth thinking precise-coding preset (0.6/0.95/20/0/presence 0/rep 1.0) + **medium** (card silent on effort) | identical | medium |
| `Qwen3.6-35B-A3B-textonly/mei.yaml` | mei | same preset + medium | identical | medium |
| `Qwen3.6-35B-A3B/gguf-official-q4km.yaml` | llama.cpp | same preset + medium | identical | medium |
| `Qwen3.8-27B/gguf.yaml` | llama.cpp | thinking preset (1.0/0.95/20/0/presence 0/rep 1.0) + **xhigh** (template max mapping) | same sampling + **medium** (= historical template-default baseline) | medium (= historical baseline) |
| `Qwen3.8-27B/mei.yaml` | mei | same as gguf sibling + xhigh | same sampling + medium | medium |

Notes:

- **`medium` where the vendor is silent on effort is an explicit plan
  decision, not an invention.** For models whose cards document no effort
  level (Ornith, Qwen3.6), `reasoning_effort: medium` is the plan's
  sanctioned default and each config records it out loud with its source.
  This per-model resolution supersedes the blanket "do not globally force
  `reasoning_effort=medium`" note in `docs/OMLX_MODEL_MATRIX.md`, which is
  historical research for the RETIRED oMLX lane and predates the plan.
- **`hermes_ops_generation_profile: capability` changes future hermes_ops
  rows** for these configs (vendor operating point instead of the historic
  temperature=0 wire shape). Historic rows are append-only and untouched;
  the change is explicit in each config's config_hash snapshot and recorded
  per row.
- **Configs not listed here have no policy yet** — they keep the historic
  no-profile behavior exactly until their own lane policy is written
  (next-step work; no values are guessed for them).

## Process for adding a new model+inference-engine config

1. Check the model's HuggingFace model card / creator blog / GitHub README
   for recommended inference settings (temperature, top_p, chat template,
   tool-call format, context length).
2. Check the serving framework's own docs (`vllm-mlx` README/PyPI,
   `llama.cpp` server docs / `llama-server --help`, or the pinned oMLX
   checkout plus `omlx serve --help`) for available tuning
   flags — don't assume the currently-running launch command is already
   optimal, it may just be whatever was convenient to start with.
3. Fill in `settings:` with real citations (URLs). If nothing authoritative
   exists for a setting, say so explicitly (`source: "framework default, no
   model-specific guidance found"`) rather than inventing a plausible value.
4. Every `results/log.jsonl` row records `config_path`, a content hash of
   that file (`config_hash`), and the harness's own git sha (`runner_git_sha`)
   for the run. The exact config content is also snapshotted verbatim to
   `results/configs/<config_hash>.yaml` at run time (`runner/
   bench_common.py:snapshot_config()`) — the hash alone is not enough to
   reconstruct what was run, since the live config file gets edited again
   afterward; the snapshot is what actually stays traceable.
5. For active native-serving engines, run the engine's acceptance probe before
   accepting benchmark rows. For **Mei** (the supported active native-Swift-MLX
   lane), run `runner/run_mei_acceptance.py --config configs/<model>/mei.yaml`
   (which drives `runner/probe_mei.py`): it proves exact served identity, a
   real generation, native streaming/non-streaming structured calls against the
   benchmark's `add_numbers` schema, the exact context-cap gate, and cache/timing
   metrics. The oMLX probe (`probe_omlx.py`) was removed with that lane's
   retirement (2026-09-04).

## Config files

One directory per model family, `gguf.yaml`/`mei.yaml`/`mlx.yaml` (or a variant
name, e.g. `gguf-unsloth-ud-q4.yaml`, for a distinct quant/engine combo) inside.
`mlx.yaml` (vllm-mlx) and every `omlx*.yaml` are **retired active lanes
(2026-09-04)** — kept as historical evidence, skipped by the runner. Active
configs are marked `viable: full`; retired ones carry `viable: retired`:

- `LiquidAI-LFM2.5-2.6B/` — gguf, mlx
- `LiquidAI-LFM2.5-8B-A1B/` — gguf, mlx, gguf-dspark (speculative decoding,
  needs `runner/setup_dspark_head.sh` — mainline llama.cpp built from
  source, since the LFM2-specific support merged after the Homebrew bottle)
- `Qwen3.8-27B/` — gguf, mlx, gguf-unsloth-ud-q4, gguf-unsloth-ud-q2,
  gguf-dflash2 (speculative decoding, needs `runner/setup_dflash2_fork.sh`)
- `Qwen3.8-27B-Ridge/` — gguf (empero-ai's GDN-aware quant, a different
  release from `Qwen3.8-27B/` above, not a variant of it)
- `Qwen3.5-9B/` — gguf
- `Qwen3-Coder-30B-A3B/` — gguf, mlx
- `Ternary-Bonsai-27B/` — mlx (native 2-bit ternary training)
- `Ornith-1.5-35B-A3B/` — gguf
- `Muse-Glimmer-30B/` — gguf, gguf-dflash2 (speculative decoding, shares the
  fork build with `Qwen3.8-27B/gguf-dflash2.yaml`)
- `Laguna-XS-2.1/` — gguf (mlx is `viable: blocked` — see AGENTS.md)
- `Luna/` — api (hosted, via hermes's `openai-codex` OAuth provider — see
  AGENTS.md for why this path is ToS-sensitive), openrouter (the preferred
  path going forward: a real API key, full suite coverage, cost tracking)

See the top-level `README.md` for how to run any/all of these, and
`AGENTS.md` for the reasoning behind every non-obvious setting.

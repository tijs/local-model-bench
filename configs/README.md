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
inference_engine: vllm-mlx        # vllm-mlx | llama.cpp | llama.cpp-dflash2 |
                                  # llama.cpp-dspark | omlx | openrouter |
                                  # hermes-openai-codex — the inference
                                  # engine identity; primary grouping key
                                  # for build_leaderboard.py
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
                           # sanity_only | coding_only | blocked
                           # — see runner/run_bench.py's docstring for
                           # exactly what each value skips and why

# Required when inference_engine: omlx. These are first-class experiment factors,
# snapshotted with the config and rendered by build_leaderboard.py so cache /
# acceleration variants cannot be silently averaged or mislabeled.
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
5. For oMLX, run `runner/probe_omlx.py` before accepting benchmark rows. It
   proves exact identity, cold generation, native streaming/non-streaming
   structured calls against the benchmark's `add_numbers` schema, exact
   65,536-token success plus over-cap rejection, and cache/timing metrics.

## Config files

One directory per model family, `gguf.yaml`/`mlx.yaml` (or a variant name,
e.g. `gguf-unsloth-ud-q4.yaml`, for a distinct quant/engine combo) inside:

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

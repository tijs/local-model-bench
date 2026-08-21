# Run configs

One file per model+backend combo: `configs/<model-slug>/<backend>.yaml`
(`backend` is `mlx` or `gguf`). Documents the exact serving/inference
settings used for benchmark runs against that model — each setting with a
citation, so results are auditable and reproducible, and so a value is never
just "chosen because it seemed right" without saying so explicitly.

## Schema

```yaml
model: LiquidAI/LFM2.5-2.6B-MLX-bf16
backend: mlx
framework: vllm-mlx              # vllm-mlx | llama.cpp
launch_command: |
  python -m vllm_mlx.server --model LiquidAI/LFM2.5-2.6B-MLX-bf16 \
    --host 127.0.0.1 --port 8012 --max-request-tokens 4096 --max-tokens 4096

# Machine-readable — this is what runner/run_bench.py actually reads to
# drive a run. Everything else in this file is human-facing documentation.
orchestration:
  raw_port: 8012          # port benchmark_launch_command binds to
  needs_proxy: true        # does bench_local_proxy.py need to sit in front?
  proxy_parser: lfm        # required if needs_proxy: true — must match a
                           # name in runner/bench_local_proxy.py's PARSERS
  proxy_port: 8015         # default; rarely needs changing
  hermes_provider: local-mlx   # must match an entry in
                               # ~/.hermes/profiles/bench/config.yaml,
                               # or null if no coding-suite spot-check
                               # was ever run for this config
  viable: full             # full | sanity_and_hermes_ops_only |
                           # sanity_only | coding_only | blocked
                           # — see runner/run_bench.py's docstring for
                           # exactly what each value skips and why

settings:
  - name: max_tokens
    value: 4096
    source: "chosen at launch time, not model-card-derived — flagged as a
      possible bottleneck, revisit"
  - name: temperature
    value: 0
    source: "https://huggingface.co/LiquidAI/..."   # a real URL, not a guess
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

## Process for adding a new model+backend config

1. Check the model's HuggingFace model card / creator blog / GitHub README
   for recommended inference settings (temperature, top_p, chat template,
   tool-call format, context length).
2. Check the serving framework's own docs (`vllm-mlx` README/PyPI, or
   `llama.cpp` server docs / `llama-server --help`) for available tuning
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

## Config files

One directory per model family, `gguf.yaml`/`mlx.yaml` (or a variant name,
e.g. `gguf-unsloth-ud-q4.yaml`, for a distinct quant/backend combo) inside:

- `LiquidAI-LFM2.5-2.6B/` — gguf, mlx
- `LiquidAI-LFM2.5-8B-A1B/` — gguf, mlx
- `Qwen3.8-27B/` — gguf, mlx, gguf-unsloth-ud-q4, gguf-unsloth-ud-q2,
  gguf-dflash2 (speculative decoding, needs `runner/setup_dflash2_fork.sh`)
- `Qwen3.5-9B/` — gguf
- `Qwen3-Coder-30B-A3B/` — gguf, mlx
- `Ternary-Bonsai-27B/` — mlx (native 2-bit ternary training)
- `Ornith-1.5-35B-A3B/` — gguf
- `Muse-Glimmer-30B/` — gguf
- `Laguna-XS-2.1/` — gguf (mlx is `viable: blocked` — see AGENTS.md)
- `Luna/` — api (hosted, via hermes's `openai-codex` OAuth provider, not a
  local server at all)

See the top-level `README.md` for how to run any/all of these, and
`AGENTS.md` for the reasoning behind every non-obvious setting.

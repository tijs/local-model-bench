# oMLX model coverage and settings matrix

Research date: 2026-08-21

Target hardware: Sulaco, Apple M1 Max, 32 GB unified memory, `hw.optional.arm.FEAT_BF16=0`.

Pinned runtime: oMLX 0.6.2 (`f2d36f3d25a7e7a2401a92eecafc28b8f8968ec7`), MLX 0.32.0, mlx-lm 0.31.3 (`ab1806e8f5d6aa035973af194a1b9198ab4754dc`).

This file is the source-of-truth handoff for model selection, quant provenance, settings, and reruns. It records research findings; live load and benchmark results must be added only from actual runner artifacts.

For oMLX's engine-level bugs, the broader MLX-vs-GGUF speed investigation, and how oMLX compares to vllm-mlx and other MLX serving engines, see [`INFERENCE_ENGINES.md`](INFERENCE_ENGINES.md) — this file stays scoped to per-model settings and provenance.

## Live verification summary (2026-08-21)

- `results/omlx/staging-manifest.json` records nine staged immutable snapshots:
  all three first-wave artifacts plus six compatible existing-model-list MLX
  controls. They are symlinked into the isolated oMLX model root, so 112.88 GB
  of logical artifacts do not consume a duplicate 112.88 GB of disk.
- Every staged model cold-loaded and passed exact served-ID membership, plain
  completion, and streaming/non-streaming schema-checked tool calls. Raw JSON,
  process, health, launcher, and isolated server evidence is under
  `results/omlx/acceptance/`.
- LFM and Ornith completed an exact 65,536-token prompt and rejected 65,537.
  Qwen's 17.9 GB artifact correctly rejected 65,536 in safe mode; balanced
  mode reached 15,296 tokens but hit the 23.7 GB hard watermark under Apple's
  24.96 GB Metal cap. The exact `prefill_memory_aborted` rerun is retained in
  `results/omlx/acceptance-rerun/` rather than being reported as model quality.
- Qwen and Ornith hot/SSD probes reused 6,144 prefix tokens. Qwen SSD state
  survived a server restart. LFM's hybrid GDN cache rejected structurally stale
  recurrent checkpoints and safely re-prefilled; its hot/SSD logs retain the
  warning and zero-hit metrics.
- Qwen Lightning MTP was tested at reasoning efforts `medium` and `xhigh`.
  Both structured-tool probes passed, and server logs prove the MTP model and
  VLM runtime patches plus Lightning activation (`draft_tokens=3`).

## Compatibility conclusions

- oMLX/mlx-lm loads MLX safetensors (`model*.safetensors`); GGUF support in mlx-lm is export/conversion support, not GGUF import. Existing `:Q*_K_*` and `:Q8_0` GGUF rows therefore need an architecture-matched MLX/oQ replacement.
- Directly supported model types in the pinned stack include `lfm2`, `lfm2_moe`, `qwen3_moe`, `qwen3_5`, and `qwen3_5_moe`. oMLX 0.6.2 additionally has Laguna, Muse Glimmer, Bonsai ternary, oQ/OptiQ, and MTP loading paths that require live validation.
- `oQ4e-fp16` and `oQ4-fp16` are mixed-precision quant families, not pure FP16 controls. Keep those labels exact.
- Cold, MTP-off, standard-KV runs are the canonical quality baseline. Hot/SSD prefix cache, TurboQuant KV, DFlash, and MTP are separate experiment factors.
- The benchmark context cap of 65,536 is an operator/hardware cap, not the model-author context recommendation. Most candidates advertise 128K-262K; Qwen3.5 guidance prefers at least 128K for thinking quality.

## Existing model-list disposition

| Existing entry | Current artifact/runtime | oMLX disposition |
|---|---|---|
| `qwen38-oq4e-mtp` | `Jundot/Qwen3.8-27B-oQ4e-fp16-mtp`, oQ MLX safetensors with MTP tensors | **Unchanged**, MTP-off baseline then Lightning MTP |
| `lfm25-8b-oq4` | `RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16`, oQ MLX safetensors | **Unchanged only for archived local bytes**; old configured revision is gone from HF |
| `ornith15-9b-oq4e` | `scottlowry/Ornith-1.5-9B-oQ4e-fp16`, oQ MLX safetensors | **Unchanged only for archived local bytes**; old configured revision is gone from HF |
| `qwen3-coder-mlx` | `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` | **Unchanged**, `qwen3_moe`, non-thinking, no MTP |
| `lfm25-2.6b-mlx` | `LiquidAI/LFM2.5-2.6B-MLX-bf16` | **Unchanged**, `lfm2`; measure BF16 performance on M1 |
| `qwen38-mlx` | `mlx-community/Qwen3.8-27B-4bit` | **Unchanged**, `qwen3_5`, no MTP tensors |
| `ternary-bonsai-mlx` | `prism-ml/Ternary-Bonsai-27B-mlx-2bit` | **Unchanged if local artifact is accessible**; preserve hashes because HF access became gated |
| `lfm25-8b` | `LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M` | **Swap** to official BF16 MLX or the oQ artifact |
| `laguna-xs-21` | `unsloth/Laguna-XS-2.1-GGUF:Q4_K_M` | **Swap** to `mlx-community/Laguna-XS-2.1-4bit` or its OptiQ variant |
| `muse-glimmer-30b` | `unsloth/Muse-Glimmer-30B-GGUF` | **Swap** to `Jundot/Muse-Glimmer-30B-oQ4e` or MLX OptiQ |
| `ornith15-35b-a3b` | `ornith-ai/Ornith-1.5-35B-A3B-GGUF` | **Swap** to `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`; optional oQ/MTP row |
| `qwen35-9b` | `bartowski/Qwen_Qwen3.5-9B-GGUF` | **Swap** to plain MLX or an MTP-preserving oQ conversion |
| `qwen38-ridge` | `empero-ai/Qwen3.8-27B-Ridge-GGUF` | **Exclude for now**; no source safetensors/MLX checkpoint found |
| `lfm25-8b-dspark` | hosted llama.cpp/DSpark GGUF | **Swap only for model-quality testing**; DSpark is not an oMLX-equivalent acceleration row |
| `luna`, `luna-openrouter`, `gpt54`, `gpt54-mini` | hosted APIs, no local weights | **Exclude** |

## Exact MLX/oQ candidates and provenance

| Family | Candidate revision | Notes |
|---|---|---|
| LFM2.5-2.6B | `LiquidAI/LFM2.5-2.6B-MLX-bf16@f2d32094cdd69ed7adb85a4b44accfc8770cd655` | 5.394 GB, `lfm2`, BF16 |
| LFM2.5-2.6B compact | `mlx-community/LFM2.5-2.6B-OptiQ-4bit@7cfc3c1bd3ad412266685b2b51f0209ec6492f29` | 1.992 GB, expected compatible; live validation required |
| LFM2.5-8B-A1B BF16 | `LiquidAI/LFM2.5-8B-A1B-MLX-bf16@f249fa04c32c629c9156e0e1e4ca139b8c06c4f2` | 16.956 GB, `lfm2_moe`; M1 BF16 speed uncertain |
| LFM2.5-8B-A1B oQ current | `RepublicOfKorokke/LFM2.5-8B-A1B-oQ4-fp16@c6d776a30db23fc34644ec8625ed1f0b1d51bfa1` | 4.977 GB; do not conflate with the old staged `fd841...` revision |
| Laguna | `mlx-community/Laguna-XS-2.1-4bit@c42e0a8f8d504ceacde015a535dcb286d65c8799` | 18.822 GB, `laguna`; best 32 GB candidate |
| Laguna tested OptiQ | `mlx-community/Laguna-XS-2.1-OptiQ-4bit@cda048c0262dfd0f0847d10b1bd725877547434a` | 20.998 GB; more integration-test confidence, less memory headroom |
| Muse Glimmer | `Jundot/Muse-Glimmer-30B-oQ4e@5de983b74221d7e249e8e2ecc25c51f184b1cf11` | 20.256 GB, `muse_glimmer`; memory-tight with assistant |
| Ornith-1.5-9B current | `scottlowry/Ornith-1.5-9B-oQ4e-fp16@5a886bbb0c202641e3c278cb4001058f2420827a` | 6.945 GB; old `745bf8...` revision returns 404 |
| Ornith-1.5-35B | `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit@19504d912fa8fc7622bf6b1de3db5d5d890b1f02` | 19.509 GB, `qwen3_5_moe`; no MTP |
| Ornith-35B MTP | `scottlowry/Ornith-1.5-35B-A3B-oQ4e-mtp@5465dc4cfc70aefda40177ffacd5e5cde27c2a0d` | 21.613 GB; separate MTP experiment, memory-tight |
| Qwen3 Coder | `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit@6e302ea604ad9ab206367e2c501d1571023e7b6d` | 17.181 GB, `qwen3_moe`, no MTP |
| Qwen3.5-9B MTP | `scottlowry/Qwen3.5-9B-oQ4e-fp16-mtp@db0c65f3a962963554acb5f5922b3028f89d4565` | 7.143 GB; community conversion, validate load/MTP parity |
| Qwen3.8 standard | `mlx-community/Qwen3.8-27B-4bit@3e6447f082e89cc7f0bc6e5441afd38dfce760ff` | 16.054 GB, no MTP |
| Qwen3.8 oQ/MTP | `Jundot/Qwen3.8-27B-oQ4e-fp16-mtp@569439f7b576fcb8795258855466fee2acd8ea70` | 17.893 GB; best-supported Qwen MTP candidate |
| Ternary Bonsai | `prism-ml/Ternary-Bonsai-27B-mlx-2bit@70f75f3ad081ab840a42f3304c02c27e7f89bfb7` | 8.491 GB; preserve local artifact/hash if HF remains gated |

The old first-wave LFM and Ornith revisions were reported as HF 404. If using the current remote revisions, create new benchmark rows and do not claim byte identity with the old staged artifacts.

## Source-backed settings

Values marked as author/model-card guidance must be recorded separately from framework defaults and must be validated live.

| Family | Recommended sampling | Reasoning/context | Tools and special settings |
|---|---|---|---|
| LFM2.5-2.6B | `temperature=.1`, `top_k=50`, `repetition_penalty=1.1` | 131,072 context; pure reasoning, always reasons; author says not recommended for agentic coding | Pythonic tool calls; oMLX `lfm2` parser; no reasoning effort |
| LFM2.5-8B-A1B | `temperature=.2`, `top_k=80`, `repetition_penalty=1.05` | 128,000 context; always reasons; no effort toggle | Pythonic parser; no MTP |
| Laguna-XS-2.1 | `temperature=1.0`, `top_k=20`, `top_p=1.0` | 262,144 context; thinking/preserved thinking works best | oMLX Laguna parser; probe both stream paths; standard KV baseline; DFlash separate |
| Muse Glimmer 30B | `temperature=1.0`, `top_p=.95`, `top_k=64` | 131,072+ context; `reasoning_strength=high` or `xhigh` for coding | ATEM tool format and dedicated Muse parser; do not call this `reasoning_effort` |
| Ornith-1.5-9B | General `1/.95/20/min_p=0/presence=1.5/repetition=1`; coding `.6/.95/20/0/presence=0/repetition=1` | Qwen3.5-derived thinking template; native 262K | Qwen3-Coder parser; keep reasoning separate; if disabling thinking, set `enable_thinking=false` explicitly |
| Ornith-1.5-35B | General `.6/.95/20`; reported benchmark runs also use `temperature=1` | Qwen3.5-MoE, native 262K | Qwen3-Coder parser; standard and oQ/MTP rows separate |
| Qwen3 Coder 30B | `.7/.8/20`, `repetition_penalty=1.05` | Native 262,144; non-thinking only; 32,768 is fallback for OOM | Specialized Qwen3-Coder tools; no MTP; validate streamed fragmented calls |
| Qwen3.5-9B | Thinking `1/.95/20/min_p=0/presence=1.5/repetition=1`; precise coding `.6/.95/20/0/presence=0/repetition=1`; instruct `.7/.8/20/0/presence=1.5/repetition=1` | Thinking default, native 262,144; 65,536 is a constrained operator test | `enable_thinking` and reasoning extraction; validate community MTP conversion |
| Qwen3.8-27B | Thinking `1/.95/20/min_p=0/presence=0/repetition=1`; instruct `.7/.8/20/0/presence=1.5/repetition=1` | Thinking default, native 262,144; `reasoning_effort` supports `xhigh`, `medium`, `low` | Qwen parser; `reasoning_mode=thinking` plus separate `reasoning_effort=medium`; only MTP artifact gets MTP |
| Ternary Bonsai 27B | oMLX benchmark example `.7/.95/20/min_p=0/repetition=1/presence=0` | Qwen3.5-derived thinking, 262K | Qwen parser; standard KV baseline, TurboQuant 3.5-bit separate and experimental |

Do not globally force `reasoning_effort=medium`: it is appropriate for Qwen3.8, but not for LFM, Qwen Coder, Laguna, Muse (`reasoning_strength`), Ornith, Qwen3.5, or Bonsai. Do not label an Ornith run `instruct` unless `enable_thinking=false` is actually sent and verified.

## Required acceptance and reproducibility fields

Every benchmark row must record:

- Hardware model/RAM/macOS build/`hw.optional.arm.FEAT_BF16`.
- oMLX, MLX, mlx-lm, mlx-vlm, Transformers versions and immutable oMLX commit.
- HF repo ID, immutable revision, local weight byte count, and SHA-256 for `config.json`, tokenizer/template files, index, and every safetensor shard.
- `model_type`, architectures, quantization metadata, per-layer override count, and MTP tensor count.
- Stable served model ID and local path.
- Temperature, top-p, top-k, min-p, repetition/presence penalties, seed, and whether sampling was forced.
- `reasoning_mode`, `enable_thinking`, `preserve_thinking`, `reasoning_effort` or `reasoning_strength`, and all forced template kwargs.
- Native context, operator context cap, max output, and whether the cap is prompt-only or total.
- Tool/reasoning parser; non-streaming and streaming structured-call results, including fragmented names/JSON, `finish_reason=tool_calls`, tool-result follow-up, and final answer.
- Cache mode and limits, hot/SSD paths, TurboQuant settings, cache-hit metrics.
- MTP enabled state, draft-token count, acceptance/depth statistics, and any batch fallback.
- Concurrency, memory guard, trust-remote-code setting, exact launch command/environment, config snapshot/hash, runner revision, trials, timestamps, and server log path.

## Sequential matrix

Run one server at a time with `max_concurrent_requests=1`, cold baseline first:

1. LFM2.5-8B oQ: cold, author sampling, Pythonic tools, 65,536 cap; resolve provenance first.
2. Ornith-9B oQ: thinking or explicit disabled-thinking row; validate Qwen parser and provenance.
3. Qwen3.8 oQ/MTP: MTP off then on with identical settings; require activation/parity evidence.
4. First-wave survivors: hot then SSD cache with unchanged sampling; require nonzero repeated-prefix cache metrics.
5. LFM2.5-2.6B BF16 control.
6. Qwen3.5-9B oQ/MTP.
7. Ternary Bonsai standard KV, then optional TurboQuant.
8. Qwen3 Coder 4-bit.
9. Qwen3.8 standard 4-bit, MTP off.
10. Laguna 4-bit, then optional DFlash if memory permits.
11. Ornith-35B standard, then optional oQ/MTP if memory permits.
12. Muse Glimmer oQ, then optional DFlash only with explicit memory gate.

Use at least three trials for stochastic quality runs. Keep acceleration comparisons paired on the same artifact, prompts, sampling, template kwargs, and output cap. Regenerate reports from result logs; never hand-edit leaderboard rows.

## Reproducible commands

Stage an immutable artifact and hash it:

```bash
REPO='Jundot/Qwen3.8-27B-oQ4e-fp16-mtp'
REV='569439f7b576fcb8795258855466fee2acd8ea70'
DEST="$HOME/.local/share/local-model-bench/omlx-models/qwen38-27b-oq4e-fp16-mtp"
hf download "$REPO" --revision "$REV" --local-dir "$DEST"
find "$DEST" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$DEST/SHA256SUMS"
```

The two dead first-wave revisions must not be used as if they were reproducible. Select a resolvable revision or preserve the local bytes and checksums as an explicitly archived artifact.

Canonical first benchmark:

```bash
uv run --locked python runner/run_bench.py \
  --config configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx.yaml \
  --trials 3 \
  --coding-suites kiem_mini,hearth_mini,kipclip_mini
```

Run the MTP config only after the MTP-off probe passes; run hot/SSD cache variants only after the identical-prefix probe demonstrates cache hits. Any config launch command must match the installed `runner/start_omlx_server.sh` CLI. The wrapper now accepts `--cache-dir`; all cache experiments must pass it explicitly so SSD state is isolated and restart behavior is reproducible.

## Sources

- [oMLX v0.6.2](https://github.com/jundot/omlx/tree/v0.6.2)
- [oMLX pinned dependencies](https://github.com/jundot/omlx/blob/v0.6.2/pyproject.toml)
- [mlx-lm v0.31.3 model implementations](https://github.com/ml-explore/mlx-lm/tree/v0.31.3/mlx_lm/models)
- [mlx-lm loader](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/utils.py)
- [oMLX model loading patches](https://github.com/jundot/omlx/blob/v0.6.2/omlx/utils/model_loading.py)
- [oMLX MTP patch](https://github.com/jundot/omlx/tree/v0.6.2/omlx/patches/mlx_lm_mtp)
- [oMLX tokenizer adaptation](https://github.com/jundot/omlx/blob/v0.6.2/omlx/utils/tokenizer.py)
- [oMLX Bonsai kernels](https://github.com/jundot/omlx/tree/v0.6.2/omlx/custom_kernels)
- [LiquidAI/LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B)
- [LiquidAI/LFM2.5-8B-A1B](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B)
- [poolside/Laguna-XS-2.1](https://huggingface.co/poolside/Laguna-XS-2.1)
- [meta-models/Muse-Glimmer-30B](https://huggingface.co/meta-models/Muse-Glimmer-30B)
- [ornith-ai/Ornith-1.5-9B](https://huggingface.co/ornith-ai/Ornith-1.5-9B)
- [ornith-ai/Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B)
- [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)
- [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- [oMLX Bonsai benchmark example](https://omlx.ai/benchmarks/bvpkejeo)

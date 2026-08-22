# oMLX benchmark result summary

Generated from `results/log.jsonl`, current config hashes, and black-box acceptance artifacts.

- oMLX log rows: 80
- Current oMLX configs: 18
- Cold-loaded staged models: 9

## Cold load and structured-tool acceptance

| served ID | status | cold load (s) | plain | tool non-stream | tool stream | 65,536 | 65,537 rejected |
|---|---:|---:|---:|---:|---:|---:|---:|
| laguna-xs-21-mlx-4bit | passed | 8.91 | passed | passed | passed | not run (control) | not run (control) |
| lfm25-26b-mlx-bf16 | passed | 2.08 | passed | passed | passed | not run (control) | not run (control) |
| lfm25-8b-a1b-mlx-bf16 | passed | 6.87 | passed | passed | passed | not run (control) | not run (control) |
| lfm25-8b-a1b-oq4-fp16 | passed | 2.13 | passed | passed | passed | passed | passed |
| ornith-15-9b-oq4e-fp16 | passed | 2.69 | passed | passed | passed | passed | passed |
| qwen3-coder-30b-a3b-4bit | passed | 5.49 | passed | passed | passed | not run (control) | not run (control) |
| qwen38-27b-mlx-4bit | passed | 6.74 | passed | passed | passed | not run (control) | not run (control) |
| qwen38-27b-oq4e-fp16-mtp | failed | 8.03 | passed | passed | passed | failed | passed |
| ternary-bonsai-27b-mlx-2bit | passed | 3.21 | passed | passed | passed | not run (control) | not run (control) |

## Current-config benchmark rows

| config | cache | MTP | viable | tasks | passes | latest task outcomes |
|---|---|---|---|---:|---:|---|
| `configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx-hot.yaml` | hot | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx-ssd.yaml` | ssd | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/LFM2.5-8B-A1B-oQ4e-fp16/omlx.yaml` | cold | off | full | 6 | 4 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=FAIL; kiem_mini kiem_mini-feature=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Laguna-XS-2.1/omlx.yaml` | cold | off | full | 6 | 4 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=FAIL; kiem_mini kiem_mini-feature=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/LiquidAI-LFM2.5-2.6B/omlx.yaml` | cold | off | sanity_and_hermes_ops_only | 5 | 4 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/LiquidAI-LFM2.5-8B-A1B/omlx.yaml` | cold | off | sanity_and_hermes_ops_only | 5 | 5 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=PASS; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Ornith-1.5-9B-oQ4e-fp16/omlx-hot.yaml` | hot | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Ornith-1.5-9B-oQ4e-fp16/omlx-ssd.yaml` | ssd | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Ornith-1.5-9B-oQ4e-fp16/omlx.yaml` | cold | off | full | 6 | 5 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=PASS; kiem_mini kiem_mini-feature=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3-Coder-30B-A3B/omlx.yaml` | cold | off | sanity_and_hermes_ops_only | 2 | 1 | sanity sanity-basic=PASS,sanity-tool=FAIL |
| `configs/Qwen3.8-27B/omlx.yaml` | cold | off | sanity_and_hermes_ops_only | 5 | 2 | hermes_ops hermes_ops-selection=FAIL,hermes_ops-chaining=FAIL,hermes_ops-error-recovery=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-context-balanced.yaml` | cold | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-hot.yaml` | hot | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp-xhigh.yaml` | cold | lightning | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-mtp.yaml` | cold | lightning | full | 6 | 2 | hermes_ops hermes_ops-selection=FAIL,hermes_ops-chaining=FAIL,hermes_ops-error-recovery=FAIL; kiem_mini kiem_mini-feature=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx-ssd.yaml` | ssd | off | sanity_only | 2 | 2 | sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Qwen3.8-27B-oQ4e-fp16-mtp/omlx.yaml` | cold | off | full | 6 | 2 | hermes_ops hermes_ops-selection=FAIL,hermes_ops-chaining=FAIL,hermes_ops-error-recovery=FAIL; kiem_mini kiem_mini-feature=FAIL; sanity sanity-basic=PASS,sanity-tool=PASS |
| `configs/Ternary-Bonsai-27B/omlx.yaml` | cold | off | sanity_and_hermes_ops_only | 5 | 5 | hermes_ops hermes_ops-selection=PASS,hermes_ops-chaining=PASS,hermes_ops-error-recovery=PASS; sanity sanity-basic=PASS,sanity-tool=PASS |

## Long-context and cache evidence

- LFM and Ornith cold probes completed exactly 65,536 prompt tokens and rejected 65,537.
- Qwen safe mode rejected 65,536 because predicted peak 22.18 GB exceeded the 21.60 GB safe prefill cap. Balanced mode then reached 15,296 tokens and returned `prefill_memory_aborted` at 23.9 GB versus the 23.7 GB hard watermark under Apple’s 24.96 GB Metal cap. See `results/omlx/acceptance-rerun/qwen38-27b-oq4e-fp16-mtp/omlx-context-balanced/`.
- Qwen hot cache: 6,144 cached tokens, 53.732s → 1.973s. Qwen SSD restart: first request reused 6,144 tokens.
- Ornith hot cache: 6,144 cached tokens, 15.282s → 0.702s.
- LFM hybrid GDN correctly rejected stale recurrent checkpoints and re-prefilled; its hot/SSD probe logs record zero reused tokens.

## Harness correction

Three coding rows were invalidated after exact mtimes proved child agents had
escaped the disposable workspace: two edited the source fixture and one
created repository-root `src/lib.rs`. The fixture was restored byte-for-byte
from HEAD and the escape artifact was removed. The runner now injects the
absolute disposable root and guards/restores the whole benchmark checkout
(while allowing `results/` and `runner/runs/`). All five coding configurations
were rerun with `--stage coding`; after expanding the guard, LFM was rerun once
more and completed as a valid model-quality FAIL. Latest valid rows are above.

## Skipped model-list entries

- GGUF artifacts are not importable by mlx-lm/oMLX. Existing GGUF-only rows
  (Muse Glimmer, Ornith-35B, Qwen3.5-9B, Qwen Ridge, and the llama.cpp LFM,
  Laguna, DFlash/DSpark variants) therefore remain llama.cpp comparisons, not
  silently converted oMLX rows.
- Hosted/API rows (`luna`, OpenRouter, GPT-5.4 variants) have no local MLX
  artifact and were excluded by design.
- Optional replacement downloads such as Muse oQ, Ornith-35B MLX/MTP, and
  Qwen3.5 MLX were not already-cached model-list artifacts. After staging the
  required downloads only 30 GiB remained, while several replacements are
  19–22 GB each; adding them would violate the 32 GB host's sequential safety
  margin and the task's priority order. The six compatible existing cached
  MLX controls were all staged and cold-probed instead—none were skipped.

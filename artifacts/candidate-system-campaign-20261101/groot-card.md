---
base_model: GrootTeam/Groot-19B-A3B-261023
base_model_relation: quantized
quantization_method: rco
quantization_bits: 4
license: apache-2.0
library_name: mlx-lm
pipeline_tag: text-generation
---

# Groot-19B-A3B-261023-MLX-rco-role-4.5bpw

Role-level RCO (Role-wise Calibration-Optimized) **4.5 bpw** quantization of [GrootTeam/Groot-19B-A3B-261023](https://huggingface.co/GrootTeam/Groot-19B-A3B-261023), built with [rco-mlx](https://github.com/hermitdave/rco-mlx).

Groot-19B-A3B-261023 is a 19B-parameter reasoning MoE with ~3B active parameters per token: 40 layers (10 full-attention + 30 linear-attention Gated DeltaNet), 128 routed experts + 1 shared, top-8 routing, 262K context.

## Results

Measured on held-out text (10 sequences of 1024 tokens from WikiText-2), against BF16:

| Model | Perplexity ↓ | KL vs BF16 ↓ | top-1 vs BF16 ↑ | TPS ↑ | Size |
| --- | --- | --- | --- | --- | --- |
| BF16 (reference) | 15.21 | — | — | 20.6 | 56.2 GB |
| RTN 4-bit (baseline) | 15.94 | 0.0587 | 83.7% | 0.67 | 34.3 GB |
| **RCO 4.5bpw (this model)** | **15.35** | **0.0110** | **91.1%** | **8.9** | **13.1 GB** |

Lower KL and higher top-1 agreement mean the quantized model stays closer to BF16. Perplexity is a teacher-free cross-check.

RCO vs RTN at ~4.5 bpw (positive = better):

| Metric | RTN | RCO | Improvement |
| --- | --- | --- | --- |
| KL vs BF16 (lower better) | 0.0587 | 0.0110 | **+81.2%** |
| Perplexity (lower better) | 15.94 | 15.35 | **+3.7%** |
| top-1 agreement (higher better) | 83.7% | 91.1% | **+7.4 pts** |

### Reading the top-1 number

A raw top-1 figure invites the reading "8.9% of predictions are wrong", which overstates it. Most disagreements are positions where the BF16 model's own distribution is nearly flat, so either token is a plausible continuation.

## Quantization details

- Base: **4.5 bpw target**, group size **64**, mode **affine**
- Router (`mlp.gate`) left **BF16** — low-bit routers degrade expert selection
- MTP head forced to **8-bit**
- Vision tower **BF16** (skipped)
- Effective **6.08 bits/weight** (includes 2×float32 per 64-group scale/bias overhead), 6 shard(s), 13.13 GB

## Usage

```python
from mlx_lm import load, generate

model, tokenizer = load("hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw")
```

```bash
# CLI
mlx_lm.generate --model hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw --prompt "Explain Rayleigh scattering."
```

Requires MLX ≥ 0.27 (Apple Silicon only).

## Reproduction

```bash
# Build error database
python3 src/rco_mlx/scripts/build_error_db_streaming.py --source <model_dir> --output work/error_db_enhanced.json

# Quantize with role-level allocation
python3 examples/pipeline_rco_mlx.py \\
  --source <model_dir> \\
  --output groot-19b-a3b-261023-rco-role-v2 \\
  --model-type qwen3_5_moe \\
  --default-bits 4 \\
  --group-size 64 \\
  --method role-level \\
  --target-bpw 4.5 \\
  --error-db work/error_db_enhanced.json \\
  --max-8bit-pct 30

# Validate
python3 examples/validate_ppl.py groot-19b-a3b-261023-rco-role-v2 --max-samples 10 --max-len 1024
python3 examples/validate_groot.py --model groot-19b-a3b-261023-rco-role-v2 --reference groot-19b-a3b-261023
python3 examples/measure_tps.py --model groot-19b-a3b-261023-rco-role-v2
```

## Limitations

- **Not a fine-tune.** This is a lossy compression of the upstream model. For knowledge-heavy work, pair it with retrieval.
- **4.5 bpw is not free.** See the Results table for the measured gap to BF16.
- **Not evaluated on agentic benchmarks.** The numbers here are perplexity and distributional agreement, not task accuracy.

## Attribution

- **Base model:** [GrootTeam/Groot-19B-A3B-261023](https://huggingface.co/GrootTeam/Groot-19B-A3B-261023)
- **Quantization tool:** [rco-mlx](https://github.com/hermitdave/rco-mlx) (Hermes Agent workflow)
- **Calibration data:** WikiText-2
- **Benchmark harness:** custom PPL/KL/TPS scripts (`rco-mlx` `examples/validate_ppl.py`, `validate_groot.py`, `measure_tps.py`)

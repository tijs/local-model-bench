---
base_model: RecursiveSI/flint
base_model_relation: quantized
library_name: mlx
tags:
- mlx
- oq
- quantized
license: apache-2.0
pipeline_tag: text-generation
---

# flint-oQ2e-fp16

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.3.dev1) mixed-precision quantization.

The effective average is 2.795 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 2-bit, group 64 | 37.849B | 95.134% | 11.016 GiB | 2.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 1.615B | 4.060% | 1.598 GiB | 8.50 |
| FP16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **12.944 GiB** | **2.795** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 13.899 GB / 12.944 GiB |
| **Total** | **39.785B** | **13.899 GB / 12.944 GiB** |

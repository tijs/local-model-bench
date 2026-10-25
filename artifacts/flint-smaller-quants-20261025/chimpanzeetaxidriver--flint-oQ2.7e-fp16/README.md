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

# flint-oQ2.7e-fp16

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.3.dev1) mixed-precision quantization.

The effective average is 3.260 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 2-bit, group 64 | 19.327B | 48.579% | 5.625 GiB | 2.50 |
| Affine 3-bit, group 64 | 18.522B | 46.555% | 7.547 GiB | 3.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 1.615B | 4.060% | 1.598 GiB | 8.50 |
| FP16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **15.101 GiB** | **3.260** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 16.214 GB / 15.101 GiB |
| **Total** | **39.785B** | **16.214 GB / 15.101 GiB** |

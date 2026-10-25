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

# flint-oQ2.5e

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.3.dev1) mixed-precision quantization.

The effective average is 3.112 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 2-bit, group 64 | 25.233B | 63.423% | 7.344 GiB | 2.50 |
| Affine 3-bit, group 64 | 12.616B | 31.711% | 5.141 GiB | 3.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 1.615B | 4.060% | 1.598 GiB | 8.50 |
| BF16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **14.413 GiB** | **3.112** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 15.476 GB / 14.413 GiB |
| **Total** | **39.785B** | **15.476 GB / 14.413 GiB** |

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

# flint-oQ3e

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.3.dev1) mixed-precision quantization.

The effective average is 3.708 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 3-bit, group 64 | 37.849B | 95.134% | 15.422 GiB | 3.50 |
| Affine 6-bit, group 64 | 0.763B | 1.917% | 0.577 GiB | 6.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 0.853B | 2.143% | 0.844 GiB | 8.50 |
| BF16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **17.173 GiB** | **3.708** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 18.439 GB / 17.173 GiB |
| **Total** | **39.785B** | **18.439 GB / 17.173 GiB** |

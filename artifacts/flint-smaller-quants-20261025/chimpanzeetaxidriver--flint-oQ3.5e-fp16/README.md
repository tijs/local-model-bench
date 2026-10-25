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

# flint-oQ3.5e-fp16

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.3.dev1) mixed-precision quantization.

The effective average is 4.008 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 3-bit, group 64 | 25.233B | 63.423% | 10.281 GiB | 3.50 |
| Affine 4-bit, group 64 | 12.616B | 31.711% | 6.609 GiB | 4.50 |
| Affine 6-bit, group 64 | 1.103B | 2.773% | 0.835 GiB | 6.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 0.512B | 1.287% | 0.507 GiB | 8.50 |
| FP16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **18.562 GiB** | **4.008** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 19.931 GB / 18.562 GiB |
| **Total** | **39.785B** | **19.931 GB / 18.562 GiB** |

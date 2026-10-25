---
library_name: mlx
tags:
- mlx
- oq
- quantized
---

# Flint-oQ4e

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.7.2) mixed-precision quantization.

The effective average is 4.633 bits/weight for the complete checkpoint.

## Quantization and Bit Distribution

| Storage format | Logical weights | Share of total | Tensor storage | Effective bits/weight |
|---|---|---|---|---|
| Affine 4-bit, group 64 | 37.849B | 95.134% | 19.828 GiB | 4.50 |
| Affine 5-bit, group 64 | 0.782B | 1.966% | 0.501 GiB | 5.50 |
| Affine 6-bit, group 128 | 0.010B | 0.026% | 0.008 GiB | 6.25 |
| Affine 6-bit, group 64 | 0.094B | 0.237% | 0.071 GiB | 6.50 |
| Affine 8-bit, group 128 | 0.296B | 0.743% | 0.284 GiB | 8.25 |
| Affine 8-bit, group 64 | 0.728B | 1.830% | 0.721 GiB | 8.50 |
| BF16 | 0.025B | 0.063% | 0.046 GiB | 16.00 |
| **Total** | **39.785B** | **100%** | **21.459 GiB** | **4.633** |

## Storage Breakdown

| Component | Logical weights | Storage |
|---|---|---|
| Language model | 39.785B | 23.041 GB / 21.459 GiB |
| **Total** | **39.785B** | **23.041 GB / 21.459 GiB** |

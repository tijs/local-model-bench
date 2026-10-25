# Smaller Flint MLX quant research — 2026-10-25

Read-only Hub research requested after the clean-memory retry stopped during Hermes Ops. Metadata, model cards, configs, indices, and HTTP range-fetched safetensors headers are saved here. No full weight shards were downloaded, no source or serving config changed, and no server started. File sizes are publisher/Hub metadata, not runtime peak-memory measurements or locally verified weight-body hashes.

## Finding

Flint is already text-only. The official RecursiveSI/flint card specifies text/text, and the inspected base/candidate indices have no vision/visual/projector keys. Removing a vision tower cannot reduce this model.

The current affine mixed 3/4-bit checkpoint has 17,837,740,282 weight-file bytes. Smaller standard MLX affine candidates exist:

| Candidate (chimpanzeetaxidriver/) | Pinned revision | Weight-file GB | Saving GB | Routed projection widths |
|---|---|---:|---:|---|
| flint-oQ2e-fp16 | 39ed60d47c27402b924412517804c1d0e858d6da | 13.899 | 3.939 | all 141 at 2-bit |
| flint-oQ2.5e-fp16 | 23faec480c8d62723561fe181e8b4158e446fdaf | 15.476 | 2.362 | 94 at 2-bit, 47 at 3-bit |
| flint-oQ2.7e-fp16 | 210bf3e3c3cbec7dfb91e6ddbebe9167a9e70539 | 16.214 | 1.623 | 72 at 2-bit, 69 at 3-bit |

All three use affine group64 routed weights, affine 8-bit non-expert exceptions, and FP16 residual tensors. The publisher reports importance-matrix calibration on code/multilingual samples and full expert activation coverage. Those are calibration records, not held-out coding/tool quality results. No qualifying Hermes/full-suite quality or peak-memory result was established by this research. Lower bit counts carry an unmeasured quality tradeoff; file-size savings do not establish workload fit.

Non-fp16 siblings exist at nearly identical sizes. The fp16 suffix is a residual dtype choice, not an additional large size saving. oQ3e-fp16 is 18.440 GB and is larger than our current candidate; OptiQ-4bit is 27.483 GB, GPTQ-MXFP4 is 22.076 GB, and oQ4e is 23.042 GB. Nav8ha/flint-mixed-3-4bit is the original duplicate of the current mlx-community build.

## Pinned Mei compatibility

Mei c9b6013958cbc838b156b717f3b49a0045f84064, Sources/MeiCore/FlintConfiguration.swift lines 128-129, accepts only affine 3/4/8 bits. Thus every smaller affine candidate currently fails admission. Do not claim drop-in support or silently loosen the gate. An isolated tested extension for 2-bit affine is the proposed next implementation, including routed numerical tests, preservation of every 8-bit override, strict key accounting, tool/tokenizer parity and fresh native admission. Existing sanitizer strips language_model.; pinned BaseConfiguration already resolves prefixed per-layer aliases. This makes an affine extension appear narrower than a custom packed format port, but execution has not been validated.

## Alignment audit

All three candidate safetensors header key sets match their indices exactly (1,798 keys, no duplicates). Natural alignment uses absolute file offsets modulo dtype byte width, matching Mei tools/align_safetensors.py; it is not a fixed 16-byte test.

- oQ2e-fp16: 1,444 unaligned tensors, 5,006,963,776 payload bytes.
- oQ2.5e-fp16: 1,445 unaligned tensors, 5,409,617,472 payload bytes.
- oQ2.7e-fp16: 1,529 unaligned tensors, 14,284,762,688 payload bytes.

These are potential loader-copy bytes inferred from headers, not measured runtime allocations. A staged aligned derivative should preserve original files and tensor payload hashes, with provenance and independent audit. Header-padding alignment does not change quantization or numerical values. Do not download and immediately serve the unaligned bundle expecting its disk saving to equal a RAM saving.

## Custom packed alternative

OsaurusAI/Flint-40B-A2.5B-JANGH2@8bfb25587388c6a235e58338a6c926da000bded9 has 13,193,711,512 weight-file bytes (4.644 GB below current), with 98/39/4 routed projections at 2/3/4 bits and Hadamard/codebook tq2_packed/tq2_scales storage. It remains unsupported by the pinned Mei/vmlx stack. Existing proj/mei plan 67c8ba44-2b65-45cf-b360-1c9c5e9ee629 covers the substantial format/kernel port. Publisher quality numbers are not benchmark evidence on this Mac.

## Proposed order

First investigate the 13.90 GB affine oQ2e-fp16: largest saving without the custom JANGH format. Add isolated 2-bit support with meaningful tests; preserve high-precision exceptions; stage a provenance-preserving aligned derivative; pass a fresh native gate and an instrumented multi-turn memory canary before another full suite. If quality is inadequate and memory permits, try 15.48 GB oQ2.5e-fp16. Keep JANGH2 as the separate larger integration. No candidate is yet proven safe or good enough for the full Hermes workload.

## Primary sources

- https://huggingface.co/RecursiveSI/flint
- https://huggingface.co/chimpanzeetaxidriver/flint-oQ2e-fp16/tree/39ed60d47c27402b924412517804c1d0e858d6da
- https://huggingface.co/chimpanzeetaxidriver/flint-oQ2.5e-fp16/tree/23faec480c8d62723561fe181e8b4158e446fdaf
- https://huggingface.co/chimpanzeetaxidriver/flint-oQ2.7e-fp16/tree/210bf3e3c3cbec7dfb91e6ddbebe9167a9e70539
- https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2/tree/8bfb25587388c6a235e58338a6c926da000bded9

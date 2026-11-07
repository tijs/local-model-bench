# Queued Peixinho benchmark challengers

Run ToolSpace first, then Gemma, one owned server at a time. The six committed
profiles declare separate native admission and held-out seeds 17 and 29. The
score method is `benchmark-v9.11.5` (`7d70334d368d81ea4376823b0655fa2dd6c4d001`):
12 household tasks and three Python tasks per fresh process. No historical score
is reused. Native admission, scored workflows, and actual Peixinho app acceptance
are separate claims.

- ToolSpace uses the [publisher model and template](https://huggingface.co/dongguanting/ToolSpace-35B-A3B/tree/dc0af2424433de30bbcf872235069fd1dfd6b32c),
  [exact IQ4_XS artifact](https://huggingface.co/mradermacher/ToolSpace-35B-A3B-GGUF/tree/caed525d85b8a36e89b7c909605f9026e1366cb3),
  and the source/build already used for the Logics control. Its embedded Jinja
  template matched the publisher SHA-256. The GGUF has 40 primary blocks and
  one NextN block; speculation is disabled and the capacity plan still counts
  the full file and an extra attention layer. The native probe checks both
  tool transports and their tool-result continuations, cache reuse and output
  parity, and the configured context boundary on native token IDs.
- Gemma uses the [pinned text-only RAM13GB checkpoint](https://huggingface.co/baa-ai/Gemma-4-26B-A4B-it-RAM-13GB-MLX/tree/a29dabbda7e2810f7f23adf18828eba174f388c9)
  and the verified Mei 0.11.0 executable and Metal library. The full publisher
  file inventory is in `gemma-hub-files.json`. Use the shipped mixed affine
  weights and template as-is. The current release includes Gemma 4 model support;
  the exact checkpoint still needs loader and live native proof.

Stage verified weights under `/Volumes/Expansion/local-model-bench`. Retain
committed config snapshots, logs, checksums, transcripts and failed admissions.
Use the standard pressure, swap, disk and byte-budget guards. Do not score a
profile before native admission or silently substitute another quant or sampler.

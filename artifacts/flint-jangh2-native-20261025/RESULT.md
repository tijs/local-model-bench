# Flint JANGH2 native admission — partial, 2026-10-25

The packed-format implementation works on the exact pinned pack, but complete
native support is blocked by a reproducible prefix-cache answer mismatch. This
is not a full Hermes benchmark, task-quality score, or front-runner verdict.

## Implementation and immutable inputs

- Model: OsaurusAI/Flint-40B-A2.5B-JANGH2 at
  8bfb25587388c6a235e58338a6c926da000bded9. Four shard files total
  13,193,711,512 bytes; 1,610 tensor keys; 141 custom routed projections
  (98 two-bit, 39 three-bit, four four-bit). No tensor needs realignment.
- Mei branch work/flint-jangh2-20261025, base c9b6013958cbc838b156b717f3b49a0045f84064.
  Uncommitted source overlay, file hashes and tracked diff are in final-source/.
  vmlx remains 633fe166630ef04310aea7d5a1795555ab32970d; dependency checkout unchanged.
- Separate default-off flag, strict complete-pack validator, payload-preserving
  metadata adapter, mixed-width packed Metal projections and ordinary affine8 /
  BF16 exceptions. Original tokenizer/template/generation configuration preserved.
  No permanent expansion, requantization, key filtering, or legacy-sidecar fallback.
- Exact stored two-bit F32 codebook levels are necessary; cubic recomputation
  introduced a one-ULP difference. Reference kernel attribution is in Mei notices.
- Fixed existing Engine allocator policy: cache-only caps now apply independently
  of explicit memory limits, before and after model load. Final live status
  confirms 536,870,912 bytes. This caps reusable buffers, not live model/KV arrays.

## Validation

- Final offline Swift suite: 414 executed, one explicit real-pack skip, zero
  failures (413 passed). Live MeiAcceptanceTests excluded; CoCore remains off.
  Five Python adapter/header mutation tests passed. RED/GREEN logs retained.
- Opt-in actual-pack test passed separately on the final source: all 150,144
  full-forward logits matched the independent Python graph exactly; maximum
  absolute difference zero, same top token 12834, tolerance unchanged at 0.05.
  Both graphs used cache-off full forward and the identical C++/Metal backend.
  Matching only the MLX version number was insufficient. Earlier failed wheel
  comparisons remain preserved. Reference provenance and external-source hashes
  are in reference-final/; unlicensed external kernel modules are not bundled.
- Initial short HTTP probe: 10/10 passed, including exact identity, visible
  response, tools streaming/buffered, transport parity, repeated/growing prefix
  cache counters. Tool-result continuation passed.
- Stronger cache test FAILED: identical 654-token request, after a diverging
  request, returned ORANGE twice instead of once with a 653-token cache hit.
  It reproduced in three builds/profiles, including the corrected 512 MiB cap.
  Cache-off A/B/A returned the requested single answer every time. Raw failure
  is retained in extended-capped.json. The earlier word-presence assertion was
  too weak; cache-divergence-assessment.json supersedes that apparent pass.
  Root cause is unresolved; cache hits alone are not correctness proof.
- 65,535 prompt + one generated token passed (716.08 seconds); 65,536 prompt
  + one generated token passed (2.45 seconds with 65,535 cached tokens);
  a 65,537-token prompt returned HTTP 400. The configured limit is a prompt cap,
  not a hard combined input/output cap. This is admission proof, not long-context
  answer-quality or long-context logit parity.
- Long-context phase: pressure always normal, swap fixed at 2,557.19 MiB,
  minimum reported free memory 25%, peak sampled physical footprint 9.18 GB.
  Source/test compilation also ran during this phase. GPU/mmap residency is not
  fully described by process physical footprint; see allocator/request logs and
  host telemetry together. A buffer-cap bug was discovered afterward: actual
  cache limit during that phase was 32,641,751,449 bytes despite a 512 MiB flag.
  The corrected cap was checked on the final short phase; do not relabel the
  historical 64K run as a corrected-cap test.
- All 16 original files were rehashed after execution and match staging exactly.
- Tiny HTTP requests decoded around 41–43 tokens/s. No Hermes Ops, coding suites,
  full benchmark, or agent-quality comparison ran for JANGH2.

## Retirement, state and next gate

Old affine Flint evidence was committed/pushed first: e15e307 and c628f3b on
work/flint-forced-disk-gate-20261022. Original append-only task rows remain intact.
Only manifest-listed old weights/runtime/build caches were retired, recovering
23,459,393,536 bytes net. See artifacts/flint-retirement-20261025/.

New JANGH source and evidence remain local/uncommitted, not released or pushed.
All four owned server processes stopped normally; ports 8024 and 8017 are free.
Final check: 86% memory free, 2,557.19 MiB swap used, about 90.44 GB disk free.

Keep JANGH experimental/default off. Resolve the precise cold/warm mismatch,
complete remaining negative/admission coverage and native gates, then review a
separate committed benchmark configuration and execution authorization. Do not
silently disable cache reuse and present that as the completed planned profile.

# Prepared Qwen SDPA operator probe

**Preparation inputs and executed diagnostic evidence are separate.** The
[isolated Debug build](../../mei011-sdpa-swift-build-20261107/result.json) and
[synthetic operator audit](../qwen-sdpa-operator-review-20261107.json) are complete.
The Python adaptation below remains CPU-checked only. A guarded real-Qwen
[dispatch trace](../qwen-sdpa-model-trace-20261107.json) is in progress.
Do not overlap a build, GPU test or model run with an owned timing campaign.

This reuses MLX's `benchmarks/python/sdpa_vector_bench.py` at core
`e790cca9df907c30ff4f18b0c772b4d9f454132e`. The unmodified snapshot, license,
checksums and small adaptation patch are retained here. The optional dtype flag
keeps FP16 as the default and adds BF16/F32 inputs. Logical bandwidth uses the
actual element size. Optional exclusive JSON output retains every sample,
reference error, settings and runtime-module path/version. Those fields alone
do not attest source/build provenance.

CPU-only checks pass: syntax/lint, two unchanged upstream reference/timing-chain
function bodies, seven parser compatibility cases and four deterministic-clock
samples retained with their units. These checks never import MLX. Run them with:

```sh
uv run --locked python artifacts/mei-upstream-qualification-20261106/qwen-sdpa-probe-preparation/static_checks.py
```

For the later GPU diagnostic, first build/verify the intended pinned core in an
isolated environment; record source/diff, build flags, runtime/shared-library and
Metal hashes. Use the same fixture, seed and settings on both arms. Do not use an
arbitrary installed wheel merely because its version string matches. A prepared
invocation, **not executed**, is:

```sh
uv run --no-project --python /absolute/path/to/verified/python \
  artifacts/mei-upstream-qualification-20261106/qwen-sdpa-probe-preparation/sdpa_vector_bench.py \
  --dtype bfloat16 --shape 16,2,30000,256 \
  --json-output /absolute/path/to/fresh-operator-evidence.json
```

Keep all raw samples and numerical checks. The upstream console's best sample
is auxiliary and never substitutes for a complete distribution. This is a
host-inclusive chained-operator probe, not loaded-model/task performance or a
release admission gate. Runtime dtype/kernel selection still needs verification.
Any proposed fix needs a reproduced mechanism, numerical regression checks,
atomic issue-first contribution review and affected Mei qualification.

## Dispatch probe and restored checkout

`dispatch-probe.patch` was applied temporarily for the separate Debug build.
The original core file and checkout were restored and the production assets
rehash unchanged. The patch adds a one-time actual kernel/dtype/shape/thread
limit trace and an opt-in selection of the existing TK1 variant. Existing dtype
eligibility and threadgroup-size checks stay in place. Run one shape per process
so the trace identifies that case. Both arms must use the same instrumented
binary, precision, shapes, flags and build settings; only the force flag differs.

First inspect the default dispatch. If it already selects TK1, forcing TK1 is
not a distinct treatment and must not be reported as a useful A/B comparison.
If variants differ, require numerical reference checks and retain all raw samples.
These are diagnostic hooks, not a production patch or proposed default. Remove
them from any final fix; an operator result alone cannot qualify Mei.

The trace includes the specialization key (mask/layout/block constants), not
just the base kernel name. The Python script’s path label is a shape-based
classification and must not be mistaken for an observed runtime variant.

## Swift operator adapter

`QwenSDPAProbeTests.swift` reused Mei's existing Debug dependency products
instead of building separate Python bindings. The temporary test-target copy
was removed after compilation; the retained source is outside the shipped
test target. The build receipt binds the exact patch, test source, flags,
Debug executable, test binary and production Metal hashes. Never replace the
frozen release product or ship the diagnostic hooks.

The explicit Metal override permits using the hash-verified production library.
Defaults are BF16, GQA8/D256 and contiguous30,000-token KV. Bounded options cover
30,000..30,128 tokens, FP16/BF16/F32 and padded KV storage up to65,536 rows, so
later fixtures can match observed tail position and strides. The C++ trace now
includes Q/K/V head/sequence strides. Actual model dtype/layout/dispatch still
needs tracing; a synthetic fixture is not proof of it.

The adapter ports the upstream reference/chaining operations and dtype-specific
absolute+relative test tolerances, retains all150 samples, and refuses an
existing output. Four guarded processes pass the numerical reference; all600
raw samples are preserved. Both forced TK1 process means are faster than both
defaults for this synthetic contiguous BF16 fixture. This does not establish
actual Qwen dispatch, model TPS or a production improvement. Compare only
genuinely distinct selected variants and confirm real layout and model behavior
before any scoped production change.

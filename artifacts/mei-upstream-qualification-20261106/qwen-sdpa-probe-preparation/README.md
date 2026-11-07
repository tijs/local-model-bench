# Prepared Qwen SDPA operator probe

**Prepared only. No GPU execution, numerical result or timing result exists.**
Wait until campaign20319 is terminal and reviewed before building or running it.

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

## Unapplied dispatch probe

`dispatch-probe.patch` applies cleanly to the pinned core; it has **not** been
compiled or applied to any checkout. After the live campaign is terminal, use a
separate source/build. The patch adds a one-time actual kernel/dtype/shape/thread
limit trace and an opt-in selection of the existing TK1 variant. Existing dtype
eligibility and threadgroup-size checks stay in place. Run one shape per process
so the trace identifies that case. Both arms must use the same instrumented
binary, precision, shapes, flags and build settings; only the force flag differs.

First inspect the default dispatch. If it already selects TK1, forcing TK1 is
not a distinct treatment and must not be reported as a useful A/B comparison.
If variants differ, require numerical reference checks and retain all raw samples.
These are diagnostic hooks, not a production patch or proposed default. Remove
them from any final fix; an operator result alone cannot qualify Mei.

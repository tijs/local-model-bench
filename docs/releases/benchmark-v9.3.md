# local-model-bench benchmark-v9.3

Puts native Mei release acceptance under the same capacity/resource rules as
scored runs. The CLI now requires a committed config, exact runtime pins and an
isolated runtime base. It owns the entire server/probe process group, forwards
the runtime base to teardown and refuses a pass without required probe evidence.
Skipped cache/context checks remain diagnostic.

Eight focused tests cover real descendant cleanup under simulated critical
pressure, preflight refusal, low-percentage capacity admission, missing evidence,
exact runtime forwarding and skipped-context classification. The runner suite
passes 679 tests. See the [native acceptance guide](../MEI_NATIVE_ACCEPTANCE.md).

Scored task helpers, validators, launch parent, supervisor and existing profiles
are unchanged from v9.2. No old task grade is rewritten. The current comparison
remains separately verified against its measured source identities.

Clover's pinned MLX-format pack is staged and all 15 publisher-file hashes match.
Its 8/32-row diffusion kernel checks pass CPU-reference comparisons on this M1
Max, including bidirectional attention. Non-attention checks also passed with
shader validation enabled; the debug layer's documented attention memory-limit
issue requires that full attention check to run without it. Native model tools
and quality are still pending. Kapitsa is a native Metal engine consuming these
weights, rather than an MLX runtime.

The prepared Groot text artifact is now public with license, attribution and
per-tensor provenance. All 16 files were independently read back anonymously
with matching metadata/hash and size. Native qualification and publication of
Mei 0.10.0-rc.2 remain in progress; stable Mei remains 0.9.0.

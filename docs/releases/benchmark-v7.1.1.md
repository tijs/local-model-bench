# local-model-bench benchmark-v7.1.1

Report-only correction: failed admission now displays **not admitted / not run**
and remains unranked. Partial task fractions explicitly label executed and
planned counts. Unattempted task counters display a dash rather than suggesting
zero observed errors. No grading, generation, transport, launcher or resource
policy changes are included.

All22 measurement/config files exactly match benchmark-v7.1; their hashes are
recorded in
[the method-identity audit](../../artifacts/automation-benchmark-20261029/report-patch-method-identity-20261031.json).
The19 comparison tests, Ruff and ty pass, including a regression that fails with
the old admission display. Existing v7.1 measurements retain their original
runner/config/method identities; this patch does not manufacture new runs or
relax admission. The comparison remains labeled with its v7.1 measurement tag.

Current campaign evidence:

| Profile | Household | Python | Coverage |
|---|---:|---:|---|
| Qwen3.6 text-only MLX4 / Mei |9/12|2/3|Complete held-out trial;486.40s|
| Flint JANGH2 / Mei |Not admitted|Not run|Published admission failed; unranked|
| Ornith1.5 MLX4 / Mei |Pending|Pending|Resource admission pending|
| MiniCPM-V4.7 Q4_K_M / llama.cpp |Pending|Pending|Resource admission pending|

Qwen's one task-budget outcome is distinct from completed incorrect output.
Its shopping script passed visible/unseen outputs after repairing an invalid
tool call; the strict invalid-call failure remains. Pressure stayed normal and
swap did not grow. Scores are separate tracks from one trajectory, not evidence
of statistical superiority or Peixinho app acceptance.

Flint raw-envelope controls show the omitted verification code was already
absent before parsing. Identical greedy reasoning/calls occur with cold cache,
a confirmed251-token warm restoration, and caching disabled. The API preserves
code when it is emitted. These controls argue against field loss or cache reuse
causing this reproduced failure; they do not distinguish the base model from
JANGH2/shared inference kernels. They do not override the failed admission or
produce a full-model score.

All model rows and failed/partial invocations remain unchanged. Source,
transcripts, resource logs, cleanup/integrity checks and diagnostic limitations
are in the [campaign evidence](../../artifacts/automation-benchmark-20261029/README.md).
The four-model comparison remains unfinished; no overall winner is declared.

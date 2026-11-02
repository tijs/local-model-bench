# local-model-bench benchmark-v9.8

Scored Mei runs can now use an exact released executable without rebuilding it.
`start_mei_server.sh --mei-binary /absolute/path` retains owned runtime/PID
cleanup while skipping Swift builds and scratch-directory creation. Scored
configs must bind the clean source revision and executable/adjacent Metal
library hashes in `mei_release_artifact`. Preflight checks the pins before
teardown; each task track verifies hashes and the actual listening executable.
Changed, missing or ambiguous artifact pins are refused.

The shared chat transport accepts an explicit request `seed`, validates it and
records the exact value in generation metadata. Seed 0 is preserved; absence
keeps the previous request shape. This uses Mei's existing request API rather
than the unsupported server CLI seed flag. A declared seed is not a guarantee
of deterministic output or independent samples.

Two full trials each for Groot on distributed Mei rc.2 and Logics-SWE on the
pinned llama.cpp binary are predeclared with seeds 17 and 29. Every outcome will
be retained. No task, grader, permission, containment, budget or resource rule
changes. New runtime/transport helper fingerprints remain distinct from older
measurements; no historical score is promoted.

[Repeat design and profiles](../FINALIST_REPEATS.md) ·
[Current candidate evidence](../CANDIDATE_CAMPAIGN.md) ·
[Previous grading correction](benchmark-v9.7.md)

Validation: 704 model-free runner tests pass; real HTTP seed and no-build
launcher regressions pass. Verifier, transport and focused tests pass ty. Ruff
passes new verifier/tests; the legacy transport retains its five pre-existing
TRY004/SIM115 findings with no new finding. All 16 staged Groot files match the
publication manifest, all four declared profiles validate, and frozen v9.5/v9.7
reports reproduce byte-for-byte. [Preparation evidence](../../artifacts/finalist-repeat-preparation-20261102/README.md).

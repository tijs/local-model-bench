# Released-runtime repeat preparation

Four complete Groot/Logics-SWE profiles are declared before inference, with
request seeds 17 and 29. See the [design and run order](../../docs/FINALIST_REPEATS.md).
No new score follows from this preparation.

- All 704 model-free runner tests pass. Focused release/source/listener, launcher
  and real HTTP seed checks pass. Changed verifier/seed tests and transport pass
  ty; Ruff passes on new/changed verifier/tests. The legacy transport retains
  four existing TRY004 and one SIM115 findings, verified against its committed
  baseline with no new lint finding.
- The installed Groot executable and adjacent Metal SHA-256 values match the
  already distributed Mei rc.2 assets. Both fresh Groot configs verify source,
  lock and asset hashes and their launcher dry runs do not build.
- All 16 public staged model files match the publication manifest.
- Both Logics configs verify the existing pinned source/executable/libraries.
- Task prompts/tools, graders and Python containment are byte-identical to
  v9.7. The transport adds seed only when explicitly provided; older no-seed
  wire-shape regression tests pass. The verifier and transport helpers receive
  new measured fingerprints rather than relabeling historical rows.
- Frozen v9.5 and Clover v9.7 reports reproduce byte-for-byte.

The full-suite log includes deliberately mocked legacy warnings and stale-chart
messages from tests; it does not represent an uncontained real scored run.
All model inference still requires fresh capacity/resource admission and owned
cleanup, and must run without unrelated build/download/GPU work.

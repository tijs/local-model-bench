# Parent integration validation — 2026-10-28

Both requested workers completed before parent review and live inference.
Benchmark implementation: efa07e9. Published runtime pins:
Mei009b7adc962ab720d3766f3bed28a5e41201838e,
vmlx5b2ffe15d7b88fe1eaebfbe51afcd81716f6a11f.

Parent plus correctness/tests/simplicity re-review resolved seven findings:
strict terminal reasons/SSE errors, invalid record-ID grader handling,
post-restart verification, actual endpoint identity, early committed-config
admission/shared transport hashes, truthful deleted-source explanations, and
contextual private transcript leakage. Source and negative-to-green tests are
committed. Kiem review97b69f4e-afaa-4d22-ba4f-3dc9f73db4d6 records the findings.

- Final locked harness suite:537 tests passed in78.529seconds.
- Focused stand-in suite:40/40passed, independently rerun by two reviewers.
- New executable stand-in/check modules and parent regression: Ruff passed.
- Stand-in/check modules:ty passed against locked Python environment.
- Launcher Bash syntax and12 focused forwarding/rejection tests passed.
- Both final configs passed launcher dry run, with separate explicit512MiB
  prefix-retention and reusable allocator caps, native sampler and disabledcompile.
- Runtime worktrees clean, exact pins match upstream work branches; scratch
  checkout matches, no editable override; fixed binary/metallib freshly rehashed
  against the memory worker's published-build provenance.
- Original16 model files reverified unchanged before inference.
- All four original historical/model-only log/report hashes remain unchanged.

First live pilot is four smoke cases then all12development contracts, one
trial each, subject to reviewing smoke/partial outcomes and fresh resources.
This does not calibrate population variance or establish actual-app acceptance.

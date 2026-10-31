# local-model-bench benchmark-v7

Adds a separate `python-automation-v1` track for agents that write and execute
small standard-library Python scripts: shopping CSV normalization, decimal-safe
expense aggregation, and reminder-export repair. The model reads named synthetic
inputs, writes `solution.py`, and runs it with real execution feedback. After it
finishes, the grader executes the submitted source on visible and unseen inputs.
It must have successfully executed the final submitted source itself. No real
project, household data, or Peixinho application is accessed.

The macOS executor installs a native Seatbelt policy before reading candidate
code. Candidate networking, writes, subprocess execution, Mach access and process
inspection are denied. Execution time, output and source size are bounded;
memory uses a sampled stop, not a hard allocation cap. Actual boundary tests,
positive controls and their limits are documented in the
[automation guide](../PYTHON_AUTOMATION.md) and
[implementation evidence](../../artifacts/automation-benchmark-20261029/README.md).
Unsupported isolation fails closed.

The twelve synthetic household tasks retain a separate score and strict attempt,
authorization and state checks. Household budgets are now12 turns,4096 tokens per
turn,180 seconds per HTTP turn and600 seconds per task. Python budgets are8
turns,4096 tokens per turn,180 seconds per HTTP turn and480 seconds per task, plus
bounded post-agent grading. Shopping capture explicitly requests item names.
These changes define a new baseline: preserve old rows and compare matching
method identities. Budget exhaustion is reported separately and does not prove
model inability. Recovering from an invalid household call does not erase it.

Both tracks use one owned model server, committed configurations, immutable
model/runtime provenance and resource supervision. UUIDs bind the resource log,
configuration and exact run manifests. The comparison builder checks released
method fingerprints, clean source, complete task coverage, serving/isolation
identities, raw grades and resource outcomes. Partial or pressure-interrupted
runs cannot become ranked full-model scores. No cross-track composite is used.

Validation:654 locked unit/integration tests pass, with focused lifecycle,
containment, reference/mutation and independent review evidence. A missing Metal
toolchain after an Xcode update was installed before the successful calibration.
Darwin cleanup now tolerates EPERM for an owned zombie-only group while preserving
live-member denial and PID-reservation checks. Existing interrupted attempts and
their original rows/manifests remain unchanged.

Complete development calibration at runner `cc2fc1b0ea7a`:

| Model / serving profile | Household | Python | Resource outcome |
|---|---:|---:|---|
| Qwen3.6-35B-A3B text-only MLX4 / Mei |10/12|3/3|Normal pressure; no swap growth; clean teardown|

Household run `20261031T073803Z-dd6549a1` failed multipart capture after inventing
an unassigned routing-operation ID, then recovered with the assigned ID; its
final state checks passed. In untrusted-content, it used the request source ID
instead of the record ID explicitly supplied by the user and reported the
record unavailable. No unauthorized mutation or private disclosure occurred.
All API arguments exactly match executed simulator arguments, and all12 frozen
grades reproduce. Earlier native/cache/independent-Python controls provide
additional bounded attribution evidence; this does not distinguish base-model
behavior from quantization/shared MLX kernels or certify every runtime path.
Python run `20261031T074330Z-0e134560` passed all3 tasks with zero invalid calls.

This calibration took756.15 seconds end to end (12m36), including a299.60-second
rebuild after the Xcode update. Household tasks used317.73 seconds and Python
tasks95.11 seconds. It is one development trajectory; the four-model held-out
comparison is a separate campaign and remains pending at publication.

Hermes remains retired. These tests are synthetic workflow and isolated-script
evidence; they are not real Peixinho acceptance, broad coding or vision scores.

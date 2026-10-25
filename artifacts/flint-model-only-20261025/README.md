# Flint JANGH2 model-only trial — 2026-10-25

Current scope: two sanity cases and eight neutral simulated-tool cases, three
repeats each. No Hermes or Peixinho application runtime is involved. Config:
`configs/Flint-JANGH2-model-only-20261025/mei.yaml`. Original source hashes:
`../flint-jangh2-native-20261025/model-provenance.json`.

The model-only harness and pinned config must be committed before execution.
`baseline.json` captures the old append-only log prefix and historical report
identities. `supervise.py OUTPUT SECONDS -- COMMAND...` records invocation,
process ownership and system resources every five seconds. The foreground Mei
launcher waits on its server child, so the server stays in the owned process
tree and process group. Telemetry identifies individual process footprints;
do not confuse the runner footprint with the server footprint.

Initial gate: >=70% memory free, normal pressure level 1, disk >10 GiB.
Stop on critical pressure (>=4), free <=10% twice, swap >=16 GiB, disk <10 GiB,
wall deadline or stop.request. Only the owned process group is signalled;
normal runner finally also stops its isolated Mei runtime. Normal disk gate
remains enabled; no waiver or exploratory bypass is passed.

Execution outcome, per-task audit and final resource/provenance verification
will be appended after the supervised run. These checks do not establish long
context quality or application suitability.

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

## Completed outcome

Runner `679bba5284e1`, config `905cd2922f41`, Mei `84364d5e2154`, vmlx
`ccbd1d337f82`. Supervisor exited 0 with no safety stop. Release build took
290.63 seconds. All 30 exact task/trial pairs executed once; 17 passed:

| Suite/task | Passes / trials |
|---|---:|
| Sanity (two cases) | 6/6 |
| Tool selection | 3/3 |
| Tool chaining | 2/3 |
| Error recovery | 1/3 |
| Targeted edit | 1/3 |
| Noisy result | 1/3 |
| Multi-step chain | 0/3 |
| Persistent tool failure | 0/3 |
| No tool needed | 3/3 |

There were zero transport/harness errors. Eight failures reached the eight-turn
limit; the other five missed required tools/sequences. Raw responses also
include empty final assistant messages after tool results. `failure-review.json`
records every failed row without rewriting grades. These observations alone do
not distinguish quant quality, sampler, template/parser or cache effects;
controlled cache-off/fresh-conversation comparisons remain follow-up work.

Tool-suite median output rate was 28.61 tokens/s (completion tokens divided by
whole task wall time, including prefill/tool turns); median TTFT was 3.08 s.
This is not a pure decode measurement or a historical composite/application score.

System memory free fell from 88% to a minimum 13%; peak pressure level was 2
(warning, not critical). Swap rose from 1905.12 to 3280.12 MiB. Minimum disk free
was 88,473,206,784 bytes, above the normal floor. No safety limit was bypassed.
The memory trajectory warrants cache/residency investigation before repeated
campaigns; successful completion does not establish comfortable memory headroom.

The owned server stopped normally; port 8024 is free and host memory recovered
to 87% immediately afterward. All 16 original model files match their pinned
hashes and sizes after the run. The original results-log prefix, historical
leaderboard and chart hashes are unchanged. Current rows remain rank-ineligible
and appear only in `results/MODEL_ONLY.md`. No Hermes runtime or Peixinho app
was launched. `audit.json`, `runtime-provenance.json`, raw runtime logs and
`run/resources.jsonl` retain verification and resource evidence.

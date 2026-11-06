# Mei upstream refresh qualification

These profiles qualify the upstream integration; they do not produce household
or Python task scores. See the [current evidence index](../../artifacts/mei-upstream-qualification-20261106/README.md)
for exact artifacts, completed gates and remaining work.

| Profiles | Purpose |
|---|---|
| `*-paged-io-native.yaml` | Current frozen57b620b/9dd023d3 candidate; full native tool/history/cache/65,536-token admission on all three Mei contenders |
| `*-speed-a1.yaml`, `*-speed-a2.yaml` | Exact installed stable0.10.0 controls, with their historical mmap policy |
| `*-speed-b1.yaml`, `*-speed-b2.yaml` | Exact current candidate, owned storage and default residency requested=true |
| Other native/residency/cold-hash profiles | Historical diagnostics; keep their original source/artifact identities and reviewed outcomes |

The [balanced matrix](../../artifacts/mei-upstream-qualification-20261106/speed-matrix.json)
predeclares A1/B1/B2/A2 per model, two processes/version and five measured
repeats/context/process. Cold and warmup observations are separate. Each cell
also runs nine prebuilt live HTTP checks and verifies observable greedy parity.
The native profiles use `mei-native-v1`; speed/API profiles use
`mei-release-qualification-v1`. Neither is ranking evidence.

Unsafe elementwise compilation stays off, matching the released benchmark
profile. Model precision, context, samplers, output budgets and resource guards
are explicit. Use one model at a time, keep builds/GPU tests idle during timing,
and preserve/review each terminal result before proceeding. Do not relaunch a
running or interrupted campaign; inspect its actual owned process and outcome.

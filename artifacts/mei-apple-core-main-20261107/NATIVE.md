# Apple MLX core main native qualification

All four profiles passed real native tool calls, cache reuse, uncached 65,536-token admission and over-limit rejection. Model hashes matched after shutdown. These are admission results; timing is reported separately.

| Model | Passed probes | Verified files | Warning samples | Swap growth (MiB) |
|---|---:|---:|---:|---:|
| [qwen](../../artifacts/qwen-mei-apple-core-main-20261107-native/probe.json) | 13 | 15 | 1 / 63 | 183.25 |
| [ornith](../../artifacts/ornith-mei-apple-core-main-20261107-native/probe.json) | 13 | 11 | 0 / 101 | 0.32 |
| [groot](../../artifacts/groot-mei-apple-core-main-20261107-native/probe.json) | 13 | 16 | 0 / 46 | 1.06 |
| [gemma](../../artifacts/gemma-mei-apple-core-main-20261107-native/probe.json) | 13 | 11 | 0 / 45 | 0.00 |

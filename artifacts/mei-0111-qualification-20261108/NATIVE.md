# Apple MLX core main native qualification

All four profiles passed real native tool calls, cache reuse, uncached 65,536-token admission and over-limit rejection. Model hashes matched after shutdown. These are admission results; timing is reported separately.

| Model | Passed probes | Verified files | Warning samples | Swap growth (MiB) |
|---|---:|---:|---:|---:|
| [qwen](../../artifacts/qwen-mei-0111-qualification-20261108-native/probe.json) | 13 | 15 | 1 / 63 | 1.00 |
| [ornith](../../artifacts/ornith-mei-0111-qualification-20261108-native/probe.json) | 13 | 11 | 0 / 102 | 0.00 |
| [groot](../../artifacts/groot-mei-0111-qualification-20261108-native/probe.json) | 13 | 16 | 0 / 42 | 0.00 |
| [gemma](../../artifacts/gemma-mei-0111-qualification-20261108-native/probe.json) | 13 | 11 | 0 / 45 | 0.00 |

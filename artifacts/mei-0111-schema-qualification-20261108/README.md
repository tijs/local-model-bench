# Mei 0.11.1 release qualification

The fixed build passed all four native profiles and all 16 timing processes.
Qwen, Ornith, Groot, and Gemma each passed 13 native probes and nine live Swift
API tests. Gemma's strict JSON canary now finishes with `stop` in both modes;
the published 0.11.0 control failed those same two tests.

| Model | Short 0.11.0 | Short 0.11.1 | 30k 0.11.0 | 30k 0.11.1 |
|---|---:|---:|---:|---:|
| Gemma | 46.68 | 46.66 | 32.32 | 32.25 |
| Qwen | 67.11 | 67.40 | 51.16 | 51.32 |
| Ornith | 67.16 | 67.20 | 51.15 | 51.26 |
| Groot | 55.73 | 55.71 | 44.25 | 44.24 |

Decode throughput in tokens/s. Each value averages the medians of two fresh
server processes on a 32 GB M1 Max. Processes ran in ABBA order on the same
checkpoints and prompts, with five measured attempts per context. All timing
comparisons passed exact streaming output, usage, and finish-reason parity.
First-token latency, decode throughput, and total time changed by less than
0.5% in every comparison. All native and timing processes stayed in normal
memory pressure with zero measured swap growth.

[Build receipt](build-receipt.json) · [Run matrix](matrix.json) ·
[Audited timing data](comparison.json) · [Native probes](NATIVE.md) ·
[Original interruption and control](../mei-0111-qualification-20261108/INTERRUPTION.md)

These are runtime qualification results, separate from scored task runs.

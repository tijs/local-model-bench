# Mei 0.10 candidate qualification review

The tested runtime is Mei `b5451a8e5cf58e0d9bb6da142df39a9a98bd51b4`, vmlx `9db62ce10416db4a33ff0108dca6fc00bdadfff7`, binary SHA-256 `fcb3c392b16394008304561cd4919b239793a29a9e23acacd64176fd6320e564`, and Metal SHA-256 `e87ac8aa940ace7dd1f9945c4b6a3238c3d94604391e0f36a0ac51259bd76f32`. The release-preparation commit `2018275` changes documentation and packaging scripts since the tested commit; `Sources`, `Package.swift` and `Package.resolved` are unchanged. This is not a claim that the binary was built from that later commit. The vmlx pin is present on its remote branch.

Qwen, Ornith and Groot each passed all 13 native probes, including exact 65,536-token context admission and over-cap rejection. Each completed four guarded candidate measurement processes, with live Swift client tests and observable greedy parity against the saved reference. Model hashes and owned cache cleanup were recorded. Ornith additionally has two independently launched controls with the same prefill-32 profile: all 14 observable rows match each other and both compile-off candidate processes. This compares returned text, token counts and finish reasons; hidden token IDs are not observed. Long-prefill status samples and the offline actor-busy regression support the responsiveness change. See the individual `mei-stable-*-unused-boundary-*` and `mei-stable-ornith-matched-control*` directories for exact evidence.

Measured process medians (short / 30,000-token context, tokens per second) are:

| Model | B1 | C1 | C2 | B2 |
| --- | --- | --- | --- | --- |
| Qwen | 45.54 / 41.68 | 43.93 / 38.92 | 66.97 / 48.82 | 69.61 / 49.86 |
| Ornith | 69.15 / 49.74 | 66.78 / 48.68 | 66.92 / 48.79 | 56.32 / 39.16 |
| Groot | 56.82 / 43.37 | 54.67 / 42.00 | 54.59 / 41.90 | 56.75 / 43.31 |

B and C toggle the public unsafe-compile flag on the same candidate binary. The large Qwen and Ornith between-process shifts prevent a reliable general speedup or regression estimate; normal sampled pressure and flat swap do not explain them. Qwen's separately audited clean launches likewise measured 67.15 / 48.89 and 44.02 / 39.62. Do not discard slower processes or describe these timing runs as task scores.

On the final source branch, package tests passed 24/24 with the tested binary and explicit previously qualified Metal artifact. An initial test without a configured binary failed before packaging; a subsequent attempt correctly rejected the older-mtime artifact. A copied binary was SHA-256 verified and its runtime source/lock identity checked before packaging; the packaged binary and Metal hashes match those above. The generated archive is local and unpublished. Stable tag, GitHub release, Homebrew update, installation checks, and fresh task benchmarks remain outstanding.

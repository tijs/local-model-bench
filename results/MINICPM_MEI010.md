# MiniCPM fresh two-seed results

MiniCPM-V-4.7 Q4_K_M ran on the frozen benchmark-v9.11.5 method with pinned llama.cpp, two fresh declared seeds, the same held-out 12 household and three Python tasks, and normal sampled pressure without swap growth. This is a CPU8/no-repack, q8 KV, text-only serving profile; it is not a pure model or runtime comparison.

| Seed | Household | Python | Result |
|---|---:|---:|---|
| 17 | 12/12 | 3/3 | [Audit and evidence](../artifacts/mei010-minicpm-local-seed17-20261105/README.md) |
| 29 | 11/12 | 2/3 | [Audit and evidence](../artifacts/mei010-minicpm-local-seed29-20261105/README.md); critical safety failure |

Across both runs, 23/24 household and 5/6 Python attempts passed. This descriptive total does not make the profile eligible for the ranked comparison: in seed 29's multipart scenario it tried three conflicting operation IDs, which were denied, then created an unrequested family shopping item. The grader recorded one unauthorized mutation and a critical safety failure. The reminder script also failed an unseen Python case. All results and failures remain visible; no best-seed substitution is used.

The first launch attempt timed out while opening a file on the Expansion volume and produced no score. A separately downloaded internal copy was verified against the same publisher-pinned size and SHA-256 before these runs. [Failed admission evidence](../artifacts/mei010-minicpm-seed17-20261105/README.md) · [Verified staging receipt](../artifacts/mei-stable-qualification-20261102/minicpm-internal-staged-model-hashes.json).

Two controlled processes averaged **41.27 tokens/s at 17 prompt tokens** and
**14.05 tokens/s at 30,000 prompt tokens**. Each average equally weights two
processes with five measured greedy 128-token decodes per context. These are
native llama.cpp decode rates, not task completion rates.
[Speed evidence and graph](charts/minicpm-mei010-context-speed.json) ·
[PNG](charts/minicpm-mei010-context-speed.png) ·
[SVG](charts/minicpm-mei010-context-speed.svg).

These synthetic tasks are not Peixinho app acceptance.

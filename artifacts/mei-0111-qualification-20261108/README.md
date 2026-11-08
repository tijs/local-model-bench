# Mei 0.11.1 release qualification

This campaign compares the proposed 0.11.1 binary with the published 0.11.0
binary on the same Qwen, Ornith, Groot, and Gemma checkpoints. It produces no
scored benchmark rows.

1. Require the candidate's offline Swift suite and verify the two C++ Release
   targets, Mei executable, and Metal library.
2. Run each model's native API, tool, cache, and exact context-cap probes.
3. Run fresh processes in ABBA order (0.11.0, 0.11.1, 0.11.1, 0.11.0) per
   model, with matched short and 30,000-token prompts. Each process includes
   warmup and five measured attempts per context. Run the pinned Swift live API
   suite after the timing measurements in the first candidate process.
4. Audit request and model identity, pressure and swap, byte-identical greedy
   output, token usage, status responsiveness, first-token latency, and decode
   throughput. Investigate adverse changes that repeat in both orders before
   promoting the candidate.

Run the committed matrix with
`artifacts/mei-apple-core-main-20261107/run_campaign.py`, first with `native`
and then `timing`, passing `--matrix` for this campaign.
`summarize.py --matrix <path>` emits the audited comparisons as JSON.

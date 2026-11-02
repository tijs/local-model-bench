# Mei 0.10 qualification campaign

Prepared runtime qualification, separate from the scored benchmark. The public
stable release remains 0.9.0 until all admission, correctness, performance and
distribution gates pass. A development binary printing `0.10.0` is not a release.

The preceding [60K diagnostic](../mei-stable-status-groot-rawfix-20261102/README.md)
proved responsive status during real prefill and visible raw completions. Its
single timing observation does not qualify performance or task quality. Earlier
failed setup diagnostics are retained alongside it.

`matrix.json` predeclares Groot, Qwen and Ornith in process order
**A1/B1/C1/C2/B2/A2** for each model. Every process supplies five measured short
and five 30K-context decodes, plus retained cold and warmup observations. Each
arm therefore has ten measured observations per context and two cold processes.

| Arm | Runtime | Existing elementwise compilation |
| --- | --- | --- |
| A | API-correct control, vmlx `e59a715e` | Off |
| B | Phase-flag lookup candidate, vmlx `2584835e` | Off |
| C | Same candidate binary as B | On |

B/A isolates the CPU environment-lookup optimization. C/B qualifies the existing
public compilation setting on the new dependency pin. Routed-MoE compilation
remains off in every arm. The runtime JSON manifests and committed profiles
pin the exact source, binary, Metal and model bytes. A fast isolated environment
lookup is only implementation evidence; it is not a model-speed result.

`run_matrix.py` executes one guarded cell at a time. After terminal exit it
preserves logs, verifies all model hashes, inventories the cache, removes only
that exited run's owned KV, then audits complete coverage and greedy observable
output against A1. A failure stops for review; the script refuses to restart an
existing campaign blindly. `matrix-progress.json` and per-run audit files record
the actual outcome. No scored rows are written by this driver.

B1 and C1 additionally run the frozen nine-test Swift HTTP client. Full Python
native admission is separately predeclared for each model. Semantic admission
uses `/v1/mei/status.maxTokens`, currently **8192**. The 128-token raw timing
probe, short cache-counter requests and one-token exact-context check do not
claim semantic task completion. No live use was made of the intermediate
256/1024-token Swift clients; their manifests document preparation history.

See [the qualification method](../../docs/MEI_STABLE_QUALIFICATION.md) and
[the owning plan](kiem://note/e48c7c4e-eb1a-4989-be5f-10e2047be86e). Logics remains
the unchanged llama.cpp control for the later scored comparison; its MLX
conversion is paused.

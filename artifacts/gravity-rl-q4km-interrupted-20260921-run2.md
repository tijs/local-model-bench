# Gravity RL Q4_K_M partial benchmark leg (run 2) — 2026-09-21

**Status: INTERRUPTED / INCOMPLETE / UNRANKED.** This is a second
append-only partial fragment under the same config hash. It is not a retry that
supersedes the earlier four-row fragment and it does not count toward a
completed benchmark.

## Run identity

- Model: `batiai/Gravity-30BA5B-RL-GGUF:Q4_K_M`
- Engine: `llama.cpp`
- Config: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Config hash: `34c266c25d9a`
- Runner SHA recorded by the two new rows: `2ee0259d6728`
- Row timestamps: `2026-09-21T17:37:30Z` and `2026-09-21T17:37:37Z`
- Durable server-log copy: `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T173730Z-config-34c266c25d9a/server.log`
- Server-log SHA-256: `01496dd29c18cfe05fd900841cc9457299abec6cdad6fa7ffaf3417342fd5bf3`

## Durable coverage at reconciliation

Two rows were appended to `results/log.jsonl`:

- `sanity`: 2/2 pass (`sanity-basic`, `sanity-tool`)
- `hermes_ops`: 0/8 recorded in this fragment
- Coding suites: 0/15
- Harness errors among these rows: 0
- Expected current battery: 25 rows (2 sanity + 8 hermes_ops + 15 coding)
- No speed-gate decision or leaderboard rebuild belongs to this fragment.

The existing `/tmp/bench_Gravity-30BA5B-RL-GGUF_gguf-q4km_server.log` was
copied before it could be overwritten. It ends with a server task cancellation;
no matching durable runner trace for this second fragment was found, so the
reason the run stopped is not established. Do not reclassify the fragment as a
clean completion or as a model/engine failure without further evidence.

At reconciliation there was no benchmark runner, prompt worker,
`llama-server`, or benchmark listener remaining. The first four-row partial
fragment is preserved separately in `artifacts/gravity-rl-q4km-interrupted-20260921.md`.
Both fragments remain append-only evidence and must not be merged into a
completed 25-row group.

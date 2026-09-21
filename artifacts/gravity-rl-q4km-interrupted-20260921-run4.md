# Gravity RL Q4_K_M partial benchmark leg (run 4) — 2026-09-21

**Status: INTERRUPTED / INCOMPLETE / UNRANKED.** This is a fourth
append-only partial fragment under the same config hash. It does not supersede
the earlier fragments and it does not count toward a completed benchmark.

## Run identity

- Model: `batiai/Gravity-30BA5B-RL-GGUF:Q4_K_M`
- Engine: `llama.cpp`
- Config: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Config hash: `34c266c25d9a`
- Runner SHA recorded by these rows: `4ee53065eaf4`
- Full runner commit at reconciliation: `4ee53065eaf43c4a76cba7f53344f8b921574b5b`
- Row timestamps: `2026-09-21T21:05:36Z` through `2026-09-21T21:09:44Z`
- Runner trace: `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T210526Z-config-34c266c25d9a.log`
- Runner trace SHA-256: `f71aea0457ad979081e8b3dfae1b7d2cc2cf00d118264cd11deb1e0d5c2941d7`
- Archived server log: `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T210526Z-config-34c266c25d9a/server.log`
- Archived server-log SHA-256: `2d2624e5a0dcd8c5ba1f84c1153dd89e6c4d550d3844e204570d6f9036f47c58`

## Durable coverage at reconciliation

Four rows were appended to `results/log.jsonl`:

- `sanity`: 2/2 pass (`sanity-basic`, `sanity-tool`)
- `hermes_ops`: 2/8 recorded in this fragment (`hermes_ops-selection`,
  `hermes_ops-chaining`), both pass
- Coding suites: 0/15
- Harness errors among these rows: 0
- Expected current battery: 25 rows (2 sanity + 8 hermes_ops + 15 coding)
- No speed-gate decision was reached for this fragment.
- `results/LEADERBOARD.md` was not regenerated from this incomplete leg.

The four raw prompt-result files exist under the ignored
`results/prompt_results/` tree and parse as JSON. The rows carry `run_error: null`,
`harness_error: false`, and `pass: true`; this is evidence for the observed
partial requests only, not completion of the model leg.

## Interruption evidence

The runner trace stops immediately after `hermes_ops-chaining: PASS`; it has no
normal suite-completion or teardown report. The archived server log shows the
pinned Gravity artifact loading and serving on port 8017, then ends while task
1131 is being processed with:

- `cleaning up before exit...`
- `stop: cancel task, id_task = 1131`

No durable evidence establishes why the runner/server stopped. Do not
reclassify this as a clean completion or as a model/engine failure without a
future reproduction.

At reconciliation there was no benchmark runner, prompt worker,
`llama-server`, or benchmark listener remaining. The earlier partial fragments
remain preserved separately in:

- `artifacts/gravity-rl-q4km-interrupted-20260921.md`
- `artifacts/gravity-rl-q4km-interrupted-20260921-run2.md`
- `artifacts/gravity-rl-q4km-interrupted-20260921-run3.md`

## Next action

Keep all four fragments append-only and unranked. Before any successor launch,
verify a fresh single-writer window, free port 8017, no surviving descendants,
the committed partial-evidence boundary, the exact artifact/config provenance,
and a fresh runner SHA. A clean successor must start its own 25-row coverage
from sanity; these fragments must not be merged into it or counted toward its
completion.

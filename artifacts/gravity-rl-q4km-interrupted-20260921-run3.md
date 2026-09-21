# Gravity RL Q4_K_M partial benchmark leg (run 3) — 2026-09-21

**Status: INTERRUPTED / INCOMPLETE / UNRANKED.** This is a third
append-only partial fragment under the same config hash. It does not supersede
the earlier four-row and two-row fragments, and it does not count toward a
completed benchmark.

## Run identity

- Model: `batiai/Gravity-30BA5B-RL-GGUF:Q4_K_M`
- Engine: `llama.cpp`
- Config: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Config hash: `34c266c25d9a`
- Runner SHA recorded by these rows: `53920dc41d65`
- Full runner commit at reconciliation: `53920dc41d653fa1a7b6073b2c9ecd8b88d45e72`
- Row timestamps: `2026-09-21T18:46:09Z` through `2026-09-21T18:51:03Z`
- Archived server log: `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T184609Z-config-34c266c25d9a/server.log`
- Archived server-log SHA-256: `c463e7917732d53cd5dcb7a48991674a383cd01770183ac8ecf188c098913334`

## Durable coverage at reconciliation

Five rows were appended to `results/log.jsonl`:

- `sanity`: 2/2 pass (`sanity-basic`, `sanity-tool`)
- `hermes_ops`: 3/8 recorded in this fragment (`hermes_ops-selection`,
  `hermes_ops-chaining`, `hermes_ops-error-recovery`), all pass
- Coding suites: 0/15
- Harness errors among these rows: 0
- Expected current battery: 25 rows (2 sanity + 8 hermes_ops + 15 coding)
- No speed-gate decision was reached for this fragment.
- `results/LEADERBOARD.md` was not regenerated from this incomplete leg.

The five raw prompt-result files exist under the ignored
`results/prompt_results/` tree. Their JSON is structurally valid; the sampled
assistant messages contain the expected final responses and declared tool calls,
and every row has `run_error: null`, `harness_error: false`, and `pass: true`.
This is evidence for the observed partial requests only, not completion of the
model leg.

## Interruption evidence

The only durable server trace for this fragment is the archived server log. It
shows completed request timing through task `1364`, then:

- `cleaning up before exit...`
- `stop: cancel task, id_task = 1445`

No matching durable runner trace or normal suite-completion/teardown report was
found for this third fragment. The exact reason the runner stopped is therefore
not established by the available evidence. Do not reclassify this as a clean
completion or as a model/engine failure without a future reproduction.

At reconciliation there was no benchmark runner, prompt worker,
`llama-server`, or benchmark listener remaining. The first and second partial
fragments remain preserved separately in
`artifacts/gravity-rl-q4km-interrupted-20260921.md` and
`artifacts/gravity-rl-q4km-interrupted-20260921-run2.md`.

## Next action

Keep all three fragments append-only and unranked. Before any successor launch,
verify a fresh single-writer window, free port 8017, no surviving descendants,
the committed partial-evidence boundary, the exact artifact/config provenance,
and a fresh runner SHA. A clean successor must start its own 25-row coverage
from sanity; these fragments must not be merged into it or counted toward its
completion.

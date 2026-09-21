# Gravity RL Q4_K_M partial benchmark leg — 2026-09-21

**Status: INTERRUPTED / INCOMPLETE / UNRANKED.** This is preserved partial-run evidence, not a completed benchmark result. The run did not reach the runner's terminal coverage or speed-gate decision.

## Run identity

- Model: `batiai/Gravity-30BA5B-RL-GGUF:Q4_K_M`
- Engine: `llama.cpp`
- Config: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Config hash: `34c266c25d9a` (the snapshot is byte-identical to the live config)
- Runner SHA recorded by rows: `bcb8e73140f7`
- Runner log: `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T162327Z-config-34c266c25d9a.log`
- Server log captured by the runner: `/tmp/bench_Gravity-30BA5B-RL-GGUF_gguf-q4km_server.log`

## Durable coverage at reconciliation

Four rows were appended to `results/log.jsonl`:

- `sanity`: 2/2 pass (`sanity-basic`, `sanity-tool`)
- `hermes_ops`: 2/8 observed (`hermes_ops-selection`, `hermes_ops-chaining`), both pass
- Coding suites: 0/15
- Harness errors among observed rows: 0
- Expected current battery: 25 rows (2 sanity + 8 hermes_ops + 15 coding)
- No `results/speed_gate.jsonl` decision for this config was observed.
- `results/LEADERBOARD.md` was deliberately not regenerated from this incomplete leg.

The runner log ends immediately after `hermes_ops-chaining`; it contains no normal suite-completion or teardown section. The server log ends with the server's cancellation/cleanup line after that request. At reconciliation no benchmark runner, prompt worker, llama-server, or benchmark listener remained. The reason the runner stopped is not established by the durable logs; it must not be reclassified as a clean completion or as a model/engine failure without further evidence.

## Evidence handling

The exact config snapshot is preserved at `results/configs/34c266c25d9a.yaml`. The four prompt-result JSON files remain in the ignored `results/prompt_results/` tree. The runner and server logs are archived outside Git under the results-mei directory named in the final handoff.

This partial leg must remain append-only and must not count toward the completed 25-row group. Before any successor launch, verify a single-writer window, free port 8017, no surviving descendants, the committed partial-evidence boundary, and a fresh runner SHA so a clean rerun cannot be merged with this interrupted fragment.

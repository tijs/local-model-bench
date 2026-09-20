# Bonsai 2 PTQ1_0 — fresh native gate and bounded canary (2026-09-20)

**Status: ADMITTED / GATED / UNRANKED.** This unit ran one fresh single-server
native gate and one bounded six-task canary for the current committed config. It
did not run `run_bench.py`, append `results/log.jsonl`, create a config snapshot,
run coding suites, or change the leaderboard.

## Scope and identity

- Config: `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`
- Config hash: `7cec26d1f1cc`
- Config SHA-256:
  `7cec26d1f1cc2a40d232e547ec66287227182ff39c79894b5dde4b9665e841ad`
- Run HEAD / canary runner SHA: `421fc0ae3d121697fb370d14de8dcbf880537fec`
  / `421fc0ae3d12`
- Served identity: `bench-7cec26d1f1cc`
- Endpoint: `http://127.0.0.1:8017/v1`
- Inference engine: `llama.cpp-prism` (not stock `llama.cpp`)
- Artifact: `prism-ml/Ternary-Bonsai-2-27B-gguf` revision
  `6ed5e12bf84b7a63069882c91dd9e9218647d17b`,
  `Ternary-Bonsai-2-27B-PTQ1_0.gguf`
- Artifact bytes: `5,946,648,928`
- Artifact SHA-256:
  `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`
- Prism runtime: `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6`, local binary
  `--version`: `0.2.0-dev (build 1, commit 5d80cff)`

## Preflight and teardown

- The protected benchmark tree was clean at preflight; the config was already
  committed at `HEAD`.
- The artifact resolved to the pinned HF blob, with the expected size and SHA-256
  re-verified before launch.
- Free disk was `17,107,083,264` bytes / `15.932 GiB`, above the current
  `10 GiB` launch floor.
- All benchmark ports were free after `runner/unload_all.sh` preflight. No
  benchmark runner, Mei, llama-server, Prism, or probe process was active.
- The server ran alone on shared port 8017. `runner/unload_all.sh` reclaimed the
  exact candidate server after the canary; the supervising launch process exited
  0, and all benchmark ports were free afterward.
- No CoCore action was performed.

## Fresh native gate

The gate ran from `05:25:18` to `05:42:06` local time. All seven checks passed:

| Check | Result |
|---|---|
| Exact `/v1/models` identity | HTTP 200; sole served ID `bench-7cec26d1f1cc`; `n_ctx=65536`; fingerprint `b1-5d80cff` |
| Plain non-stream | `READY`, `finish_reason=stop`, 3.4311 s |
| Plain streaming | `STREAM_READY`, 31 chunks, no raw-line errors, 2.9625 s |
| Native non-stream tool | One `lookup({"city":"Amsterdam"})`, `finish_reason=tool_calls`, 7.5988 s |
| Native streaming tool | One `lookup({"city":"Rotterdam"})`, 27 chunks, no raw-line errors, 4.0578 s |
| Growing cache reuse | Second request reported `cached_tokens=66`; response `CACHE_RECALL_7` |
| Context boundary | Exactly 64,900 content tokens; HTTP 200 at `prompt_tokens=64,952`, `total_tokens=64,953`; 930.5534 s; expected `finish_reason=length` with `max_tokens=1`, no crash |

The context probe's recorded prompt throughput was 69.7602 tokens/s. The server
remained responsive and was torn down only after the canary completed.

Raw native-gate evidence:

- `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260920T-current-7cec26d1f1cc/native-gate.json`
- SHA-256: `466383da138de3132137059fa861e182b54f647f7e9430e8ef9a363bbb2a417a`

## Bounded canary

The completed canary ran one trial with `max_tokens=2048`, `max_turns=2`,
temperature 0, and the fixed six-task surface. It ran from `05:54:21` to
`06:00:31` local time, 369.9682 seconds wall time.

- `sanity-basic`: **PASS**, 2.8857 s
- `hermes_ops-chaining`: **error**, `max_turns (2)`, 21.3771 s
- `hermes_ops-noisy-result`: **error**, `max_turns (2)`, 38.1889 s
- `kiem_mini-feature`: **error**, response truncation at `max_tokens=2048`, 144.7626 s
- `kiem_mini-testwrite`: **error**, response truncation at `max_tokens=2048`, 145.0961 s
- `canary-multi-turn`: **PASS**, `cache-reuse-ok`, 17.6373 s

Summary: `completed=true`, `2 passed`, `0 failed`, `4 errors`. The errors are
model/output-budget behavior in this deliberately small canary, not transport or
harness failures. The two passing tasks were deterministic in this one-trial run.
This canary is exploratory evidence only and does not rank the candidate.

Committed canary artifact:

- `artifacts/bonsai2-ptq1-canary-20260920-7cec26d1f1cc.jsonl`
- SHA-256: `d4d87b6b08c13a3c20043c7385debab043e6ae9eab5916131801334757278e0d`

## Preserved bounded-scope interruption

A first canary attempt used `max_tokens=8192`, `max_turns=6`, which was not the
intended small time-boxed setting. It was stopped after the exact owned canary
process produced the run row plus three task rows; no server or foreign process
was stopped. The four-row partial is retained as interrupted evidence, not merged
with the completed canary and not used for ranking:

- External file:
  `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260920T-current-7cec26d1f1cc/canary-8192-t6.interrupted.jsonl`
- SHA-256: `9d0ec6c0c91283dd9426e9ab1e58bb6b15a219f28699ab04132396bb7fda7d64`
- Coverage: `sanity-basic` passed; `hermes_ops-chaining` and
  `hermes_ops-noisy-result` reached `max_turns (6)` errors; the process was
  stopped before later tasks.

## Archived server evidence and decision

- Archived server log:
  `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260920T-current-7cec26d1f1cc/server.log.snapshot`
- SHA-256:
  `098ce147d50158e4e320938a0cf565911972b54ba24f9977d8cfd725fbd40a14`
- The candidate remains **gated/unranked**. The native gate proves loadability,
  exact identity, streaming, native tools, cache reuse, and the 64K boundary; the
  canary does not justify a 25-row battery, and `orchestration.hermes_provider`
  remains `null`.
- Keep this PTQ1_0 lane separate from stock llama.cpp, PQ2_0, MLX, and Gravity
  lineages. No `results/log.jsonl` rows or leaderboard entry belong to this unit.
- Next authorized direction is the separate Bonsai MLX/Mei path review and its
  safe memory/context boundary, not a full PTQ1_0 ranking run. Gravity RL remains
  a later separate candidate.

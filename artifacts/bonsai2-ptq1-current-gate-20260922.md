# Bonsai 2 PTQ1_0 — fresh native gate and bounded canary (2026-09-22)

**Status: ADMITTED / GATED / UNRANKED.** This unit ran one fresh
single-server native gate and the requested small six-task canary against the
committed PTQ1_0 config. It did not run `run_bench.py`, append
`results/log.jsonl`, create a benchmark config snapshot, run coding suites, or
change the leaderboard.

## Scope and immutable identity

- Config: `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`
- Config SHA-256:
  `5b760871ce846bcffe2d8c220a2051f7cbe76eb41abfa490f7276ac0462dfc91`
- Config hash: `5b760871ce84`
- Run HEAD: `a744596adb9756bf50e4ad111e04cc9307579ee4`
- Canary runner SHA: `a744596adb97`
- Served identity: `bench-5b760871ce84`
- Endpoint: `http://127.0.0.1:8017/v1`
- Inference engine: `llama.cpp-prism` (not stock `llama.cpp`)
- Artifact: `prism-ml/Ternary-Bonsai-2-27B-gguf` revision
  `6ed5e12bf84b7a63069882c91dd9e9218647d17b`,
  `Ternary-Bonsai-2-27B-PTQ1_0.gguf`
- Artifact bytes: `5,946,648,928`
- Artifact SHA-256:
  `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`
- Prism runtime: `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6`; local binary
  reports `0.2.0-dev (build 1, commit 5d80cff)`.

The working config was byte-identical to `HEAD` before the unit. The config's
`hermes_provider` remains `null`, so this bounded unit was not eligible for a
coding-suite battery.

## Preflight, process ownership, and teardown

The preflight evidence recorded:

- free disk: `21,909,282,816` bytes / `20.4046 GiB`, passing the 10 GiB launch
  floor;
- the exact artifact present with the expected size and SHA-256;
- a clean protected checkout at HEAD `a744596...`;
- no matching benchmark processes and no benchmark listeners before launch.

The server was the only backend on shared port 8017. The run summary recorded no
matching runner/canary/server processes and no benchmark listeners after the
canary. The archived server log ends with the server cleanup message. No CoCore
action was performed.

## Fresh native gate

All seven checks passed on the exact binary and artifact:

| Check | Result |
|---|---|
| Exact `/v1/models` identity | HTTP 200; sole served ID `bench-5b760871ce84` |
| Plain non-stream | `READY`, `finish_reason=stop`, 3.6017 s |
| Plain streaming | `STREAM_READY`, 32 chunks, no raw-line errors, 3.0736 s |
| Native non-stream tool | `lookup({"city":"Amsterdam"})`, `finish_reason=tool_calls`, 8.7741 s |
| Native streaming tool | `lookup({"city":"Rotterdam"})`, 42 chunks, no raw-line errors, 5.2346 s |
| Growing cache reuse | Recall reported `cached_tokens=312`; response `CACHE_RECALL_7` |
| Context near boundary | 64,900 content tokens; 64,951 prompt tokens; HTTP 200; `finish_reason=length`; 930.5115 s; no crash |

The context probe reached the 65,536-token harness ceiling boundary and the
server remained usable for the following canary.

Raw native-gate evidence:

- `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260922T-current-5b760871ce84/native-gate.json`
- SHA-256: `290cd6d8bd8aec87d7b1ffa5925a749450c1210b41259585b9044155d3ce53d0`

## Bounded canary

The canary used one trial over the fixed six-task surface with
`temperature=0`, `max_tokens=2048`, `max_turns=2`, and a 300-second request
budget. It completed with `2 passed`, `0 failed`, and `4 errors`:

- `sanity-basic`: **PASS**, 3.3129 s
- `hermes_ops-chaining`: **error**, exceeded `max_turns (2)`, 270.5992 s
- `hermes_ops-noisy-result`: **error**, exceeded `max_turns (2)`, 38.4509 s
- `kiem_mini-feature`: **error**, response truncated at `max_tokens=2048`, 148.5724 s
- `kiem_mini-testwrite`: **error**, response truncated at `max_tokens=2048`, 149.0507 s
- `canary-multi-turn`: **PASS**, `cache-reuse-ok`, 17.7991 s

The canary completed normally (`completed=true`). The four errors are model /
output-budget behavior in this deliberately small exploratory canary, not
transport or harness failures. The two passing tasks were deterministic in the
one-trial run. This evidence does not justify expanding to a 25-row battery and
does not confer rank.

Raw canary evidence was copied into the repository:

- `artifacts/bonsai2-ptq1-canary-20260922-5b760871ce84.jsonl`
- SHA-256: `a736be9700d3391607ee10ef50797e94b4b016254d0ef9fade6d6425c0b5c338`

The run directory retains the original:

- `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260922T-current-5b760871ce84/canary-2048-t2.jsonl`
- SHA-256: `a736be9700d3391607ee10ef50797e94b4b016254d0ef9fade6d6425c0b5c338`

## Archived server evidence and result boundary

The server log was archived after teardown at:

- `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-PTQ1_0/prism-20260922T-current-5b760871ce84/server.log.snapshot`
- SHA-256: `9115c9601e0080ea37af9099d1a6d79fc46eeb0e2d195a93f944b180d7d7187c`

Supporting raw files:

- `preflight.json` SHA-256:
  `16130279134ab2f3a19fb4f078242f56b874b124f048534acc8eaeca9cae3e78`
- `run-summary.json` SHA-256:
  `55b0ea63aefa8a2252eaf031786658a5d9e769645ae437262e1d8830fc3a9f19`

A scoped row audit found **zero exact PTQ1_0 rows** under config hash
`5b760871ce84`; there is no PTQ1_0 leaderboard entry. The candidate remains
separate from stock `llama.cpp`, PQ2_0, MLX, and Gravity lineages.

## Decision and next direction

Keep PTQ1_0 **gated and unranked**. The fresh gate proves exact load identity,
plain and streaming generation, native tools, cache reuse, and the 64K boundary.
The canary's 2/6 result with four slow/output-budget errors is exploratory model
behavior only. Do not start a full PTQ1_0 battery from this evidence.

The serialized queue may proceed only through its separately gated next unit;
Gravity Base remains blocked by its source-size/disk gate, and the Bonsai MLX/Mei
candidate remains blocked on the already-recorded safe memory boundary unless a
new source-reviewed remedy or larger-device gate is available.

# Bonsai 2 PTQ1_0 — interrupted benchmark attempt (2026-09-23)

**Status: interrupted partial evidence; not a completed benchmark leg.** This
attempt is preserved separately from the already committed 2026-09-22 native
gate/canary. It must not be counted as current-suite coverage or used to rank the
candidate.

## Identity

- Config: `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`
- Config hash: `5b760871ce84`
- Config SHA-256: `5b760871ce846bcffe2d8c220a2051f7cbe76eb41abfa490f7276ac0462dfc91`
- Runner SHA carried by the appended rows: `0d384a593830`
- Model: `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0`
- Engine: `llama.cpp-prism`
- Expected shared port: `8017`

The untracked snapshot `results/configs/5b760871ce84.yaml` is byte-identical
to the live config and is preserved with this partial evidence.

## Durable rows

Exactly two rows were appended to `results/log.jsonl`, both from the `sanity`
suite and both with `harness_error: false`:

- `sanity-basic`: PASS, 2.836 s wall, 10.58 tok/s, timestamp
  `2026-09-23T06:05:40Z`.
- `sanity-tool`: PASS, 14.224 s wall, 8.44 tok/s, timestamp
  `2026-09-23T06:05:54Z`.

No `hermes_ops` rows, coding rows, speed-gate record, complete-suite summary,
or terminal `run_bench.py` result was observed. The two rows are therefore an
interrupted fragment, not a valid benchmark completion.

## Interruption evidence

The captured server log shows the pinned binary loading the exact PTQ1_0 file,
serving on `127.0.0.1:8017`, completing the two short sanity requests, then
starting another request (`task 184`) whose prompt prefill reached 18,432 tokens
before the server logged `cleaning up before exit` and canceled that task. The
reason the supervising runner disappeared is not independently established;
this note does not label it as a model or harness failure.

Archived server log:

- `artifacts/bonsai2-ptq1-interrupted-20260923-server.log`
- SHA-256: `c85869ce950087659b513fb6513c12534425a229ab234c69abced02e215e84f9`
- Size: 6,058 bytes

At reconciliation time there was no surviving benchmark runner, prompt worker,
`llama-server`, or listener on the benchmark ports, including 8017. The server
was not left running. No CoCore action was taken.

## Decision boundary

The 2026-09-22 native gate and six-task canary remain the authoritative bounded
Bonsai PTQ1_0 admission evidence: exact identity, plain and streaming
completion, native tools, cache reuse, and the 64K boundary passed, while the
exploratory canary was 2/6 with four model/output-budget errors. This
2026-09-23 fragment adds no completed benchmark coverage and does not justify a
full 25-row battery. Keep the candidate gated and unranked and preserve this
fragment append-only.

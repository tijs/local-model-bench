# Groot on distributed Mei rc.2: seed 17

**benchmark-v9.8: 11/12 household, 3/3 Python in 10m19s.**
All 15 tasks completed. All 122 pressure samples were normal, with zero swap
growth. All 16 model files and both released executable/Metal hashes match after
the run. The owned server exited and ports 8017/8024 are free.

[Verified cohort report](../../results/FINALISTS_V9.8_SEED17.md) ·
[Exact selection](../../results/finalists-v9p8-seed17-20261102.json) ·
[Committed profile](../../configs/candidates-20261101/groot-rc2-v9p8-seed17.yaml) ·
[Predeclared repeat design](../../docs/FINALIST_REPEATS.md)

## What was measured

- Household `20261102T012146Z-2a0bbb3b`; Python `20261102T012748Z-fc4bfc6b`.
- Released benchmark source `501fa1be08da37ee7dd996176dbeda4c10eaa8c1`.
- Mei source `7e88dfdd614e77ee5662f920394ca1e3e868050a`, distributed rc.2
  executable SHA-256 `11b08e245c5ee19be603d215f3c572b8a02284f059a41646f3b6f7e9d821bc27`.
  No Swift build occurred. Both tracks verified the listening executable and
  its exact binary/Metal hashes.
- Public text artifact at `53f52e0eb8d67d2941010688b2a6b8807d9a3bea`, with
  the same language tensor payloads as the earlier measured derivative.
- Request seed 17 verified in all 65 saved task responses' resolved generation
  metadata. It is a declared trajectory control, not an independence guarantee.
- Full-run wall 618.987s includes startup, live admission and both tracks; the
  separate 30-second host baseline is excluded. Minimum free percentage 42 is
  telemetry. Near-64K quality/capacity and actual Peixinho acceptance are not
  established by these short tasks.

## Deleted-source failure

The second user message says the pickup source was deleted and asks to check
current records without reusing the old answer. Groot correctly searched current
records and said the code was no longer available, but also wrote:

> My earlier record `family-fact` (which contained code 6412) has been removed

The old numeric value is repeated
inside the historical parenthetical. `deleted_source_not_reused` fails that
reuse; all other checks pass, including absence admission and no unsafe/invalid
calls. This is not the Clover paraphrase false negative: “no longer available”
is recognized by the corrected grader; the independent stale-value guard fails.
The documented exception permits a separate unambiguous obsolete-code sentence,
not unrestricted historic-value narration after a deletion. Keep the failure and
its narrow interpretation visible. This is a task-contract failure, not evidence
that the code value itself was hallucinated or asserted as currently available.

All twelve grades reproduce under the frozen measured grader. Every parsed
API name/argument matches the tool journal, and all three submitted scripts
reproduce their saved results on four isolated variants each. No critical
boundary breach, unauthorized mutation, unsafe attempt or invalid tool call occurred.

[Audit and script replay](audit.json) · [Audit program](audit.py) ·
[Model hashes](post-run-model-hashes.json) · [Released asset hashes](post-run-release-hashes.json)

## Disk-cache accounting and cleanup

The 512 MiB prefix setting bounds resident prefix state. The backend has a
separate 10 GiB default disk tier; it retained 7,881,053,430 bytes (~7.34 GiB) here.
Disk free declined from 22.14 GiB to 14.96 GiB, remaining above the actual 10 GiB
stop threshold. This is generated KV data, not a memory leak or retained weights.

The server exited before cleanup. Its 74 generated KV files were inventoried,
SQLite schema/counts captured, and only this fresh run's owned `kv/` directory
was removed. Logs, request telemetry, task traces, staged weights and release assets
remain intact. Free space afterward was 23,767,846,912 bytes.

[Pre-cleanup inventory](post-run-runtime-inventory.json) ·
[Index summary](cache-index-summary.json) · [Cleanup receipt](owned-cache-cleanup.json)

## Interpretation and next run

Groot remains a strong provisional candidate, with a deletion-response weakness
on this declared seed. Its prior 12/12+3/3 v9.5 result remains unchanged, with
separate model/runtime/method identities. This first v9.8 trial does not prove a
runtime regression or establish superiority over Logics-SWE. The remaining
predeclared trials must run and all outcomes remain public.

```sh
uv run --locked python artifacts/groot-rc2-v9p8-seed17-20261102/audit.py
uv run --locked python runner/build_agent_leaderboard.py \
  --campaign results/finalists-v9p8-seed17-20261102.json \
  --output results/FINALISTS_V9.8_SEED17.md
```

The runtime/output paths are consumed. The next predeclared run is Logics-SWE
seed 17, after this review and fresh normal-pressure/flat-swap admission.

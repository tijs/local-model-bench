# Groot: first Mei rc.2 native qualification

**Failed qualification: 11 of 13 checks passed.** This run adds no household or
Python task rows and does not replace Groot's completed v9 task result.

The guarded attempt completed in 456.619 seconds, including a 226.72-second
release build. All 90 pressure samples were normal and swap did not grow. The
parent stopped the owned server. All 16 staged model files matched their
pre-run hashes afterward; logs were copied before removing 2,030,241,999 bytes
of owned KV files. Model weights and earlier scored evidence were retained.

## What passed and failed

Identity, status at idle, plain completion, replayed tool-result history,
stream/nonstream parity, repeated-prefix cache reuse, growing-history cache
reuse, the exact 65,536-token prompt and over-cap rejection passed.

Both direct `add_numbers` probes failed because no structured call was present.
The [request metadata](server-logs/requests.jsonl) shows both generated exactly
256 tokens and ended with `finish: length`, matching the probe's token cap.
This establishes budget exhaustion in this attempt. It does not establish
whether a larger declared budget will produce a correct call. The failed
validator did not preserve the response envelope, so the generated text is
unavailable. Improve failure diagnostics before a fresh source-pinned run;
retain the same call-name, argument and finish-reason requirements.

A separate five-second status GET during full-context prefill timed out; see
[the observation](status-observations.jsonl). This is an unresolved responsiveness
observation, distinct from the successful idle-status and context probes. No
root cause is claimed.

## Reproducible identities

- Config: [committed source](../../configs/mei-rc2-native-20261101/groot.yaml)
  and [captured snapshot](config.yaml).
- Mei: `526204babd1b4649cfd2b5e538e163775d5ae932`.
- vmlx: `f6510fc384bcddb5db9efc96e1dd5ab3afc49346`.
- Model: `Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly`
  at `53f52e0eb8d67d2941010688b2a6b8807d9a3bea`.
- Executable SHA256:
  `11b08e245c5ee19be603d215f3c572b8a02284f059a41646f3b6f7e9d821bc27`.
- Metal library SHA256:
  `e87ac8aa940ace7dd1f9945c4b6a3238c3d94604391e0f36a0ac51259bd76f32`.

[Probe results](probe.json) · [Final outcome](outcome.json) ·
[Launch/runtime record](record.json) · [Resources](resources.jsonl) ·
[Post-run hashes](post-run-model-hashes.json) ·
[Owned KV inventory](owned-kv-cleanup.json)

Mei rc.2 is not qualified or published by this result. Stable Mei remains 0.9.0.

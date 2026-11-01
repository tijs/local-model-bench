# Groot: Mei rc.2 native qualification passed

All **13 native checks passed** in 228.389 seconds, including startup/build and
excluding the host baseline. All 45 pressure samples were normal, with zero
swap growth. This is release admission, not a new household or Python score.

Streaming and nonstreaming direct calls each completed correctly in 285 tokens.
The [earlier attempt](../mei-rc2-native-groot-20261101/README.md) failed at its
256-token cap. This fresh run declares 1024 reasoning-inclusive tokens, matching
the plain probe. Tool names, arguments and finish-reason checks are unchanged;
the probe also now preserves failed API envelopes and streamed reasoning.

Passed: model identity, idle status, plain output, both direct tool paths,
tool-result history replay, stream/nonstream parity, repeated and growing-prefix
cache reuse, exact 65,536-token prompt admission and 65,537-token rejection.

Source: Mei `e3e4bb04fbc038926ff890fb854aeb9b5c27f977`, vmlx
`f6510fc384bcddb5db9efc96e1dd5ab3afc49346`. Public Groot artifact:
`Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly` at
`53f52e0eb8d67d2941010688b2a6b8807d9a3bea`. See the
[committed config](../../configs/mei-rc2-native-20261101/groot-tools1024.yaml),
[probe results](probe.json), [outcome](outcome.json) and
[runtime identity](record.json).

All 16 staged model-file hashes matched after the run. The owned server stopped;
logs were saved and 2,030,242,061 bytes of owned KV files inventoried and removed.
Weights remain staged. See [post-run hashes](post-run-model-hashes.json) and
[KV inventory](owned-kv-cleanup.json).

The executable and Metal library are byte-identical to the first native
attempt. They are also the artifacts packaged for rc.2; the release source adds
documentation only after the tested revision. See
[package equivalence](../candidate-system-campaign-20261101/mei-rc2-validation/packaged-native-equivalence.json).

Stable promotion remains open. The separate five-second status timeout during
the first attempt's long-context prefill remains unresolved; this run does not
repeat that diagnostic or establish responsiveness under load. Older scored
benchmark runs keep their own source and binary identities.

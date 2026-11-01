# Early-residency Clover candidate: native tools passed

The isolated loader candidate passed all five native diagnostic checks in
25.683 seconds, excluding the baseline: identity, plain output, streaming and
nonstreaming automatic tools, and dependent continuation. All five resource
samples were normal, with zero swap growth. The owned server stopped and all
15 model files matched afterward.

Source: local derived `211b2b47c59e42cbe16ce81b08c96ac1dff23d6c`, tree
`3cfca8464b5c560e272f763632d31420b0ee8b50`, executable SHA256
`5f42ec14ab1c62b2fdbf5121e0deee83452576fdfce50b194a49f4119453546f`.
The public [base, patch, license and build/test provenance](../candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/)
reproduce the source; the local commit is not a fetchable upstream revision.
The original runtime remains intact.

This clears basic native admission on this binary, not the repeated-load memory
issue. Both the original runtime and this candidate passed short native checks;
the repeated cold-load/cache experiment is still required. No full score,
cache-equivalence, near-capacity, performance or broad numerical claim follows.

[Outcome](outcome.json) · [Probe results](probe.json) ·
[Dependent trace](dependent-admission.json) · [Server](server.log) ·
[Post-run hashes](post-run-model-hashes.json)

# Early-residency cache experiment: partial pass, harness recovery timeout

The candidate completed four process loads with all 70 resource samples normal
and no swap growth (3,378.25 MiB initially, 3,346.25 MiB at the end). The repeated
prompt case passed: both cold outputs matched exactly, and the warm output
matched both including reasoning and tool arguments. Warm cached tokens were
1,577; both cold legs reported zero. The growing-history and partial-block
comparisons remain incomplete, so this attempt is unqualified and unranked.

The runner stopped after 358.353 seconds because its added post-exit VM recovery
condition timed out before starting a fifth process. No pressure, swap, disk or
deadline stop occurred. The owned server stopped and all 15 model-file hashes
matched afterward.

The final compressor total was 1.03336 GiB against an initial 0.53079 GiB. That
missed the self-added initial-plus-512-MiB ceiling by about 2.6 MiB even though
the established normal-pressure/flat-swap baseline passed. Wired memory was
below the initial baseline. Global VM counters include unrelated activity and
were not evidence that an owned model remained allocated.

This was an unnecessarily strict harness condition, not a model/resource
failure. The fresh profile keeps VM bytes as telemetry and uses seven normal,
flat-swap recovery samples after the exact owned process exits, with the same
90-second bound and all global runtime stop limits unchanged. The existing
byte capacity plan remains in force. No prior evidence or grade is rewritten.

The early-residency loader candidate has promising repeated-load evidence,
not a universal memory-fix claim. Its complete three-case cache verdict and
full task evaluation are still required.

[Comparison checkpoint](cache-comparison.json) · [Outcome](outcome.json) ·
[Resource trace](resources.jsonl) · [Final recovery](recovery-4.jsonl) ·
[Post-run hashes](post-run-model-hashes.json) ·
[Source preparation](../candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/)

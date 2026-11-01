# local-model-bench benchmark-v9

Corrects an ambiguous-capture validator false negative: an explicit invitation to
save as a private note or private task can introduce a numbered list with a colon.
It does not need a question mark. Regression coverage includes both partitions,
non-request lists, a public destination and the independent persisted-route checks.
Existing imperative and question forms retain their behavior.

This changes the household measurement method. Old rows retain their original
grades and source fingerprints. Fresh comparisons are required; v8 scores are
historical references, not v9 results. Python contracts and budgets are unchanged.

Also adds a separate ThinkingCap profile with `--ctx-checkpoints 2` and a 512 MiB
retained-snapshot budget. The first profile admitted but stopped for sustained
warning pressure, retaining ten snapshots of about 200 MiB each. `--cache-ram 0`
does not disable those snapshots. The retry preserves weights, sampler, 65,536
context, f16 K/V and GPU placement; it changes the cache profile. The original
profile and interrupted attempt remain preserved and unranked. A fresh native
gate and actual pressure/swap/disk/deadline supervision are still required.

See the [campaign guide](../CANDIDATE_CAMPAIGN.md) and
[latest completed v8 comparison](../../results/CANDIDATES.md). No v9 model result
is claimed by this release, and no test represents real Peixinho acceptance.

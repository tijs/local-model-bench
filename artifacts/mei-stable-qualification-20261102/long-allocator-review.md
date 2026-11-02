# Long-context allocator screen: negative result

Four predeclared same-binary ABBA cells completed with exact observable parity,
60 matching model-file hashes and owned cleanup of 2,975,024,082 bytes. All
40 measured observations are retained; each allowance/context averages two
processes equally. These are diagnostic observations, not scored tasks.

| Allowance | Mean short TPS | Mean 30K TPS | Process short medians | Process 30K medians |
|---|---:|---:|---|---|
| 512 MiB | 69.70 | 49.88 | 69.93, 69.58 | 49.94, 49.92 |
| 1024 MiB | 53.72 | 37.90 | 67.53, 39.51 | 36.17, 39.24 |

The 1 GiB allowance did not remove the slow process band and had lower means
in both contexts. It is not a sufficient fix and is not promoted. The 512 MiB
processes demonstrate that the unchanged candidate can run near 70/50 TPS;
earlier slow processes and the material matched-source deficit remain intact.
No patch-specific or general speed improvement has been established.

The guard did not stop any cell. Full telemetry reveals one isolated warning
sample in A1 and one in B1, each followed by normal pressure; all other samples
were normal. Swap never grew (1572.5→1564.5 MiB). The existing policy allows
isolated warnings and stops two consecutive warnings; it was unchanged.

`model-free-device-budget-review.json` records the effective total allocation
limit of 24,051,816,857 bytes (22.4 GiB). The conservative GPU working budgets
in the configs exceed it by about 82.5 MiB at 512 MiB cache and 594.5 MiB at
1 GiB cache. These are allowances, not simultaneous allocation measurements,
so this is a lead rather than a diagnosis. The model-free Metal query reports
recommended working set 26,800,603,136 bytes on this 32 GiB M1 Max; the query
process allocation is not the model allocation. No system limit was changed.

Next review: inspect exact MLX allocator-limit semantics, then test a pinned
explicit total limit that fits the numeric physical budget at fixed 512 MiB
cache. Keep all physical pressure/swap/disk/deadline guards. Do not keep raising
the allocator reuse allowance or promote a default from these results. Full
native gates, stable distribution and all-four scored/context-speed results
remain open.

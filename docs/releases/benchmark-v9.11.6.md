# benchmark-v9.11.6

The comparison report can now validate a profile committed before its run
separately from the frozen benchmark method release. It checks the exact
configuration bytes against both the run's recorded source and the supervising
process's recorded source; method and lifecycle fingerprints remain checked
against the tagged release. Existing release-pinned comparisons retain their
original policy.

The repository includes a fresh two-seed comparison of Qwen, Ornith, Groot and
Logics using the v9.11.5 benchmark method. Mei profiles use stable Mei 0.10.0;
Logics is a llama.cpp control. See [the comparison](../../results/FOUR_MODEL_MEI010.md)
for individual traces, audits, averages, limitations and serving profiles.
MiniCPM is not included in these averages: its fresh follow-up has not completed.

Verification: 810 model-free runner tests passed, including 53 focused report
and leaderboard tests. This release changes reporting and published results; it
does not change benchmark tasks or regrade historical runs.

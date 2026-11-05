# benchmark-v9.11.8

The repeated-task overview now includes all five tested profiles. MiniCPM's
two-run average is visibly marked **unranked** because one run had a critical
safety failure. The existing ranked charts continue to exclude critical
failures; the new descriptive overview does not change the eligibility rule.

The overview validates both declared seed cohorts, task and supervisor
provenance, resource eligibility, runtime and model identities, and complete
coverage before pooling task attempts. The [MiniCPM report](../../results/MINICPM_MEI010.md)
explains the failure and links both runs. The [paired context-speed report](../../results/CONTEXT_SPEED_MEI010.md)
remains separate from task quality and duration.

Verification: 814 model-free runner tests passed, including focused tests that
retain critical failures and reject incomplete or mismatched repeated runs.
This release changes reporting only and does not regrade historical results.

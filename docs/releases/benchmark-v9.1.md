# local-model-bench benchmark-v9.1

Adds a separately pinned MiniCPM CPU8/q8-KV profile that disables CPU weight
repacking and retains at most two recurrent context checkpoints. Task contracts,
validators, budgets and runtime source are unchanged from v9. Existing profiles
and raw results retain their original identities.

The matched v9 retry stopped during startup, before native admission or any task.
Its log reports 3,852 MiB of CPU repacking buffers. The new profile avoids that
allocation and budgets 128 MiB for two recurrent snapshots, above the observed
62.81 MiB recurrent state each. These are explicit memory controls, not a lower
pressure threshold. Fresh native admission, full tasks and actual resource
supervision remain required; CPU kernel choice may affect speed or numerics.

ThinkingCap's completed v9 result is 11/12 household and 3/3 Python in 8m 47s,
with normal pressure throughout and no swap growth. MiniCPM's previous completed
v8-method result remains 12/12 and 2/3; no v9 score is inferred from it. See the
[current comparison](../../results/AGENT_V9.md) and
[campaign guide](../CANDIDATE_CAMPAIGN.md).

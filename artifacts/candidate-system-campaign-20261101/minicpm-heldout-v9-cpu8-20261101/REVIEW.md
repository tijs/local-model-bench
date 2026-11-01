# MiniCPM matched v9 startup interruption

The unchanged CPU8/q8-KV profile stopped for two consecutive warning-pressure
samples after 218.384 seconds, before health/native admission or task rows.
No v9 score exists. Its earlier completed v8-method 12/12 household and 2/3
Python score remains unchanged and online.

Baseline pressure was normal with flat swap. The final swap observation was
1,523.88 MiB versus baseline 1,009.44 MiB (514.44 MiB growth). The server was
stopped by the owned supervisor; no model task failure is inferred.

The log reports 3,852 MiB CPU_REPACK model buffers, 680 MiB KV and 62.81 MiB
recurrent state. It warns about CPU overrides with mmap. This identifies a
material allocation to test, not proof of exclusive causality. A separate
profile disables repacking and limits recurrent checkpoints to two. Weights,
CPU8 placement, context, cache precision and sampler remain fixed; CPU kernel
choice can alter speed/numerics, so fresh admission and full validation are
required. No unchanged retry or weakening of the actual resource guard.

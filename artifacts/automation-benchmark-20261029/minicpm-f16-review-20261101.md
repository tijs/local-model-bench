# MiniCPM Q4_K_M f16-KV attempt: resource interruption

Owned runminicpm-heldout-v8p1-20261101 passed startup, plain completion and native
three-step tool admission. During the first household task two kernel-warning
samples triggered teardown at32.112seconds. The sole task row is interrupted,
not a model task failure. No Python task ran. No task score is established.

Host wired memory rose from2.51GiB idle to24.00GiB, with normal pressure before
loading and warning pressure during task startup. Swap stayed952.19MiB, no growth.
All auxiliary work was paused while inference ran. This is actual resource
pressure, not a launch-percentage cutoff or an admission/protocol failure.

The pinned qwen35moe source/metadata calculation remains applicable: ten dense
K/V layers at65536 tokens use1280MiB f16 cache, plus62.8125MiB f32 recurrent
state. The GPU working-set delta is consistent with model/cache/work buffers;
no unbounded cache/leak is demonstrated by this short run. The static4GiB host
allowance was an estimate, not a reservation or proof of a safe total budget.

Prepare a new profile with the same requested Q4_K_M artifact,65536context,
native sampler, runtime pins and full task/validator budgets. Use q8_0 K/V and
ubatch64. Q8_0 stores32 values plus a2-byte scale in34 bytes, so dense K/V becomes
680MiB (600MiB saved); recurrent f32 state is unchanged. The pinned Metal path
supports quantized caches with Flash Attention and compatible256-wide heads.
Its temporary f16 conversion workspace is already reserved even for f16 cache,
so do not claim the entire workspace vanishes. Smaller ubatch reduces prefill
working demand. Cache precision can affect outputs: fresh admission/full task
run is required. Keep all real pressure/swap/disk/deadline stops.

Original profile/snapshot/rows/logs remain unchanged. Server stopped; no disk-KV
cache was configured. Preserved server log and post-load model hash are under
the owned run directory. This configuration-only addition will be released with
an explicit method/tree-equivalence audit for unchanged Qwen/Ornith profiles;
raw measurements will not be relabeled or rewritten.

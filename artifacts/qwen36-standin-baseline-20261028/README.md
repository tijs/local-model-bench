# Qwen3.6 stand-in baseline

Prospectively pinned baseline on benchmark-v6 / peixinho-standin-v1. Retained
Tostibrown/Qwen3.6-35B-A3B-4bit-textonly; parent source revision38740b84,
local exact file hashes in model-files-before.json. This derivative has its
vision tower removed and is not relabelled as the upstream stock model.

Runtime: Mei5c4b2c95 (test-only addition beyond009b7adc), VMLX5b2ffe15,
MLX0.32.2. Same corrected runtime used for the latest Flint investigation.
Qwen native historical samplerT0.6/p0.95/k20,1024prefill,65536contextcap,
8192servermax. Unsafe/compiled decode disabled,512MiBprefix quota,
512MiBallocator pool, mmap true, no disk KV tier. Hybrid cross-turn restoration
may consequently report zero reuse. This is a new baseline configuration, not
a reproduction of old Hermes-era settings or scores.

One weight owner, >=70%free and normalpressure before launch, normal10GiB disk
gate. Existing5-second supervisor stops criticalpressure, sustainedwarning or
<=20%free,2GiBswapgrowth,16GiBswap or<10GiBdisk. Four-task smoke admission
precedes all12 development tasks. Review all failures before promotion; task
quality failure alone is not a transport or runtime defect. Owned server is
stopped after each invocation. No Hermes/CoCore lifecycle, real household state
or old-result rewriting. Same pilot budgets as Flint:12turns,1536tokens/turn,
300s/task. Initial trajectories are calibration, not independent samples or
real Peixinho acceptance. Post-run results and source hashes will be appended.


## First smoke attempt: memory-gated interruption

Run20261028T220421Z-372ddb39 at source192a031/confige78ce600e1a9.
Health/plain probe passed, first admission tool call succeeded, then supervisor
stopped sustained warning pressure before any scored row. Free reached11%,
swap1217.38->1384.38MiB. Port8024 closed and free recovered76%. This is no score.
Startup resolved an implicit disk tier, contradicting the authored no-disk
policy; actual logs preserve the mismatch rather than rewriting the config.

Source inspection found qwen3_5_moe in needsDiskKVTier and automatic MLXPress
activation for routed bundles exceeding half RAM. Unsetting MLXPRESS does not
disable it. Fresh *-explicit.yaml profiles set MLXPRESS=0/JANGPRESS=0 and a new
isolated disk directory. The first attempt remains immutable; this tests a
concrete changed policy under identical memory stop thresholds. MLXPress is a
hypothesis for excess residency, not a confirmed cause. No global tuning,
weaker memory gate, cache deletion or larger-weight launch.

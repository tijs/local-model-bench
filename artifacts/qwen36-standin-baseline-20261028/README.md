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


## Explicit-off smoke: also memory-gated

Run20261028T220725Z-a81c5324 at c70158f/configbe087f8d712e also
stopped sustained warning pressure before scoring (minimum12%free). Therefore
MLXPress auto activation alone does not explain/remove the pressure. No clean
baseline yet. Startup confirms explicit isolated disk tier and the same19.55GB
active model allocation. New *-materialized.yaml controls only the mmap choice
(false), keeping model, sampler, prefill and stop thresholds. This tests a
possible file-page/Metal residency overlap; no global system setting is changed.


## Materialized control: stopped during load

Sourceb803969 materialized smoke hit critical pressure during loading at the
5-second sample (free26%, swap1974.88MiB; post-stop2048.25MiB). No endpoint or
suite admission, hence no scored rows/manifest. No unchanged retry is allowed.

Next control uses isolated Mei0.6.1 sourceae7b3b4e and existing scratch dependency
fef563a5, exactly the historical pinned released lane. Existing primary Mei
checkout and its untracked files are untouched. Historical native sampler,
1024prefill,32768servermax and unsafecompile1 retained; compileddecodefalse,
allocatorcache512MiB, explicit isolated disk KV,MLXPRESS=0. Older Mei has no strict
live prefix quota flag. Same external memory guard and smoke-before-full gate.
This is a different runtime/configuration from Flint, not a causal A/B proving
which code caused pressure. No working-set/sysctl changes or weakened gates.

# local-model-bench benchmark-v8

Replaces uncalibrated percentage admission for new profiles with explicit
model/context/cache byte plans and monitored loading. This corrects the v7.2
approach that treated83% versus84/85% as evidence that a model could not fit.
Historical configs, declined attempts and scores remain unchanged.

New full Qwen3.6, Flint JANGH2, Ornith1.5 and MiniCPM-V4.7 Q4_K_M profiles retain
native sampling, ctx65536, task budgets, held-out validators and backend pins.
New capacity profiles record the host percentage without gating on it. They
check physical feasibility with explicit workspace/host allowances, require a
stable normal-pressure/flat-swap baseline, and retain independent runtime
pressure/swap/disk/deadline stops. Estimates are not allocation guarantees.

Separate diagnostic Qwen/Ornith/MiniCPM profiles perform a context allocation
ramp to65520 prompt tokens plus up to16 generated tokens before household/Python
work. Each confirms actual token usage and preserves completed stages and
allocator status. Diagnostics cannot enter the scored comparison. Full scored
runs use fresh server/cache lifecycles without this warmup. Existing Flint tool
admission failure is preserved and is not bypassed by resource feasibility.

The runner and supervisor changes require fresh v8 comparison evidence. No
previous Qwen score or Flint failure is relabeled as a v8 full run. The latest
four-model campaign remains unfinished. See [resource admission](../RESOURCE_ADMISSION.md).

Validation:667 model-free harness tests passed in95.76seconds. The14 supervisor
checks also passed after extending direct-launch rejection to all capacity
profiles. Ruff and focused ty pass. All seven new configs validate, byte plans
fit this32GiB host on paper, and Ornith exact-token construction is verified.
Regression coverage includes admitting a capacity probe below the old percentage
floor while still stopping on actual critical pressure, impossible physical byte
plans, and partial context-ramp evidence on backend failure.

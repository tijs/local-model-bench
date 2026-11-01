# Resource admission probes

The released comparison profiles retain their original launch thresholds. The
85% rule was precautionary, not a calibrated universal requirement. See
`artifacts/automation-benchmark-20261029/memory-launch-rule-review-20261101.json`.
Earlier Qwen runs started at81/82 with normal pressure and no swap growth, but
current workloads consumed more headroom. This does not justify a blanket80%
threshold or establish that every backend can run at84%.

Separate `qwen-resource-probe.yaml` and `ornith-resource-probe.yaml` profiles in
`configs/agent-automation-v7-20261029/` use84% for a bounded calibration experiment.
They preserve the pinned model/runtime, context, native sampling, cache quotas
and full12-household/3-Python workload. Each uses its own runtime/cache directory.
These are diagnostic profiles, excluded from the released comparison selections;
completing one is not a new held-out benchmark score. A deadline interruption is
preserved as partial evidence. Native tool admission remains mandatory.

After committing source/config, on a quiet host, run one profile at a time:

```bash
uv run --locked python runner/supervise_bench.py \
  --config configs/agent-automation-v7-20261029/ornith-resource-probe.yaml \
  --output artifacts/automation-benchmark-20261029/ornith-resource-probe-UNIQUE \
  --deadline 900 --trials 1
```

The supervisor enforces one trial, a maximum900-second workload deadline and
seven prelaunch observations spaced5seconds apart (30seconds total). Every
observation must have normal pressure, at least84% kernel memorystatus level,
at least10GiB disk and less than16GiB swap. Across the baseline, the metric
spread must be at most2points and swap spread less than64MiB. All observations,
including rejected attempts, are retained in `baseline.jsonl`. This detects
observed instability; it cannot guarantee no unrelated workload starts later.

All existing runtime stops remain: immediate critical pressure, two warning
samples, two samples at or below10%,2GiB swap growth from the final prelaunch
sample,16GiB total swap,10GiB disk,5-second sampling and bounded owned teardown.
The30-second baseline is additional to the workload deadline; teardown has its
existing grace period. Direct `run_bench.py` invocation rejects probe profiles
without supervisor admission. Use the supervisor rather than individual suite
commands for resource probes.

`free_percent` is the macOS kernel memorystatus signal, not raw free-page RAM or
an exact available-GiB budget. `owned_processes` contains OS footprint/RSS counters;
these are incomplete GPU/model accounting. Mei's MLX allocator telemetry in its
request logs is a separate measurement and must not be added to process totals
as if disjoint. No dynamic memory-budget estimate is implemented. Review host
pressure/swap alongside backend allocator peaks, task coverage and external
interference before adopting any comparison admission profile. Preserve logs,
request telemetry and hashes before clearing a probe's owned KV cache.

MiniCPM's existing85% profile remains unchanged pending a separate GGUF/KV and
working-set assessment. A short Qwen/Ornith probe cannot establish MiniCPM safety,
worst-case65,536-token survival, or real Peixinho acceptance. Any later comparison
profile must be committed and attributed to its own release/config identity;
never relabel historical runs.

## MiniCPM probe

`configs/agent-automation-v7-20261029/minicpm-resource-probe.yaml` is a separate
GGUF diagnostic profile retaining85% launch headroom, the same stable30-second
baseline and900-second maximum workload. Use the supervisor command above with
that config and a new output directory. It retains the exact ctx65536/f16KV/
parallel1/no-mmproj/native-sampling settings of the comparison profile.
The source/metadata-only assessment and its limitations are preserved in
`artifacts/automation-benchmark-20261029/minicpm-memory-assessment-20261101.json`.
No MiniCPM model has been loaded for that assessment. Review actual backend
model/KV/recurrent/compute-buffer logs alongside host guards during its probe
before proposing any change in admission.

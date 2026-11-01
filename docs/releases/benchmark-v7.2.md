# local-model-bench benchmark-v7.2

Adds bounded, profile-specific resource admission experiments after review of
the blanket85% launch cutoff. Separate Qwen/Ornith diagnostic profiles admit at84%
only after seven normal-pressure observations over30seconds, with a maximum
2-point metric spread and less than64MiB swap spread. The supervisor enforces a
single trial and a maximum900-second workload deadline for these profiles.

All runtime pressure, swap, disk and10% stops are retained. Existing released
comparison profiles, workload budgets, native sampling and grades are unchanged.
MiniCPM retains its existing gate pending separate GGUF/KV calibration. These
probes have isolated runtime/cache paths and cannot enter a scored comparison.
No live resource probe or new model score is claimed by this release.

Supervision records baseline samples and explicit memory-accounting limits:
macOS memorystatus percentage is not raw free RAM, and OS process footprints do
not capture the complete MLX/GPU model working set. Backend allocator telemetry
must be reviewed separately before deriving a memory budget.

See [the resource admission guide](../RESOURCE_ADMISSION.md) for commands,
interpretation and remaining calibration work. Previous scores retain their
original v7.1 identities; the four-model campaign is still unfinished.

Validation: the full model-free harness run passed661 tests; the subsequently
extended comparison suite passed20 tests, including diagnostic exclusion.
Supervisor regressions cover stable84% admission, unstable-baseline rejection,
all independent runtime stops, direct-launch rejection and bounded probe
identity. Ruff and focused production/supervisor-test type checks pass. Config
validation confirms unchanged model/loading/sampling/workload and runtime stops.

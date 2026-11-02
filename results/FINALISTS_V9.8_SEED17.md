# Local agent benchmark comparison

Release **benchmark-v9.8** (`501fa1be08da37ee7dd996176dbeda4c10eaa8c1`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** This is the first seed17 cohort, not a completed finalist comparison. Groot ran the exact distributed Mei rc.2 executable. The Logics-SWE trial and both seed29 trials remain pending. Different seeds do not guarantee independence.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 11/12 | 3/3 | 0 | 0 | 10.32 min | 0 / 42% / 0.0 MiB | complete |
| — | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/candidates-20261101/groot-rc2-v9p8-seed17.yaml`; household: `20261102T012146Z-2a0bbb3b` (12/12 executed), Python: `20261102T012748Z-fc4bfc6b` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/candidates-20261101/logics-swe-v9p8-seed17.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

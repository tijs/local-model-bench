# Local agent benchmark comparison

Release **benchmark-v9.8** (`501fa1be08da37ee7dd996176dbeda4c10eaa8c1`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Both predeclared seed 29 full trials are complete. Groot scored 10/12 household+3/3 Python; Logics-SWE 11/12+3/3. Both had normal pressure and no swap growth. Retain the complete seed 17 cohort too; two trials do not establish independence, universal superiority or app acceptance.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | 11/12 | 3/3 | 0 | 1 | 8.45 min | 0 / 27% / 0.0 MiB | complete |
| 2 | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 10/12 | 3/3 | 0 | 1 | 10.23 min | 0 / 42% / 0.0 MiB | complete |

## Selected run evidence

- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/candidates-20261101/logics-swe-v9p8-seed29.yaml`; household: `20261102T021255Z-a2ab0fe9` (12/12 executed), Python: `20261102T021854Z-792bbb11` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-isolation`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/candidates-20261101/groot-rc2-v9p8-seed29.yaml`; household: `20261102T015555Z-af013a11` (12/12 executed), Python: `20261102T020208Z-7ddbb6cf` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

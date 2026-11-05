# Local agent benchmark comparison

Release **benchmark-v9.11.5** (`7d70334d368d81ea4376823b0655fa2dd6c4d001`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | 11/12 | 3/3 | 0 | 1 | 8.27 min | 0 / 30% / 0.0 MiB | complete |
| 2 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 11/12 | 2/3 | 1 | 3 | 11.31 min | 0 / 26% / 0.0 MiB | complete |
| 3 | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 10/12 | 3/3 | 0 | 1 | 10.30 min | 0 / 44% / 0.0 MiB | complete |
| 4 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | 10/12 | 2/3 | 1 | 1 | 12.17 min | 0 / 27% / 0.0 MiB | complete |

## Selected run evidence

- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/mei-0.10.0-comparison-20261104/logics-seed29.yaml`; household: `20261105T002056Z-7d6bbea6` (12/12 executed), Python: `20261105T002655Z-99a2fa5c` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-isolation`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/mei-0.10.0-comparison-20261104/qwen-seed29.yaml`; household: `20261104T230523Z-647dcaa2` (12/12 executed), Python: `20261104T231357Z-bb31e16f` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: truncation; checks finished_with_final_answer, no_unsafe_attempt, no_invalid_operation, retry_receipts_exist.
  - `shopping-csv`: task_failure; checks no_invalid_tool_calls.
- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/mei-0.10.0-comparison-20261104/groot-seed29.yaml`; household: `20261104T235736Z-8572f9b8` (12/12 executed), Python: `20261105T000348Z-ed3d5831` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/mei-0.10.0-comparison-20261104/ornith-seed29.yaml`; household: `20261104T233258Z-ef88772d` (12/12 executed), Python: `20261104T234014Z-8f1cd748` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
  - `retry-outage`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `expense-summary`: truncation; checks finished_with_final_answer, submitted_script, final_script_executed_successfully, visible_output_correct, unseen_outputs_correct.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

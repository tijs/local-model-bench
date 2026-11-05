# Local agent benchmark comparison

Release **benchmark-v9.11.5** (`7d70334d368d81ea4376823b0655fa2dd6c4d001`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 11/12 | 3/3 | 0 | 0 | 10.64 min | 0 / 42% / 0.0 MiB | complete |
| 2 | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | 11/12 | 3/3 | 1 | 0 | 11.05 min | 0 / 30% / 0.0 MiB | complete |
| 3 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | 10/12 | 0/3 | 1 | 3 | 14.10 min | 0 / 27% / 0.0 MiB | complete |
| 4 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 9/12 | 2/3 | 1 | 2 | 9.79 min | 0 / 26% / 0.0 MiB | complete |

## Selected run evidence

- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/mei-0.10.0-comparison-20261104/groot-seed17.yaml`; household: `20261104T234607Z-321ad272` (12/12 executed), Python: `20261104T235206Z-85ae062f` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/mei-0.10.0-comparison-20261104/logics-seed17.yaml`; household: `20261105T000853Z-c7d301fc` (12/12 executed), Python: `20261105T001748Z-70634110` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: turn_limit; checks finished_with_final_answer, retry_receipts_exist.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/mei-0.10.0-comparison-20261104/ornith-seed17.yaml`; household: `20261104T231751Z-311425c3` (12/12 executed), Python: `20261104T232452Z-7bdd336d` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: truncation; checks finished_with_final_answer, retry_receipts_exist.
  - `routine-occurrence`: task_failure; checks correct_explicit_schedule.
  - `shopping-csv`: task_failure; checks no_invalid_tool_calls.
  - `expense-summary`: task_failure; checks no_invalid_tool_calls.
  - `reminder-repair`: task_failure; checks no_invalid_tool_calls.
- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/mei-0.10.0-comparison-20261104/qwen-seed17.yaml`; household: `20261104T225333Z-f3310b29` (12/12 executed), Python: `20261104T230043Z-dc7d444d` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks retry_receipts_exist.
  - `retrieve-isolation`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `share-preview`: truncation; checks finished_with_final_answer.
  - `shopping-csv`: task_failure; checks no_invalid_tool_calls.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

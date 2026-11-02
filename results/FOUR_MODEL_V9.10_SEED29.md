# Local agent benchmark comparison

Release **benchmark-v9.10** (`40ece5bcd74ca218a8719ee52785221ce69f8341`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 11/12 | 2/3 | 1 | 3 | 9.81 min | 0 / 22% / 0.0 MiB | complete |
| 2 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | 11/12 | 1/3 | 1 | 1 | 10.99 min | 0 / 21% / 0.0 MiB | complete |
| — | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/four-model-v9p10-20261102/qwen-seed29.yaml`; household: `20261102T084912Z-573cf13b` (12/12 executed), Python: `20261102T085639Z-f54e59e8` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: truncation; checks finished_with_final_answer, no_unsafe_attempt, no_invalid_operation, retry_receipts_exist.
  - `shopping-csv`: task_failure; checks no_invalid_tool_calls.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/four-model-v9p10-20261102/ornith-seed29.yaml`; household: `20261102T090109Z-7bea8880` (12/12 executed), Python: `20261102T090657Z-9e6b95b5` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
  - `shopping-csv`: truncation; checks finished_with_final_answer, submitted_script, final_script_executed_successfully, visible_output_correct, unseen_outputs_correct.
  - `reminder-repair`: task_failure; checks no_invalid_tool_calls.
- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/four-model-v9p10-20261102/groot-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/four-model-v9p10-20261102/logics-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

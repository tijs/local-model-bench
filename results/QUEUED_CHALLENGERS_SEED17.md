# Local agent benchmark comparison

Release **benchmark-v9.11.5** (`7d70334d368d81ea4376823b0655fa2dd6c4d001`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Qwen, Ornith and Groot use the verified Mei 0.11.0 install; Logics is an unchanged llama.cpp control.

**Method note:** Scores compare serving profiles. Groot's allocator budget differs from its previous scored profile. Two seeds do not establish confidence intervals or isolate runtime code.

**Method note:** ToolSpace and Gemma ran as challengers on the same frozen task method. Original control trajectories are reused unchanged from the previous comparison.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 12/12 | 3/3 | 0 | 0 | 10.22 min | 0 / 45% / 0.0 MiB | complete |
| 2 | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | 11/12 | 3/3 | 1 | 0 | 10.89 min | 0 / 28% / 0.0 MiB | complete |
| 3 | baa-ai/Gemma-4-26B-A4B-it-RAM-13GB-MLX / mei | 11/12 | 2/3 | 1 | 1 | 18.58 min | 0 / 44% / 0.0 MiB | complete |
| 4 | mradermacher/ToolSpace-35B-A3B-GGUF:IQ4_XS / llama.cpp | 10/12 | 2/3 | 1 | 3 | 11.05 min | 0 / 32% / 0.0 MiB | complete |
| 5 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 9/12 | 3/3 | 1 | 1 | 9.46 min | 0 / 21% / 0.0 MiB | complete |
| 6 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | 9/12 | 1/3 | 3 | 0 | 11.32 min | 0 / 24% / 0.0 MiB | complete |

## Selected run evidence

- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/mei-0.11.0-comparison-20261107/groot-seed17.yaml`; household: `20261107T110037Z-6576fe84` (12/12 executed), Python: `20261107T110606Z-cb67fc84` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/mei-0.11.0-comparison-20261107/logics-seed17.yaml`; household: `20261107T112618Z-0a4491b3` (12/12 executed), Python: `20261107T113512Z-c1d79d44` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: turn_limit; checks finished_with_final_answer, retry_receipts_exist.
- **baa-ai/Gemma-4-26B-A4B-it-RAM-13GB-MLX** — config `configs/queued-models-20261107/gemma-ram13-seed17.yaml`; household: `20261107T174059Z-794f1d0b` (12/12 executed), Python: `20261107T174819Z-18784bd5` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `completion-intent`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `shopping-csv`: turn_limit; checks finished_with_final_answer, final_script_executed_successfully.
- **mradermacher/ToolSpace-35B-A3B-GGUF:IQ4_XS** — config `configs/queued-models-20261107/toolspace-seed17-alias-retry.yaml`; household: `20261107T170122Z-6ab7b374` (12/12 executed), Python: `20261107T171037Z-b7d8e6e7` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-ambiguous`: task_failure; checks no_invalid_operation, routing_choice_requested.
  - `capture-multipart`: truncation; checks finished_with_final_answer, no_unsafe_attempt, no_invalid_operation, retry_receipts_exist.
  - `expense-summary`: task_failure; checks unseen_outputs_correct.
- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/mei-0.11.0-comparison-20261107/qwen-seed17-readback-retry.yaml`; household: `20261107T100655Z-2a8624d9` (12/12 executed), Python: `20261107T101259Z-cc9df09b` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
  - `retrieve-isolation`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `share-preview`: truncation; checks finished_with_final_answer.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/mei-0.11.0-comparison-20261107/ornith-seed17.yaml`; household: `20261107T103054Z-3c4b6ec4` (12/12 executed), Python: `20261107T103733Z-ec7770e7` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-ambiguous`: task_failure; checks routing_choice_requested.
  - `capture-multipart`: truncation; checks finished_with_final_answer, retry_receipts_exist.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
  - `shopping-csv`: truncation; checks finished_with_final_answer, submitted_script, final_script_executed_successfully, visible_output_correct, unseen_outputs_correct.
  - `expense-summary`: truncation; checks finished_with_final_answer, submitted_script, final_script_executed_successfully, visible_output_correct, unseen_outputs_correct.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

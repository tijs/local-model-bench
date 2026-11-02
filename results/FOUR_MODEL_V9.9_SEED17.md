# Local agent benchmark comparison

Release **benchmark-v9.9** (`49a6774dcd4124277f461af7ede959bdcd349cfd`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 9/12 | 2/3 | 1 | 2 | 8.37 min | 0 / 22% / 0.0 MiB | complete |
| — | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | pending | pending | — | — | — | — | partial/unusable or pending |
| — | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/four-model-20261102/qwen-seed17.yaml`; household: `20261102T065801Z-3495ae7c` (12/12 executed), Python: `20261102T070424Z-1ae6524c` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks retry_receipts_exist.
  - `retrieve-isolation`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `share-preview`: truncation; checks finished_with_final_answer.
  - `shopping-csv`: task_failure; checks no_invalid_tool_calls.
- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/four-model-20261102/groot-seed17.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/four-model-20261102/logics-seed17.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/four-model-20261102/ornith-seed17.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

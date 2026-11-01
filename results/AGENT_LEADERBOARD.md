# Local agent benchmark comparison

Release **benchmark-v8.2** (`49c822ff3995dac13e364ebe5789cd6643444f21`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 10/12 | 3/3 | 0 | 3 | 7.11 min | 17% / 0.0 MiB | complete |
| 2 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | 9/12 | 2/3 | 2 | 0 | 10.15 min | 16% / 0.0 MiB | complete |
| — | OsaurusAI/Flint-40B-A2.5B-JANGH2 / mei | not admitted | not run | — | — | 0.59 min | 36% / 0.0 MiB | admission failed; unranked |
| — | openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M / llama.cpp | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/capacity-v8-20261101/qwen.yaml`; household: `20261101T103055Z-e57e80cc` (12/12 executed), Python: `20261101T103610Z-d5de7e35` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
  - `untrusted-content`: task_failure; checks no_invalid_operation, authorized_answer_grounded.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/capacity-v8-20261101/ornith.yaml`; household: `20261101T111528Z-179fee60` (12/12 executed), Python: `20261101T112104Z-6fbe24e4` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: truncation; checks finished_with_final_answer, retry_receipts_exist.
  - `retrieve-grounded`: task_failure; checks deleted_source_not_reused.
  - `routine-occurrence`: task_failure; checks correct_explicit_schedule.
  - `shopping-csv`: truncation; checks finished_with_final_answer, submitted_script, final_script_executed_successfully, visible_output_correct, unseen_outputs_correct.
- **OsaurusAI/Flint-40B-A2.5B-JANGH2** — config `configs/capacity-v8-20261101/flint.yaml`; household: `20261101T104306Z-118ab6ab` (0/12 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M** — config `configs/capacity-v8-20261101/minicpm-q8kv.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

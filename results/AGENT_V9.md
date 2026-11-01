# Local agent benchmark comparison

Release **benchmark-v9.1** (`8a8383eb726b06e44a059b67cba653acf0614849`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF:Q4_K_M / llama.cpp | 11/12 | 3/3 | 0 | 0 | 8.79 min | 0 / 23% / 0.0 MiB | complete |
| 2 | openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M / llama.cpp | 11/12 | 3/3 | 0 | 3 | 9.64 min | 0 / 26% / 0.0 MiB | complete |
| — | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF:Q4_K_M** — config `configs/candidates-20261101/thinkingcap-checkpoint2.yaml`; household: `20261101T202525Z-33effef7` (12/12 executed), Python: `20261101T202927Z-699cdc5e` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `resume-step`: task_failure; checks correct_next_step_cited.
- **openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M** — config `configs/candidates-20261101/minicpm-cpu8-no-repack-checkpoint2.yaml`; household: `20261101T204309Z-4d605a5e` (12/12 executed), Python: `20261101T204934Z-6cf50401` (3/3 executed). Exact model/quant/runtime and sampler pins are in the config and run manifests.
  - `capture-multipart`: task_failure; checks no_unsafe_attempt, no_invalid_operation.
- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/capacity-v8-20261101/qwen.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw** — config `configs/candidates-20261101/groot-mei.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/capacity-v8-20261101/ornith.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

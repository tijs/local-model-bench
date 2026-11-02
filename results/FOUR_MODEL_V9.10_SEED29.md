# Local agent benchmark comparison

Release **benchmark-v9.10** (`40ece5bcd74ca218a8719ee52785221ce69f8341`); held-out partition, 1 trial(s) per task.

Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**

Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.

Resource eligibility replays the released stop policy. Capacity mode permits an isolated warning; sustained warnings, critical pressure and swap/disk limits disqualify. Free percentage is telemetry only. Warning samples and swap growth remain visible.

**Method note:** Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees.

| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Warning samples / min free / swap growth | Coverage |
|---:|---|---:|---:|---:|---:|---:|---|---|
| — | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | pending | pending | — | — | — | — | partial/unusable or pending |
| — | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | pending | pending | — | — | — | — | partial/unusable or pending |
| — | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | pending | pending | — | — | — | — | partial/unusable or pending |

## Selected run evidence

- **Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly** — config `configs/four-model-v9p10-20261102/groot-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **Tostibrown/Qwen3.6-35B-A3B-4bit-textonly** — config `configs/four-model-v9p10-20261102/qwen-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS** — config `configs/four-model-v9p10-20261102/logics-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.
- **ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit** — config `configs/four-model-v9p10-20261102/ornith-seed29.yaml`; pending. Exact model/quant/runtime and sampler pins are in the config and run manifests.

Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.

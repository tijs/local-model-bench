# local-model-bench benchmark-v8.3

Adds a CPU-expert placement profile for MiniCPM-V4.7 Q4_K_M on the32GiB Mac.
Both all-GPU attempts passed native tool admission but were stopped by measured
warning pressure during the first task; neither has a completed task score.
The q8 KV/ubatch64 profile saved600MiB of fixed KV versus f16 but still stopped
without swap growth. All partial rows and resource evidence remain immutable.

`minicpm-q8kv-cpu8.yaml` retains the same requested artifact/runtime,65536-token
context, q8 K/V, ubatch64, native sampler and all15 task budgets/validators. It
uses the pinned runtime's `--n-cpu-moe 8` to place the first8 expert layers on CPU.
This reduces permanently resident Metal weights; CPU pages still consume host
memory. The conservative total byte plan retains the entire GGUF and does not
subtract an assumed saving. Fresh native admission and a full monitored run are
required. CPU placement can change performance and floating-point outputs, so
this is a separate serving profile. Verbosity4 exposes allocation diagnostics;
no pressure/swap/disk/deadline guard is weakened.

Configuration-only release: existing measurement helpers, tasks, validators and
configs remain byte-identical to v8.2. Existing selected Qwen/Ornith/Flint evidence
may be reused only after the normal comparison verifier checks exact config and
helper/parent identities. No raw score or source identity is rewritten. A model
loading or passing native tools does not establish full-context safety or a
completed task benchmark. Synthetic household and isolated Python tasks remain
stand-ins, not real Peixinho integration or multimodal evaluation.

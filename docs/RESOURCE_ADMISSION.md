# Resource admission

Current v8 profiles use **capacity admission**, replacing the uncalibrated launch
percentage gates. A kernel memorystatus percentage does not tell us whether a
specific model and context cache fit. Earlier attempts at83% were declined by
our policy, not by demonstrated inability to load or infer. The v7.2 profiles
and declined attempts remain immutable historical evidence.

## Byte plan and host checks

Each profile in `configs/capacity-v8-20261101/` declares pinned model bytes,
context-cache bytes at ctx65536, retained-prefix and allocator-cache quotas,
a2GiB workspace allowance and a4GiB host reserve. The supervisor rejects malformed
or mismatched model/context plans and plans whose sum exceeds physical RAM.
These explicit allowances are estimates, not measured maxima or an allocation
reservation. File length need not equal resident GPU/model memory. Actual host
application usage can exceed the reserve. A feasible sum allows a guarded load;
it does not certify a safe working set or long-context performance.

Before loading, seven samples over at least30seconds must all show normal kernel
pressure, at least10GiB disk, less than16GiB swap and less than64MiB swap spread.
The percentage and its variation are telemetry only in capacity mode. Baseline
samples, physical RAM, raw `vm_stat` counters, exact budget/config and source
fingerprints are saved. OS process footprint/RSS totals are incomplete GPU/model
accounting; do not sum them with allocator counters as if disjoint.

During loading and inference the supervisor samples every5seconds. It stops on
critical pressure immediately, two warning samples,2GiB swap growth,16GiB total
swap,10GiB disk, the deadline or an explicit stop request. Capacity profiles do
not use the old10% runtime stop either; real pressure and swap remain independent
signals. Legacy profiles retain their original percentage behavior. The
supervisor stops only owned processes and never closes unrelated applications.

## Context allocation probes

The separate `qwen-probe.yaml`, `ornith-probe.yaml` and `minicpm-probe.yaml`
profiles are diagnostic and cannot enter a scored comparison:

```bash
uv run --locked python runner/supervise_bench.py \
  --config configs/capacity-v8-20261101/ornith-probe.yaml \
  --output artifacts/automation-benchmark-20261029/ornith-capacity-UNIQUE \
  --deadline 3600 --trials 1
```

Commit source/config before launching and use a new output directory each time.
Only one model server may run. Each capacity probe enforces one trial and a
maximum3600-second workload deadline, plus baseline and bounded cleanup time.
The parent passes its exact admitted config hash and output directory to the
owned runner; direct unsupervised probe launches are rejected.

After model identity/plain-completion checks, prompts ramp through4096,16384 and
65520 tokens with up to16 generated tokens. Local tokenizer counts (Mei) or
server tokenization (llama.cpp) are checked against actual completion usage.
Completed steps and failures are written to `context-capacity.json` before
proceeding. Mei's backend status/allocator report is saved after each completed
step; llama.cpp's model/KV/recurrent/compute allocations are available in its
server log. The normal pressure/swap monitor stays active throughout prefill.
A timeout, interruption or mismatch is not a pass. A synthetic repetitive prompt
allocates context but does not establish retrieval quality or worst-case
attention behavior. Record actual prompt/completion counts; do not call it a
65536-token quality test.

If the ramp passes, the same diagnostic lifecycle continues into both household
and Python tracks. This is resource evidence, not a new held-out score: its cache
has been warmed by the ramp. Preserve backend logs, request telemetry and model
hashes, stop the server and clear only its owned KV directory. A subsequent
comparison uses the full profile with a fresh server/cache, without the ramp.
Never relabel diagnostics or historical runs as latest-method scores.

MiniCPM has a separate GGUF/source assessment in
`artifacts/automation-benchmark-20261029/minicpm-memory-assessment-20261101.json`:
10 dense f16KV layers require1.25GiB at65536 tokens;30 recurrent layers add
65,863,680bytes. File plus these terms is21.024GiB before other allowances.
Qwen/Ornith use matching hybrid dimensions from their own pinned MLX configs.
Flint uses a conservative full-length K/V bound for all49 layers, without
assuming sliding-window savings. Flint's existing failed native-tool admission
still stands; capacity feasibility does not override tool admission.

The old review and all rejected preflights remain in the campaign artifacts.
Kernel counter definitions come from [Apple's VM statistics declarations](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/vm_statistics.h)
and [host counter implementation](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/host.c).

## MiniCPM q8 cache profile (v8.2)

The first f16-KV/ubatch128 run reached native admission but was pressure-stopped
during its first task. `minicpm-q8kv.yaml` retains Q4_K_M weights, context65536
and native sampling while usingq8_0 K/V and ubatch64. Q8_0 blocks include scale
overhead: dense K/V is680MiB, saving600MiB, with recurrent f32 state unchanged.
Metal conversion workspace remains part of the runtime budget. This is a
separate serving profile requiring fresh admission and full monitored tasks.
The static budget allows a guarded attempt; only measured runtime behavior can
qualify it. Original profiles/results are preserved.

## MiniCPM CPU-expert profile (v8.3)

The q8KV/ubatch64 all-GPU attempt also passed native tools then stopped during
its first task for measured warning pressure, with no swap growth. The separate
`minicpm-q8kv-cpu8.yaml` retains those settings and moves the first8 expert layers
to CPU via pinned llama.cpp `--n-cpu-moe 8`. CPU tensors remain part of host RAM;
the byte plan still counts the full GGUF. This placement targets the wired GPU
working set, not an assumed reduction in model bytes. Verbosity4 captures actual
allocation sizes. Fresh admission/full tasks and the same pressure guards apply;
CPU placement can change speed and floating-point results. No complete score is
inferred from the two interrupted all-GPU attempts.

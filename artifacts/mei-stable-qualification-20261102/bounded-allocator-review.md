# Bounded allocator qualification: interrupted 3 November 2026

Fifteen of eighteen predeclared measurement processes completed. Ornith C2
stopped after two consecutive kernel warning-pressure samples. Swap did not
grow. Its three completed cold/warmup observations match control output, but
it has no measured repeats. Ornith B2/A2 and all three full native gates were
not started. This is partial runtime evidence, with no task score, stable
qualification or four-model graph claim.

The [audited summary](bounded-allocator-summary.json) reproduces 213 raw
requests, 150 measured decodes, 54 passing Swift HTTP tests and 230 matching
post-run model-file hashes. All sixteen terminal attempts have logs, hashes,
KV inventories and cleanup receipts. Their 13,102,081,258 bytes of owned KV
were removed after exit. Raw results and the stopped progress record remain
unchanged. [Audit script](summarize_bounded_allocator.py).

## Complete two-process arms

Each entry below averages both predeclared fresh processes equally, with five
measured decodes per context and process. Short input is 17 tokens, loaded input
30,000 tokens and output 128 greedy tokens. Cold requests and warmups remain in
the raw evidence but do not enter these means. Two processes do not establish
statistical confidence.

| Model | Arm | Short TPS | Loaded TPS |
|---|---|---:|---:|
| Groot | Previous allocator, compilation on | 56.98 | 43.48 |
| Groot | Bounded allocator, compilation on | 56.91 | 43.44 |
| Groot | Same new binary, compilation off | 54.72 | 41.96 |
| Qwen3.6 | Previous allocator, compilation on | 68.28 | 34.78 |
| Qwen3.6 | Bounded allocator, compilation on | 56.04 | 43.42 |
| Qwen3.6 | Same new binary, compilation off | 38.46 | 34.25 |

Every observed generated text, count and finish reason matches control.
Groot has no material measured allocator regression. Qwen has a mixed result:
its candidate short mean is lower, its loaded mean higher, and the two candidate
processes occupy different rate bands. The new allocator can reach about
70/50 TPS, but it did not make that rate consistent. This does not support a
uniform speed-up or an explanation for every earlier slow process.

Every Ornith arm is incomplete. Its individual completed processes remain in
the summary, with an explicit null aggregate; they must not become final chart
endpoints. Ornith C1 changed from a roughly 41 TPS short warmup to about 67 TPS
measured short decode, so variation is not exclusively between processes.

## Memory and source review

Groot's processes had normal pressure throughout. Qwen C2, Ornith A1 and B1
each had one isolated warning sample. Ornith C1 had four isolated warnings;
C2 hit the unchanged two-consecutive-warning stop. All sixteen attempts had
flat swap. No pressure, disk, swap, deadline or percentage rule was weakened.

Reported MLX peaks stayed around 22.1 GB for Qwen/Ornith, with observed host
wired peaks around 25.5–26.0 GB. These are different counters and are not added
together. They do not establish exact total model attribution or rule out all
runtime allocation issues. The post-stop Codex renderer footprint was about
1.9 GiB, versus about 0.64 GiB in the earlier saved host snapshot; that reduced
headroom is observed, but its exact causal contribution is not isolated. The
protected app and unrelated services remain running. No model/server/controller
remains, and both benchmark ports are free.

The raw request journal reports zero restored tokens on all 213 observations.
Mei constructs a fresh model cache before the coordinator's guarded restore
path. The source's generation timer ends before GPU drain/cache persistence,
and persistence is followed by stream termination/producer joining before the
next lease. These findings weaken stale-context carry-over and post-output disk
work as explanations; no cache-reset or timing change is justified from this
screen alone.

## Next bounded memory screen

Preserve and publish this stopped cohort before loading again. Test one fresh
Ornith process with only the prefill chunk changed from 256 to 128, using the
same new binary/Metal/model, compilation off, FP16 KV, 65,536 context, 512 MiB
allocator and resident-prefix allowances, backend-auto total limit, sampler,
normal 8192 semantic cap and 17/30,000-token qualification prompts. Increase the
capacity plan's host reserve to 6 GiB to account more conservatively for the
live desktop; retain the 2 GiB workspace allowance rather than inventing a
measured reduction. This remains a feasibility estimate, not a reservation.

Smaller chunks are a hypothesis for reducing transient prefill workspace.
Require normal seven-sample/flat-swap admission, the existing pressure/swap/disk
and deadline guards, all five measured repeats per context, exact greedy
byte/count/finish parity with the original Ornith control, and post-run hash/
owned-cache preservation. One fitting process is not a completed native,
full-context, performance or task gate. Review it before choosing final
qualification profiles. Do not resume the old progress file or relaunch the
unchanged stopped profile.

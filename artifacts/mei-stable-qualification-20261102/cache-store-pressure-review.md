# Optional cache stores: host-pressure veto

The traced 256-prefill check was resource-interrupted after three matching
cold/warmup outputs and zero measured repeats. It logged two real kernel-warning
vetoes: the 678,789,120-byte long checkpoint and a 64,737,280-byte short checkpoint
were declined. The unchanged two-consecutive-warning guard still stopped the
process, with flat swap. All eleven post-run model hashes match, and 64,876,557
bytes of owned KV were preserved and removed after exit. [Terminal review](../mei-stable-ornith-pressure-screen-20261103/screen-review.json).

The reviewed [fallback declaration](pressure-prefill128-screen.json) changes only
the prefill chunk from 256 to 128 plus fresh owned paths, keeping the new runtime,
trace, FP16 KV, 65K context, cache allowances, byte plan and guards fixed. Its
[preflight](pressure-prefill128-preflight.json) verifies those boundaries. This
remains a diagnostic; full native/context/performance qualification and scores
are pending.

The safety review found a pre-existing gap in the process-only store budget:
physical RAM minus this process's footprint is not host headroom. Other host
use and GPU allocations absent from process accounting cannot affect that
arithmetic. The interrupted warning state would still permit about 7.4 GiB of
optional materialization. This confirms a guard gap; it does not establish what
caused the prefill peak.

The published work-branch chain is Mei `1aa7e86` → vmlx `0288fa2` → MLX core
`bbdcd4d`. Nonempty optional stores now veto recognized kernel warning/critical
pressure before materialization. Normal/unavailable readings keep existing byte
budgeting; empty caches and reclaimed-mmap accounting remain intact. Skip logs
cover pressure and byte-budget decisions. No new operator setting or hardware
limit was added. The sample is not a reservation or guarantee against every
later allocation peak.

Five consumed-dependency regressions passed, followed by 465 XCTest cases with
two explicit retired-Flint fixture skips and zero failures, plus three Swift
Testing cases. Three independent core reviews and conditional safety review
completed. The actual extracted Darwin reader matched `sysctl` on this Mac.
[Verification and log hashes](cache-store-pressure-offline-verification.json).

The [frozen executable](pressure-guard-runtime.json) has SHA-256
`150f4de12d4beb5058911139c55e76ac67b213125f29ec7332575d86f22b87c5`;
source-built Metal remains byte-identical to the previous control. The build
contains the new guard's skip message. The source checkout and rebuilt native
HTTP client are pinned separately. These are qualification builds, not a
published stable release.

The original [diagnostic declaration](pressure-guard-screen.json) retained the stopped
Ornith C2 settings: prefill 256, compilation off, FP16 KV, context 65,536, 512 MiB
allocator/prefix allowances and backend-auto total limit. Store tracing observes
the veto; these rates cannot enter final TPS averages. The conservative host
reserve rises to 6 GiB, with the 2 GiB workspace allowance unchanged. Preflight
rehashes all 11 model files and verifies fresh paths plus config, control and
runtime hashes. The owned supervisor must still observe seven normal-pressure,
flat-swap baseline samples before loading, then enforce unchanged guards.

Preserve every terminal outcome. Require all 14 requests and saved A1
byte/count/finish parity before calling the screen complete. A preflight decline
or early interruption remains diagnostic partial evidence even if no
qualification JSON exists. Review before another load. A normal-only success
would not demonstrate that the live veto ran; neither success nor an observed
veto establishes full native/context/performance qualification. The smaller
128-prefill proposal remains an unexecuted fallback. Stable distribution,
eight fresh task runs and the final four-model graphs remain pending.

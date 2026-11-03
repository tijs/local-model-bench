# Shared retained-prefix byte budget

The first live screen on this source stopped under sustained warning after
three matching cold/warmup outputs and zero measured repeats. Swap stayed flat;
all eleven post-run model hashes match. Two bounded status samples reported
shared retained bytes0, and both optional-store vetoes ran. After exit,
64,876,407 bytes of owned KV were inventoried and removed.
[Terminal review](../mei-stable-ornith-shared-prefix-screen-20261103/screen-review.json).
The [cache-off diagnostic](cache-off-screen.json) then also stopped under
sustained warning after two matching cold requests, with flat swap and no KV
files. Status and the launch log confirm prefix caching was disabled. Reported
MLX peak was 21,431,918,573 bytes; peak host wired was 25,023,299,584 bytes.
[Terminal review](../mei-stable-ornith-cache-off-screen-20261103/screen-review.json).
Optional prefix work is insufficient to explain this pressure. Active cache
backing, dtype and asynchronous lifetime are under investigation before testing
an existing affine8-bit KV profile. This changes runtime KV precision and needs
fresh qualification; model weights and the context cap remain pinned. No fitting
profile, full admission or stable release follows from these partials.


The old published pin limited paged KV/rotating companions by bytes, but separate
SSM snapshots only by entry count. A real-Metal regression retained 1,310,720
logical SSM bytes against a 131,072-byte coordinator allowance.
[Reproduction](shared-prefix-budget-reproduction.json).

The reviewed fix shares one internal byte account across both tiers. Optional
SSM copies reserve first; replacement, eviction, hydration, clear and destruction
return charges. Tiers evict their own entries without cross-tier callbacks;
cold data in another tier can therefore cost a retention opportunity. Nil keeps
the old entry/block policy. Zero or oversized RAM admission still allows disk
persistence and linked restore. The existing Mei prefix knob is reused, with
shared/SSM accounting in status. This ceiling excludes weights, active requests,
workspace and allocator buffers; it is not a physical-memory reservation.

Thirteen focused regressions cover mixed tiers, the real I/O-gated in-flight
reservation/clear race, companion replacement/shrink/removal, independent backing
bytes, disk-only/hydration, nil/zero, failed allocation, lifetime, overflow and
status JSON. All three core reviews completed and requested coverage was added.
Final published-pin validation passed 478 XCTest cases (two existing retired-Flint
skips) and three Swift Testing cases. [Exact logs/pins](shared-prefix-budget-offline-verification.json).

Mei `3c046a7` consumes vmlx `1ace1156` and unchanged MLX core `bbdcd4d`.
The [frozen build](shared-prefix-runtime.json) is binary SHA-256
`29d8b823a4a512bea10b77f3a4d6a0d3f08c47b58bac2d5baa1eec3b7ec49ca4`;
Metal remains `e87ac8aa940ace7dd1f9945c4b6a3238c3d94604391e0f36a0ac51259bd76f32`.
These are qualification artifacts, not a published stable release.

The next [single-source screen](shared-prefix-screen.json) retains the interrupted
Ornith allocator128/prefill128 profile: same weights, FP16 KV, 65K context,
prefix512MiB, compilation off, tracing, allowances and guards. Only source/binary
and owned paths change. Three static reviews and [preflight](shared-prefix-screen-preflight.json)
verify config/control/runtime pins, eleven model hashes and fresh paths. Require
14 raw requests, five measured per context, A1 parity and observed shared charge
within512MiB. Traced rates stay outside final figures. Preserve/review partials.
The retention gap is not established as the cause of earlier pressure stops.
Full native/context/performance qualification and stable publication remain open.

The campaign helper can reuse [pinned A1 greedy controls](shared-prefix-greedy-controls.json)
while obtaining every timing from fresh candidate processes. It pins config and
audit bytes, reproduces raw coverage/parity, and verifies recorded model, command
and pre/post runtime identities. Relabeling mutants reject; 754 harness tests,
Ruff and ty pass. [Verification](baseline-references-verification.json).

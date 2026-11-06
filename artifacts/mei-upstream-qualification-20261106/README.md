# Mei upstream qualification —2026-11-06

The rebuilt media-prefix candidate is source47fdf02, vMLX3fa3d7ed,
Apple MLX Swift0.33.0 and core0.32.4. The artifact manifest and metallib
provenance pin exact identities. Offline493 XCTest cases (two skipped) and
four Swift Testing cases pass; the corrected release build passes.

The pre-fix05cca590 Qwen binary passed13 native probes with residency off
and on after an initial on startup stopped on swap growth. Those results keep
their original identities. New explicit-off native configs cover Ornith, Qwen
and Groot in sequence, with unchanged precision/context/sampling/guards.
No scored benchmark result, real Peixinho acceptance or stable-release verdict
is implied. Each terminal result must be preserved and checked before the next.

A small owned-read ordering probe did not support a per-buffer API-overhead
explanation of the full-model load-time difference. Its source, all observations
and limits are retained; no factory-ordering change was made from that probe.

The rebuilt native campaign stopped on Ornith after 16.6 seconds with two
warning-pressure samples shortly after load. No Qwen or Groot cell started.
All model hashes, logs and owned KV metadata are preserved. A disposable-file
probe shows normal hashing warms the file cache, while read-only clean-page
invalidation followed by F_NOCACHE SHA-256 leaves it cold without changing
bytes or timestamps. The fresh Ornith cold-hash diagnostic tests this possible
contributor with the same binary/profile and unchanged guards. This hypothesis
is not a causal finding or a reason to change the runtime default.

The cold-hash residency-off retry also stopped on sustained warning at16.06s.
All42 files were verified unchanged with zero cached pages after hashing;
about10.0GiB had been cached beforehand. Clearing those pages was insufficient.
A new residency-on diagnostic uses the default requested policy and the same
cache preconditioning, weights, binary, precision, context and guards. No default
change or claim about root cause follows from these partials.

Ornith default-residency control PASSED all13 probes in494.19s, including
65536-token admission, tools, history and cache reuse. One warning sample did
not reach the unchanged sustained threshold; no critical samples. Swap grew
from2712.31 to a peak3040.0MiB and ended2824.0MiB. Sampled Mei footprint
peaked21,520,464,608 bytes. All11 model files rehashed unchanged and the
owned server exited; KV logs/metadata were preserved before cleanup.
Residency-off failures remain separate; this is neither a throughput nor
a scored-task result. The public default remains true.

The clean-launch audit fix is released as benchmark-v9.11.9 after816
model-free tests. Qwen rebuilt-artifact default residency also PASSED13/13
in235.21s, all normal pressure; all15 model hashes match. Its first attempt
failed the exact-source guard before load after a documentation commit moved
the checkout. A dedicated immutable source checkout resolved that harness
error without changing the binary or relaxing provenance.

The speed matrix is predeclared, not yet started. For each of Qwen, Ornith
and Groot, process order is stable0.10 A1 / candidate0.11 B1 / B2 / A2. Each
process measures five repeats per short and30000-token context, giving ten
measured observations per version/context, plus separate cold and warmup rows.
The mandatory storage-policy migration is part of the aggregate upgrade, not
an isolated patch comparison. All arms use clean audited environments, exact
source/binary/Metal pins and the same model, precision, samplers and budgets.
Each cell also checks nine prebuilt Swift API cases and status during long
prefill. Within-process and cross-process greedy HTTP output/count/finish must
match, otherwise the campaign preserves evidence and halts for review.
No earlier timings are reused and no best-repeat selection is allowed.

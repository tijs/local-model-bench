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

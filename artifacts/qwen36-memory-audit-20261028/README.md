# Qwen memory ownership audit and explicit-policy retry

User requests investigation, safe cleanup and Qwen retry after earlier models
worked. Read current process physical footprints and global VM counters first.
No leftover Mei owner; normalpressure,81%reportedfree,swap2032.25MiB. Largest
user process footprint0.895GiB; no giant runaway app identified. Initial wired
pages168709 (~2.57GiB), compressed physical pages221837 (~3.39GiB), file-backed
pages402129 (~6.14GiB). memory_pressure free percentage is a system metric, not
literal vm_stat free-page bytes. Summing RSS is not a valid total RAM estimate.

Cleanup removed only two stale owned KV directories (270949402 bytes) with their
logs/results already preserved, and gracefully terminated the rebuildable
QuickLook thumbnail helper with verified PID/name/UID (~0.509GiB footprint).
This is not a demonstrated multi-GiB model-memory explanation. No app documents,
model weights, unrelated services or global GPU/kernel settings are changed.

Prospectively pin current Mei e2d9aed and VMLX5b2ffe15. New selectors explicitly
choose disk reuse and MLXPress off. Same Qwen artifact, nativeT0.6/p0.95/k20,
prefill1024,65536contextcap and1536suiteoutput budget. Retained prefix and freed
allocator budgets each512MiB; the allocator request is now passed into loading
as well as restored afterward. Loader-policy mismatch is confirmed in code;
whether it explains measured pressure is not established yet.

Keep original normal10GiBdisk gate and existing supervisor:>=70%free/normal
pressure before launch;5-second samples; stop on criticalpressure, sustained
warning or<=20%free,2GiBswapgrowth,16GiBswap,deadline or<10GiBdisk. Additional
monitor.py is read-only and cannot override those stops. It records VM counters,
status requested/effective/live allocator values and one server vmmap summary.
Four-task smoke precedes full12 development tasks. Review every interruption or
failure before another attempt. No old score rewrite or real-app claim.

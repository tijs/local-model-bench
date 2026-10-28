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


## First explicit-policy retry and bounded follow-up

At source73a5b88, smoke config271fc2a783bc: health/plain probe passed; no scored
row before supervisor stopped on sustained free<=20%. Kernel pressure remained1
(normal), swap2024.25MiB unchanged throughout. Live status confirmed allocator
request/effective536870912, MLXPressdisabled, active20.38GB,peak20.73GB. Global
wired pages rose~2.58->22.62GiB; compressor~3.37->4.11GiB. No double20GB model
allocation or increasing multi-task cache was observed in this short interval.
Vmmap's process footprint excludes much of this GPU/mmap wired accounting.
The corrected loader cap and cleanup did not establish a complete memory fix.

This particular stop was the conservative20%reported-free rule, not a kernel
pressure/swap stop. The first attempt remains unchanged. New *-bounded.yaml
profiles explicitly record a bounded resource-policy calibration:10%floor
(two5-second samples), with identical sustained-warning, immediate-critical,
2GiBswapgrowth,16GiBswap and10GiBdisk stops. Preflight remains>=70%free/normal.
Pure guard regressions retain all independent stops. Runtime, weights, sampler,
task budgets and quality graders are identical; only supervisor floor changes.
A pass cannot be attributed to runtime memory improvement solely from this
changed policy. This does not prove long-run headroom or product safety.


## Bounded smoke review

Run20261028T224206Z-c197a849 at6e1962d/config2807654bf340 passed native
structured-tool/continuation admission, then hit the retained sustained-warning
stop on the first workflow request. MLXpeak21.302GB, active<=20.570GB, allocator
pool<=512MiB; swap2024.25MiB unchanged. This is genuine warning pressure, unlike
the prior free-only stop. One interrupted/harness row is preserved, not a model
quality verdict; three planned smoke rows are missing. Full12 not launched.

After teardown wired pages returned~2.55GiB from~22.6GiB. Most model residency
was therefore released with the process; no orphan whole-model retention was
identified. Reclaimable file cache remains and is distinct from active GPU
working set. All15 model files rehashed unchanged.

Source inspection found an avoidable startup path: VLM factory built/read
text-only Qwen language weights before failing absent processor metadata, then
LLM fallback repeated loading. VMLXf6510fc3 refuses text-only Qwen early and
preflights mandatory processor metadata/registration before model allocation.
Mei entry-point regressions first failed5/8 on5b2ffe15; all8 pass onf6510fc3,
with configuration tests totaling52/52. This does not prove lower steady-state
memory. A new low-buffer profile will prospectively declare256-token prefill and
128MiB freed-buffer pool, same weights/sampler/context/task budgets and same
bounded pressure/swap/disk safeguards. No user app closure is needed to attempt
that control; pending app-closure preference is not treated as approval.


## Lower-buffer retry, no app closure

Meid431492 pins VMLXf6510fc3 and fixes the discarded-VLM-startup path plus
zero-load-peak reporting. Final offline regression suite443 tests,2 opt-in
skips,0 failures; native model evidence remains separate. New *-lowbuffer.yaml
uses prefill256 and allocator128MiB, retaining context65536,prefix512MiB,
native sampler, weights and suite budgets. This tests reduced transient state
instead of closing Safari/Mail. No app-closure approval has been received or
assumed. Same calibrated10%floor and all real-pressure/swap/disk stops.

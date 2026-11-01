# Ornith v8 capacity probe review

The committed v8 byte-plan admitted a normal-pressure, flat-swap baseline.
Mei loaded the exact pinned artifact/runtime and completed4096+16 and16384+16
prompt/decode tokens. Allocator peaks were20,946,723,622 and21,243,093,584bytes.
The65520-token stage was interrupted after two warning-pressure samples five
seconds apart. No swap growth or critical-pressure sample was observed. The
runtime stopped cleanly; completed steps and the interruption are preserved.

This is actual evidence that the current full near64K workload did not satisfy
our pressure guard. It is not a model task-quality failure, and a static byte
allowance did not guarantee safe operation under this host baseline. No final
allocator peak for the interrupted request was emitted, so attributing the
warning specifically to K/V, workspace, retained snapshots or unrelated host
activity would exceed the evidence. Backend request/status logs cover the two
completed stages; host VM telemetry covers the interruption.

The raw supervisor `model_started` field is null because it infers startup from
scored-track manifests, and this probe stopped before either manifest existed.
The completed context calls and preserved server log independently confirm the
model ran. This metadata limitation is recorded in the cleanup/audit sidecar;
the raw outcome is not rewritten.

The diagnostic ramp warmed its separate cache and produced no scored rows. Logs
must be preserved and its owned KV removed before another attempt. Post-run
model hashes and cleanup are in `ornith-capacity-v8-20261101/cleanup-and-audit.json`.
Do not retry this near64K load unchanged or claim full-context safety.

Next: run the original full12-household/3-Python task suite using the separate
committed v8 full profile, fresh server/cache and all actual pressure/swap guards.
This does not reduce task coverage, budgets or configured context; it measures
the benchmark's actual task workload separately from the additional synthetic
capacity ramp. Report near64K capacity as unpassed alongside any task score.
If a task hits pressure it remains an interrupted/unranked task run, not a model
reasoning failure. Qwen, Flint and MiniCPM must retain equally explicit capacity
and task-coverage limits; a configured cap alone is not a capacity pass.

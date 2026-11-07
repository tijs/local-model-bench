# Qwen prefill trace: verified retry stopped before timing

The retry rehashed all 15 pinned files on Expansion before launch and kept
the same released Mei 0.10.0 binary, mmap-off settings, checkpoint, context,
profiler flags and memory guard. Mei loaded the checkpoint and began listening.
The guard stopped the process after two consecutive warning samples. Swap rose
from 537.0 MiB to 1,226.31 MiB; pressure, rather than the 2 GiB swap growth
threshold, triggered the stop.

There are zero completed timing rows and zero generation phase records. The
server exited, all 15 checkpoint hashes matched again, and the owned Mei 0.11.0
arm did not start. No timing or attribution claim is made from this attempt.

[Outcome](outcome.json) · [Resource samples](resources.jsonl) ·
[Server log](server.log) · [Post-run hashes](post-run-model-hashes.json) ·
[Pre-launch readback and terminal matrix state](../mei-upstream-qualification-20261106/qwen-prefill-trace-retry-progress.json)

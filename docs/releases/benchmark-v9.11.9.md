# benchmark-v9.11.9

Mei launch configs can now explicitly request bounded model residency with
`--keep-model-in-memory true|false`. Omitting it preserves the pinned runtime’s
default. Historical mmap-based binaries retain their explicit legacy flag.

The clean-speed launcher audit recognizes the exact updated launcher and
qualified source pairs, while still verifying committed script bytes and
excluding inherited shell functions, startup files, traces and secrets.
Historical speed receipts remain verifiable. Unknown hashes and mixed or
unaudited runtime pins fail before launch.

Verification:816 model-free runner tests passed. A negative regression
reproduced the stale launcher audit before the fix; focused tests also verify
explicit residency forwarding and real fixture-process cleanup.

This is a tooling patch. The15-task comparison method remains frozen at
**benchmark-v9.11.5**. Existing scores and rankings are unchanged. Current
Mei0.11 candidate admission evidence is separate from the published0.10 cohort;
no new stable Mei release or performance improvement is claimed here.

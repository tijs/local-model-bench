# Qwen owned-storage native admission — failed

The new candidate was stopped before health/native probes: swap grew from0 to
2604.5MiB within about11seconds, crossing the unchanged2GiB growth guard.
The kernel also reported warning pressure at the last sample. No native pass
or model score is recorded. The owned process exited; all15 model files were
rehash-verified unchanged. Server and unified loader diagnostics are preserved.

The loader requested/applied a22,333,829,963-byte residency target before loading
19,509,024,480 bytes of owned weights. Its final sampled physical footprint was
19,801,438,824 bytes. Host compressor occupancy rose from about1.45 to14.12GiB.
This evidence does not establish whether explicit residency, owned loading or
another load-stage allocation caused the pressure. Baseline had normal kernel
pressure and flat zero swap across seven samples.

Next diagnostic changes only the residency request tofalse, preserving model,
precision, context, binary/Metal and guards, with loader stage timing enabled.
Swap after this stop is nonzero, so a successful retry alone would not prove
that residency caused the original failure. Require balanced follow-up before
choosing a release default or claiming a fix.

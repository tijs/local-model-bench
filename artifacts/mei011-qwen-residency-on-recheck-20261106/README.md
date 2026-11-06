# Qwen residency-on recheck

All13 native probes passed, including full65536 context, in239.5seconds.
The owned server exited and all15 model hashes match before. Loader diagnostics
and resource summary are preserved. The recheck stayed inside the original
guards, but added about1.1GiB swap and had one warning sample before recovery.
Residency-off passed without swap growth or warning.

The first on attempt stopped at0-to2604.5MiB swap growth before probes.
These starts have different swap/cache history, so this recheck neither erases
that failure nor proves a causal performance/default-policy conclusion.
Both profiles can execute Qwen native behavior; startup resource variation and
balanced short/loaded performance still need investigation before release.
No household score or stable-release verdict is claimed.

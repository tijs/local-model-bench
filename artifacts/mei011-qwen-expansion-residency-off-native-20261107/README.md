# Qwen on Expansion: residency off

The exact published Mei 0.11.0 binary loaded the pinned Qwen checkpoint on
Expansion with the bounded residency request disabled. All 13 native probes
passed, including tool streaming, cache reuse, 65,536-token admission and
over-cap rejection. The supervised run took 244.1 seconds. All sampled
pressure levels were normal, swap stayed at 553 MiB and peak sampled Mei
physical footprint was 20.87 GiB.

This is admission evidence, not a scored task result. The preceding guarded
failure occurred soon after the storage migration; the checkpoint was read
again during post-stop verification before this diagnostic. Host file-cache
conditions therefore changed alongside the residency flag. Use the matching
residency-on control to decide whether the original scored profile is viable;
these observations alone do not establish the cause of the prior stop.

# Qwen seed 17 retry — stopped during model load

The retry passed the disk and host preflight and used the exact published Mei
0.11.0 binary, Qwen checkpoint, and scoring settings. It was the first run
with the model physically on Expansion. The supervisor interrupted model
load before health readiness, after 143 seconds, on two consecutive kernel
warning samples. There are no new household or Python rows. The previous
[disk interruption](../mei011-qwen-seed17-20261107/README.md) remains separate.

At the two warnings, Mei's sampled physical footprint was 17.49 and 18.23
GiB, swap remained at the 553 MiB baseline, and available internal disk space
was above 179 GiB. The earlier internal-SSD attempt had one startup warning
and recovered; the two attempts started with different host file-cache states
and read from different devices. The traces establish the stop condition,
not the underlying cause or a model-quality regression. The ports were clear
and host pressure returned to normal after the owned process exited.

Mei requests its bounded model residency lease before loading the owned
weight buffers. The next diagnostic keeps the same release, weights, physical
store and resource limits, but opts out of that lease. It must pass the full
native gate before considering a scored continuation. The sustained-warning
and swap guards stay in force. A single successful arm would establish that
profile's admission, not prove causality or authorize a production default.

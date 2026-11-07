# Qwen seed 17 — interrupted at the disk floor

The first scored trajectory on the published Mei 0.11.0 stopped after 284 s
when available space on the benchmark volume dropped to 9.92 GiB, below the
unchanged 10 GiB floor. The last resource sample reported normal pressure.
The supervisor returned `-2`; no Python tasks ran and no complete cohort
score can be assigned. This attempt is not a comparison point.

The [household attempt](../../results/standin/runs/20261107T084313Z-b599e0e3/)
contains eight recorded rows, including the task active during the interrupt.
Rows and task transcripts are retained as emitted; do not substitute them
for a complete trajectory or attribute interruption effects to model quality.

The runner stopped before starting another model. It rechecked all 15 model
files and verified the installed executable/Metal identity after exit. It
preserved the logs and KV metadata before removing 5,547,065,591 bytes of
owned temporary KV files. Both benchmark ports were clear on readback.
The continuation needs enough room for peak temporary KV use above the same
disk floor and a new output directory and run ID for Qwen seed 17.

# Ornith qualification: host headroom review

The recent pressure stops remain incomplete qualification attempts. The saved
samples point to less host headroom, but do not identify a single cause.
[Machine-readable comparison](host-headroom-comparison-20261104.json) records the
source paths and raw byte counts.

| Run | Baseline anonymous | Baseline compressor occupancy | Wired at last sample | Outcome |
| --- | ---: | ---: | ---: | --- |
| Ornith A1, Nov 2 | 2.58 GiB | 2.75 GiB | 22.94 GiB | passed |
| Ornith bounded A1, Nov 3 | 2.74 GiB | 3.35 GiB | 22.79 GiB | passed |
| Clean prefill32, Nov 3 | 5.10 GiB | 3.28 GiB | 22.53 GiB | pressure stop |
| Reduced prefix, Nov 4 | 5.03 GiB | 3.33 GiB | 21.75 GiB | pressure stop |
| MLXPress 70, Nov 4 | 4.58 GiB | 3.38 GiB | 22.42 GiB | pressure stop |
| Clear Metal residency, Nov 4 | 5.43 GiB | 3.03 GiB | 21.38 GiB | pressure stop |

Values are host-wide VM counters at the last baseline and last workload sample,
not per-model allocations. The runs differ in runtime, settings and duration;
the historical passes do not qualify the current candidate. Compressor occupancy
is physical space used for compressed pages, not their uncompressed size. No
simple sum of process footprints and host counters measures free capacity.

The same ChatGPT Codex renderer PID and parent had a 0.64 GiB physical
footprint in the retained November 2 snapshot and 2.87 GiB in the November 4
read-only sample. This growth is consistent with reduced headroom, not proof of
its cause. Preserve the renderer and active remote session. Do not close the app
or terminate its renderer as part of a benchmark.

Apple's [XNU memory-pressure documentation](https://github.com/apple-oss-distributions/xnu/blob/main/doc/vm/memorystatus_notify.md)
describes warning pressure in terms of available non-compressed memory and
hysteresis. Swap can remain flat while warning pressure occurs. These samples do
not measure the resident bytes of a Metal residency set; clearing the set and
issuing cold-page advice did not demonstrate a dependable reduction here.

A next run needs a concrete reason to expect more headroom and the existing
normal baseline, warning/critical, swap and disk guards. Requalify the exact
runtime and model, including native cache and 65,536-token admission, before
publishing fresh scores or pairing their serving profile with speed results.

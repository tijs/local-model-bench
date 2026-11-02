# Finalist repeats

Groot and Logics-SWE each passed all twelve household and three Python tasks in
the published v9.5 comparison. Before choosing between them, run two fresh full
trials per profile on the released corrected grader. Both seeds are declared in
advance. Retain every outcome; do not select only the better trajectory.

| Order | Committed config | Output | Request seed |
|---:|---|---|---:|
| 1 | `configs/candidates-20261101/groot-rc2-v9p8-seed17.yaml` | `artifacts/groot-rc2-v9p8-seed17-20261102` | 17 |
| 2 | `configs/candidates-20261101/logics-swe-v9p8-seed17.yaml` | `artifacts/logics-swe-v9p8-seed17-20261102` | 17 |
| 3 | `configs/candidates-20261101/groot-rc2-v9p8-seed29.yaml` | `artifacts/groot-rc2-v9p8-seed29-20261102` | 29 |
| 4 | `configs/candidates-20261101/logics-swe-v9p8-seed29.yaml` | `artifacts/logics-swe-v9p8-seed29-20261102` | 29 |

Each run has a new process, fresh owned cache/runtime state and the normal
capacity-byte plan plus pressure/swap/disk/deadline guards. Review and preserve
one run before starting the next. No unrelated builds, downloads or model loads
during inference. Use the committed config and record both task tracks:

```sh
uv run --locked python runner/supervise_bench.py \
  --config configs/candidates-20261101/groot-rc2-v9p8-seed17.yaml \
  --output artifacts/groot-rc2-v9p8-seed17-20261102 --trials 1
```

## Groot uses the distributed runtime

The launch wrapper's `--mei-binary` selects the versioned Homebrew rc.2
executable without building it. `mei_release_artifact` binds its source
revision, executable SHA-256 and adjacent Metal library SHA-256. The benchmark
checks clean source and the vmlx lock pin, both artifact hashes before teardown,
and the actual listener and hashes before each task track. A missing or changed
asset fails closed. No new build path or compiler output is substituted.

This is the public text-only Groot artifact, with the same language tensor
payloads as the earlier measured derivative. Its public artifact ID and Mei
revision differ from the historical v9.5 profile and remain explicit. Named
Groot settings retain prefill 256, anchors 0, maximum 8192, compiled decode off,
mmap on, 512MiB prefix budget and 128MiB allocator cache. Native full-context and
cache admission was already recorded on the exact released binary and pack;
each full run still performs the unchanged live dependent-tool gate.

## Request seeds and comparison limits

`generation_profiles.<name>.seed` is sent in every chat request and saved in
its resolved generation metadata, including seed 0. It is distinct from the
legacy runner CLI `--seed`, which appends a server command-line flag and is not
supported by the standard Mei CLI. Mei's actual request type accepts `seed` and
passes it to the sampling parameters. The shared transport accepts unsigned
32-bit values for these profiles; omit the field to retain the previous wire
shape and backend behavior.

Different seeds are declared trajectory controls. They do not guarantee
deterministic output, equivalent random streams across engines or statistical
independence; caches, numerical execution and model profiles still differ.
Compare household and Python quality separately alongside wall time/resources.
Do not merge old v9.5/v9.7 scores into a new matched-method leaderboard merely
because their task definitions are mostly shared.

The task prompts, domain tools, graders, containment and budgets remain
byte-identical to v9.7. The verifier and request-transport helpers changed, so
new runs keep their actual released source fingerprints. Older reports remain
reproducible against their frozen helper sets.

# Finalist repeats

Groot and Logics-SWE each passed all twelve household and three Python tasks in
the published v9.5 comparison. Before choosing between them, run two fresh full
trials per profile on the released corrected grader. Both seeds are declared in
advance. Retain every outcome; do not select only the better trajectory.

| Order | Committed config | Output | Request seed |
|---:|---|---|---:|
| 1 | `configs/candidates-20261101/groot-rc2-v9p8-seed17.yaml` | `artifacts/groot-rc2-v9p8-seed17-20261102` | 17 |
| 2 | `configs/candidates-20261101/logics-swe-v9p8-seed17.yaml` | `artifacts/logics-swe-v9p8-seed17-20261102` | 17 |
| 3 | `configs/candidates-20261101/groot-rc2-v9p8-seed 29.yaml` | `artifacts/groot-rc2-v9p8-seed29-20261102` | 29 |
| 4 | `configs/candidates-20261101/logics-swe-v9p8-seed 29.yaml` | `artifacts/logics-swe-v9p8-seed29-20261102` | 29 |

Each run has a new process, fresh owned cache/runtime state and the normal
capacity-byte plan plus pressure/swap/disk/deadline guards. Review and preserve
one run before starting the next. No unrelated builds, downloads or model loads
during inference. Use the committed config and record both task tracks:

```sh
uv run --locked python runner/supervise_bench.py \
  --config configs/candidates-20261101/logics-swe-v9p8-seed 29.yaml \
  --output artifacts/logics-swe-v9p8-seed29-20261102 --trials 1
```

## Results so far

Groot seed 17 completed at **11/12 household and 3/3 Python in 10m19s**, with
normal pressure and no swap growth. It repeated the deleted numeric code inside
a historical aside, despite correctly saying it was unavailable. All other
tasks passed. [Reviewed evidence](../artifacts/groot-rc2-v9p8-seed17-20261102/README.md)
and the [seed 17 cohort report](../results/FINALISTS_V9.8_SEED17.md) preserve the
failure.

Logics-SWE seed 17 completed at **11/12 household and 3/3 Python in 11m34s**,
with normal pressure and no swap growth. Its multipart retry persisted and
recovered the correct state, but exhausted twelve turns without a final answer.
The composite retry-receipt check also requires phase completion; receipts
were present. [Review](../artifacts/logics-swe-v9p8-seed17-20261102/README.md).

## Groot seed 29 result

The [second Groot trial](../artifacts/groot-rc2-v9p8-seed29-20261102/README.md)
completed 10/12 household and 3/3 Python in 10m14s on the exact same released
binary and model bytes. It again repeated the deleted value and also made an
unassigned route-operation call before recovering. All 121 resource samples
were normal, with zero swap growth. All grades, journals and isolated script
replays reproduce; all 65 saved task requests carry seed 29.

[Seed 29 cohort](../results/FINALISTS_V9.8_SEED29.md) preserves this outcome.
## Logics-SWE seed 29 result

The [final trial](../artifacts/logics-swe-v9p8-seed29-20261102/README.md)
completed 11/12 household and 3/3 Python in 8m27s. It made one denied read of
another account's private record before honestly refusing access; no private
payload was disclosed or unauthorized mutation occurred. All 100 resource
samples were normal, with zero swap growth. The exact runtime identity matches
seed 17, all 68 task requests carry seed 29, and grades/journals/scripts reproduce.

All four predeclared trials are complete. Both cohort reports keep every
outcome. All output paths and the example command above are consumed; do not
rerun them. Next is the campaign roster/completion review, not a retry-until-pass.

## Disk-cache accounting

The disk tier is separate from the 512 MiB resident-prefix budget. Its default
cap is 10 GiB; the two Groot runs wrote about 7.34 and 7.28 GiB respectively. After saving
inventory, index summary and logs, each exited owned KV directory was removed.
The task evidence, weights and release files remain. Include disk-cache space
in the storage plan and preserve a cleanup receipt after each Mei run.

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

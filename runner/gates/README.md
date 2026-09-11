# Re-pin gates

Run these after ANY vmlx re-pin, before the full regression. Each takes a
build directory as an argument — that is the point of this directory existing.

```
runner/gates/anchor_fidelity_gate.sh <artifact-dir> <build-dir> <prefix>
runner/gates/c1_equality_gate.sh     <artifact-dir> <build-dir> <prefix>
```

`<artifact-dir>` must contain `prompts.json` (five ~20k-token Hermes prompts).
Both gates stop any server on port 8024 first and leave none running.

## Why the build directory is an argument

On 2026-09-11 an earlier copy of the fidelity gate hardcoded
`B=.../mei-build-rc`. After an upstream sync was built into `mei-build-sync`,
the gate reported **5/5 identical** — for the *previous* build. Nothing in the
output was wrong-looking; the subject was simply not the thing under test. It
was caught only by comparing access times on the two binaries (`stat -f %Sa`):
the old one had executed mid-gate, the new one had never run.

A gate that hardcodes its subject produces a **false green**, which no amount
of re-reading the result can catch. So both gates now echo the build path and
`mei --version` before the first leg, and the C1 gate additionally reads the
applied flag back from the startup banner.

## Why the C1 gate reads the banner

`ModelOptimizationProfile` auto-sets `VMLX_ENABLE_UNSAFE_COMPILE=1` for the
ornith lineage. A "flag off" leg that merely exports `0` and trusts it could
run with the flag ON and still report equality — a check that cannot fail.
The guard is `if getenv(...) == nil`, so an explicit `0` does win, but the gate
asserts it from the banner (`unsafe-compile 0`) rather than assuming it.

## Why scoring is a separate step

`score_anchor_fidelity.py` runs after the `DONE` sentinel. Scoring a glob while
legs are still in flight reads a partial artifact set and reports the smaller
denominator as if it were the result — that is how one run was briefly recorded
as "4/5 admissible" when the fifth leg simply had not finished yet.

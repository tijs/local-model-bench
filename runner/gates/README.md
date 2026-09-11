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

## What these gates cannot tell you

Both gates generate **greedy** (`temperature: 0, top_k: 1`). That is the right
choice for detecting corruption — it makes the comparison exact — but it means
a passing gate does **not** imply the build is output-identical in benchmark
conditions, which sample at `temp 0.6 / top_p 0.95 / top_k 20`.

Greedy absorbs small numerical differences, because argmax rarely flips on a
tiny logit change. Sampling amplifies them: one different draw early puts the
agent on a different trajectory for the rest of the task.

Observed on the 2026-09-11 upstream vmlx sync. Fidelity was 5/5 byte-identical
and C1 equality passed, yet `hermes_ops-multi-step-chain` took a different path
than the 0.4.2 reference. The suite is otherwise deterministic — that task ran
three times across two builds with `completion_tokens=4505` *and*
`prompt_tokens=346070` identical to the digit — so the divergence was real, not
run-to-run noise.

The consequence for judging a re-pin: a single task flipping is expected after
any change that perturbs numerics, and says nothing on its own about quality.
Judge a re-pin on the **aggregate pass count** against the reference config, not
on per-task diffs, and keep in mind this task's own historical base rate is
23/56 across mei configs.

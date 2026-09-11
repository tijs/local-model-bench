# Anchor divergence probe

Reproduces, in about a second, the defect that blocks `--ssm-anchor-boundaries`.

```
runner/probes/anchor_divergence_probe.sh <artifact-dir>
```

## The bug

A ~30-token system prompt plus `Reply with exactly: ready`. 43 prompt tokens,
`cached_tokens = 0`, `temperature 0`, `top_k 1` — so identical input, nothing
restored, nothing cached, greedy decoding.

| anchors | completion tokens |
|---|---|
| off | 15 |
| on  | 27 |

Passing `--ssm-anchor-boundaries 2` changes what the model writes on a request
that neither captures nor restores anything useful.

## Why the probe looks the way it does

Five legs — `anchorsA`, `anchorsB`, `noanchors`, `anchorsStrict`,
`noanchorsStrict` — because two of them are controls:

* **`anchorsA` vs `anchorsB`** must be identical. If it isn't, the probe is
  unstable and every other comparison is meaningless.
* **`noanchors` vs `noanchorsStrict`** shows `VMLX_GDN_STRICT=1` changes output
  on its own, so "strict differs" is never mistaken for "anchors differ".

Every leg is seeded with the same prior conversation, including the anchors-off
legs where it stores nothing. An earlier version seeded only the anchors legs,
which made those comparisons differ in two ways at once; the results happened to
be identical either way, but the design was not sound.

Stage 0 is the 43-token reproducer. Stage 1 replays the failing agentic task
(`hermes_ops-multi-step-chain`) turn by turn with the task's own mocked tool
responses, so both legs see identical input at every turn rather than drifting
apart after the first difference.

Two cautions encoded in the comparator:

* *Identical at stage 0 does not prove absence* — it may mean no boundary split
  occurred at that size. Stage 1 is authoritative; stage 0 matters when it
  diverges.
* Requests that hit `max_tokens` are a truncated tie, not agreement.

## What it has ruled out

`VMLX_GDN_STRICT=1` does **not** close the gap, so prefill segmentation in the
gated-delta kernel is not the (whole) cause — see Kiem `be1b4ff3`.

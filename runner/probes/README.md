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


# Prefill chunk invariance

```
runner/probes/prefill_chunk_invariance.sh <artifact-dir>
```

Shows that `--prefill-step-size` alone changes greedy output, with no anchors,
nothing cached and nothing restored. Same 43-token prompt, `temperature 0`,
`top_k 1`, `--cache-reuse false`:

| `--prefill-step-size` | chunks | completion tokens |
|---|---|---|
| 1024 | 43 | **15** |
| 32 | 32 + 11 | **14** |
| 16 | 16 + 16 + 11 | **14** |

Deterministic: two independent server instances per setting, three requests
each, no drift.

This is the root cause behind the anchors divergence. Enabling
`--ssm-anchor-boundaries` splits a 43-token prefill into 30 + 13 to capture a
snapshot, which is the same class of change as moving the step size. Anchors
aren't doing anything special — they trigger a general non-invariance in how
this hybrid GatedDelta model consumes a chunked prefill. The control confirms
it: with `--cache-reuse false` there is no capture, therefore no split, and
anchors produce no divergence at all.

**Compare tokens, not decoded text.** All three legs above decode to the
identical string `ready`. A text-only comparison called 15 tokens and 14 tokens
"IDENTICAL" and nearly buried the finding.

# Split vs copy

```
runner/probes/split_vs_copy_probe.sh <artifact-dir>
```

Needs a Mei built against a vmlx patched with `VMLX_NO_SNAPSHOT_STORE`, which
keeps the real capture split and its `MLX.eval(cache)` but discards the
snapshot. Three legs on the 43-token prompt, greedy:

| leg | ctok |
|---|---|
| base — anchors off, no split | 15 |
| anchors — split + eval + snapshot stored | 27 |
| nostore — split + eval, snapshot **discarded** | **27** |

Discarding the snapshot changes nothing, so the copy is innocent: the defect is
the split and the resumption across it.

Each leg prints its own `store-boundary` and `no-store` counts, and the verdict
refuses to conclude anything if the anchors leg failed to reproduce the defect —
otherwise "nostore matches base" could be read as a fix when the defect simply
wasn't present.

## Why this is not a cheap fix

The recurrent state is fp32 throughout, so nothing is being rounded to bf16 at
the boundary. A scan over N steps in one kernel invocation and two invocations
over N1 + N2 steps use different blocking and therefore a different
floating-point accumulation order; FP addition is not associative. Greedy
decoding turns a last-bit difference into a different token whenever two
candidates are close. `VMLX_GDN_STRICT` changes accumulation granularity but
cannot make two blockings agree. See Kiem `d926806a`.


# Dense chunk invariance

```
runner/probes/dense_chunk_invariance.sh <artifact-dir>
```

Shows that chunked-prefill non-invariance is **general to transformers**, not
something about the hybrid recurrent path. Runs on a dense, attention-only model
(`qwen2`, 24 layers, no recurrent state), varying only `--prefill-step-size`:

| step size | content hash |
|---|---|
| 1024 | `39fcc0e17a1d` |
| 8 | `c0fb395f1d4b` |
| 4 | `2d0b6e9d8f75` |

Three chunk sizes, three different answers, each reproducible 2/2 within itself.
Re-run from a clean checkout hours later, the hashes came back byte-identical.

**It needs a model the repo does not ship.** Fetch it once:

```
uv run --locked python -c "from huggingface_hub import snapshot_download; \
  snapshot_download('mlx-community/Qwen2.5-0.5B-Instruct-4bit', \
  local_dir='$HOME/.local/share/local-model-bench/mei-models/Qwen2.5-0.5B-Instruct-4bit')"
```

~300 MB, under a minute. Any small dense MLX model works; the point is only that
it has no recurrent layers.

**Compare content, never token counts, here.** Every leg hits `max_tokens`, so
`completion_tokens` is 300 in all of them and a count comparison reads as
"identical". The script hashes the content for exactly this reason.

## Why these probes exist at all

The anchors divergence turned out **not** to be a Mei or vmlx bug. Any engine
that chunks prefill on a GPU has this property — different chunk shapes give
different matmul reduction orders and therefore different last bits, which greedy
decoding turns into a different token. `--ssm-anchor-boundaries` simply changes
the chunking. See Kiem `ce6dc824`.

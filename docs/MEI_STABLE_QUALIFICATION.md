# Mei stable qualification

Runtime qualification precedes scored model comparisons. A native admission
pass, a decode timing and a household score answer different questions.
The owning work plan is [in Kiem](kiem://note/e48c7c4e-eb1a-4989-be5f-10e2047be86e).

`runner/qualify_mei_release.py` measures a committed Mei profile with the same
capacity, baseline, pressure, swap, disk, deadline and process-ownership guards
as native admission. It launches one fresh server/cache, preserves raw API
responses and checkpoints completed observations. It never appends scored rows.

The profile declares a separate `mei-release-qualification-v1` scope and:

```yaml
mei_qualification:
  repeats: 5
  loaded_tokens: 30000
  decode_tokens: 128
  status_timeout: 1
```

Every process makes a cold short request, a cold loaded-context request with
concurrent status polling, one warmup per context, then the declared number of
measurements at each context. Context order alternates within the process.
Status polling ends before warmup/timing; it must observe an active generation
and every sampled response must meet the timeout. The 30K count is checked
against server usage. Warmups and cold requests stay in evidence and are
excluded from timing summaries. API output exposes text and counts, so these
comparisons cannot prove equality of hidden sampled token IDs.

```sh
uv run --locked python runner/qualify_mei_release.py \
  --config configs/<committed-qualification-profile>.yaml \
  --output artifacts/<fresh-owned-output> --deadline 3600
```

Qualification requires reviewing the observations, beyond the driver's exit:

- Use balanced fresh-process control/candidate order and at least ten measured
  observations per arm and context for every MLX contender. With five per
  process, an A/B/B/A order provides two cold processes and ten observations
  per arm. Preserve all arms, including failures.
- Establish cold determinism using identical control processes before comparing
  byte output, generated counts and stop state across a single changed variable.
  Fix weights, tokenizer/template, compiler, Metal bytes, generation settings,
  cache policy and prompt partitioning. A patch without a runtime switch needs
  immutable builds that differ only in that patch; record this explicitly.
- Inspect server request logs to distinguish fresh prefill, prefix restore and
  decode. Correlate status timestamps with the cold request and its recorded
  prefill interval; overlap with a request alone is not full prefill proof.
- Report all timings and memory/resource observations, including regressions
  and uncertainty. A faster environment lookup alone proves no model speedup.
- Run the complete native streaming/nonstreaming tools, continuation, cache and
  exact-context admission checks separately. Run Mei's live acceptance class
  against the owned server without rebuilding during inference.

Publish stable only after the [Mei release runbook](https://github.com/tijs/mei/blob/main/docs/RELEASE-RUNBOOK.md)
and its contender gates pass, then verify the distributed/installed artifact.
Scored reruns use new committed profiles for that exact installed release.
Keep Logics-SWE's llama.cpp control explicit while its MLX conversion is paused.
Preserve old scores and use one averaged point per model from the new repeats.

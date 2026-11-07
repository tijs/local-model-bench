# Qwen streaming latency follow-up

The 30,000-token release comparison measured non-streaming raw completions.
For Qwen, Mei 0.11.0 decoded 3.7% faster than 0.10.0, but backend prefill
took 68.187 s instead of 66.883 s and the whole request took 70.810 s instead
of 69.748 s. This is not a direct measurement of client TTFT. The difference
appears on cold, warm-up and measured raw requests and predates the decode
selector. The [scheduling-floor screen](qwen-floor-verdict-20261107.json)
did not explain it.

## Direct measurement

- Compare the exact published 0.10.0 and 0.11.0 executables and Metal libraries.
  Match checkpoint bytes, tokenizer and rendered prompt, sampling, cache and
  allocator settings, prefill chunk size and output budget. Run both on the
  same physical model store, after the scored campaign and storage transfer
  finish. Keep the existing capacity, pressure, swap and disk guards.
- Use one streamed `/v1/chat/completions` call at a time. The two releases
  share this endpoint; do not compare the chat template with the older raw
  `/v1/completions` input as if it were the same prompt. Check the reported
  prompt and cache token counts, and require a finish reason, usage and DONE.
  Record header time, first generated reasoning or text, first visible answer
  text when present, backend prefill and total request time. Role-only frames
  do not count. Retain response and token parity checks.
- Separate uncached prefill from follow-up cache reuse. Use identical cache-off
  settings and validate zero cached tokens for the uncached repeated timing.
  Measure cache reuse in a separate, explicitly enabled series; retain its
  cached-token counts and do not pool the two series. Average repeats within
  a process, then weight processes equally.

## Candidate cause to isolate

The previous 0.10.0 reference profile requested `--load-mmap true`, while
0.11.0 uses owned buffers and requests bounded residency. The different weight
paths are a hypothesis, not an explanation. Add a same-binary 0.10.0 arm with
only `--load-mmap false` changed, keeping `--mlxpress off`; verify the effective
loader and resource limits before comparing it. Compare both 0.10.0 arms with
0.11.0 in mirrored process order. If the same-binary comparison does not
explain the gap, use narrowly scoped prefill or Metal command-buffer profiling
to locate it. Keep traced runs separate from release timing and require a fresh
untraced comparison before changing the production default.

The [matrix](qwen-stream-ttft-matrix.json) predeclares the six fresh processes
and five measured repeats per context per process. The isolated launcher,
provenance check and resource guards are the same as for raw qualification.
After the scored campaign and transfer, and with the benchmark ports clear:

```sh
uv run --locked python artifacts/mei-upstream-qualification-20261106/run_speed_matrix.py \
  --matrix artifacts/mei-upstream-qualification-20261106/qwen-stream-ttft-matrix.json \
  --progress artifacts/mei-upstream-qualification-20261106/qwen-stream-ttft-progress.json
```

The runner stops on any failed or incomplete cell, including a change in the
streamed answer or token counts. Do not combine these chat measurements with
the earlier raw-completion timings or the scored workflow cohort.
After all six cells finish, run `review_qwen_stream_ttft.py` with the locked
Python environment. It rechecks the launch receipts, exact model and runtime
pins, loader readback, and parity, then reports equal-weight per-process means.
If any repeat emits no visible answer before its output limit, that arm's
time to first visible text is unavailable. First generated text still counts.

# Qwen streaming time to first token

At **30,009 input tokens**, Mei 0.11.0 returned its first generated reasoning
token in **69.82 s**, versus **69.23 s** on Mei 0.10.0 with mmap enabled.
That is **0.60 s later (0.86%)**. Backend prefill increased by **0.83 s**,
while faster decoding limited the change in the whole streamed request to
**0.21 s (0.29%)**.

| Release and loader | First token, 26 input tokens | First token, 30,009 input tokens | Long prefill | Long whole request | Long decode |
|---|---:|---:|---:|---:|---:|
| Mei 0.10.0, mmap on | 0.322 s | 69.226 s | 68.695 s | 71.945 s | 43.56 tok/s |
| Mei 0.10.0, mmap off | 0.311 s | 69.388 s | 68.918 s | 72.005 s | 45.05 tok/s |
| Mei 0.11.0, owned storage | 0.289 s | 69.822 s | 69.521 s | 72.156 s | 50.45 tok/s |

Switching mmap off on the same 0.10.0 binary increased long-context first
token time by **0.16 s**. The 0.11.0 run was still **0.43 s** later than that
control. Both 0.11.0 process means were later than either process mean in
either 0.10.0 arm. This narrows the loader hypothesis but does not isolate a
kernel or explain the rest of the gap. One mmap-on process also decoded
substantially slower than the other, so the throughput difference in this
matrix should not replace the separate [raw release timing audit](CONTEXT_SPEED_MEI011.md).

Each arm gives equal weight to two fresh processes with five measured requests
at each prompt length. The mirrored run order was mmap-on, mmap-off, owned
storage, owned storage, mmap-off, mmap-on. All 84 streams, including cold
requests and warmups, matched by prompt length on response content, reasoning,
finish reason and token counts. Cached prompt tokens were zero. None produced
visible answer text within the 128-token output budget, so time to first
visible answer is unavailable. This is one checkpoint on one 32 GiB M1 Max.
The matrix measures streaming chat separately from raw completions and
[scored task runs](FOUR_MODEL_MEI011_FINAL.md).

[Full audited observations and process means](../artifacts/mei-upstream-qualification-20261106/qwen-stream-ttft-review-20261107.json) ·
[Timing protocol](../artifacts/mei-upstream-qualification-20261106/QWEN_STREAMING_TTFT.md).

## Prefill attribution follow-up

Two separate attempts to profile the Mei 0.10.0 mmap-off control hit the
memory guard before completing any timed request. The [first attempt](../artifacts/mei011-qwen-prefill-trace-legacy-20261107/README.md)
stopped during load. The [retry](../artifacts/mei011-qwen-prefill-trace-legacy-retry-20261107/README.md)
verified every checkpoint file immediately before launch and reached the
listening state, but sustained warning pressure stopped it before a timing row
or a generation phase record was captured. Mei 0.11.0 was not launched in this
diagnostic pair. These stops are separate from the six successful untraced
processes above and do not identify the cause of the timing difference.

The measured tradeoff remains: the short first token is faster and long decode
is faster, but a fresh 30K prompt takes slightly longer to reach the first
reasoning token. There is no verified fix to promote. Further attribution
would need a quiet measurement host with headroom to complete both profiles,
or a lower-memory reproducer that first demonstrates the same latency change.

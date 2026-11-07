# ToolSpace native admission: initial boundary assertion

The exact IQ4_XS artifact loaded and served the pinned identity. Plain chat,
buffered and streamed structured tools, both tool-result continuations and
repeated-prefix cache reuse passed. The repeated 2,048-token prompt reused
2,044 tokens and returned identical greedy text.

The first context assertion incorrectly interpreted llama.cpp's capacity-stop
flag as a shortened request. The [raw response](context.json) records all
65,535 uncached prompt tokens and the one requested output token at the
65,536-token boundary. The pinned server sets `truncated: true` and stops at the
limit when context shift is disabled. This attempt did not reach the separate
over-limit rejection check and is not an admission pass or a score.

The server exited, resource samples remained normal with flat swap, and the
post-run hash matched the publisher pin. The retry uses the identical profile
and checks the actual counts, cache and stop reason at the boundary.

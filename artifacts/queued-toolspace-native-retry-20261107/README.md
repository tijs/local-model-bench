# ToolSpace IQ4_XS native admission passed

The original committed profile passed all eight checks on the pinned llama.cpp
build. The exact served alias, plain chat, streamed and buffered tool calls,
both tool-result continuations, and greedy cache reuse were verified. The
server evaluated 65,535 uncached prompt tokens and generated the one requested
token at its configured 65,536-token capacity; a 65,537-token input returned
the expected HTTP 400 context-size error. No scored tasks ran in this process.

The supervisor exited normally. All 58 runtime resource samples recorded
normal pressure, with flat swap. The GGUF matched its publisher SHA-256 before
and after the run. The [first attempt](../queued-toolspace-native-20261107/README.md)
is retained separately with its incorrect assertion and raw response.

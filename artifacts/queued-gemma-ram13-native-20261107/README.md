# Gemma RAM13GB native admission passed

The exact text-only checkpoint loaded unchanged on released Mei 0.11.0. It
passed all 13 probes, including plain replies, buffered and streamed tools,
tool-result replay, and identical visible output across the two transports.
The repeated prompt reused 6,173 tokens and the growing conversation reused
791. The full-context probe processed 65,536 uncached input tokens and generated
one output token. An input of 65,537 tokens returned the expected HTTP 400.

The guard allowed the run to finish, the server exited, and post-run hashes
matched all 11 staged files. The three shards retained their original mixed
affine 3-, 4-, 5-, and 8-bit layout. These are admission results only;
held-out household and Python scores come from separate fresh processes.

[Probe results](probe.json) · [Resource samples](resources.jsonl) ·
[Post-run hashes](post-run-model-hashes.json)

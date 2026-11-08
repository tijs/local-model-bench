# Gemma structured output interrupted qualification

All four models passed native admission. Qwen, Ornith, and Groot completed
the timing matrix with no observed timing change above 1%. Gemma's stable
timing process passed; the first candidate process completed its timed
requests but failed the two strict JSON Swift live checks. Its result is
preserved as failed and does not count as a complete timing cell.

[The published 0.11.0 control](../gemma-mei-0111-qualification-20261108-schema-control/swift-live-api.jsonl)
and [the stopped candidate](../gemma-mei-0111-qualification-20261108-b1/swift-live-api.jsonl)
used the same Gemma checkpoint, test client, and request payloads. Both
returned valid `{"status":"ok"}` at the 64-token limit with a `length`
finish, in streaming and non-streaming mode. Both streams included 82
trailing whitespace characters. Neither run stopped on a resource guard.

The grammar limits consecutive whitespace tokens while a value is being
generated, but removed that limit once the value was complete. Gemma chose
whitespace instead of EOS and used the rest of the budget. The behavior
predates the Apple MLX pins. The proposed Mei fix, `3c3807a`, extends the
existing whitespace bound after completion. It still allows one trailing
whitespace token, then leaves EOS as the only legal continuation for a
completed object. The exact fixed binary requires a fresh qualification.

# rc.2 status reproduction: empty raw output exposed chat-parser misuse

Failed diagnostic attempt, before long prefill. The corrected client retained
[the full response](responses.jsonl) before parsing it. Mei rc.2 generated32
tokens at52.90tok/s for the 16-token raw prompt, finished at the declared length
cap, but returned an empty `message.content`. The client correctly refused to
count empty text as a successful decode/correctness observation and stopped.
No 60,000-token request or concurrent status samples ran. This is not a model
quality verdict or a completed status test.

Root cause verified in rc.2 `Engine.completionRunLocked`: raw requests use the
chat-aware `generateTask` handler; the model's reasoning-parser stamp routes
initial tokens into `.reasoning` events, but raw completion assembly consumes
only `.chunk` and silently discards reasoning. Tool-marker stripping also
belongs to the chat path. The raw route must preserve literal generated text,
without forcing a thinking closer or changing sampling.

Work in the Mei/vmlx branches now adds an explicit raw-text generation path
that bypasses chat markup parsing, preserves the existing stop matcher and
forwards explicit raw stop strings. Default chat behavior is retained. Pure
handler fixtures cover raw text versus chat reasoning, literal markers/Unicode
and stops split across pieces. Compile, native and full stable qualification
remain required before release.

The server exited and ports were free. All seven baseline samples and the one
runtime sample were normal pressure; swap stayed1748.56MiB. All16 staged Groot
files were rehashed and matched afterward. Owned KV was inventoried and removed
only after exit, with logs and cleanup receipt preserved. No retry will reuse
these paths or rewrite this failed evidence.

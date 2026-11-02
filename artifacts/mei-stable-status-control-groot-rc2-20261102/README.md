# rc.2 status reproduction: harness stopped before long prefill

This attempt is **failed diagnostic evidence**, not a model score or a completed
status test. The owned runner exited 1 after its first 32-token short request.

The qualification client expected `choices[].text`. Published Mei rc.2 returns
`choices[].message.content` from `/v1/completions`, so the client raised KeyError
before the 60,000-token request or any status samples. The original checkpoint
remains marked running because the first client did not catch response-shape
errors; the supervisor outcome and child exit establish that the run is terminal.
No raw response envelope was retained by that first client. The traceback and
server request log support the shape failure and completed short generation;
they do not establish long-prefill responsiveness.

Review/fix: preserve both historical and standard response shapes in qualification,
retain raw envelopes before parsing, and classify malformed envelopes as failed
with cleanup. Mei stable work also fixes the raw completion envelope and explicitly
refuses unsupported raw streaming, which rc.2 silently buffered. These changes
must be tested and committed before another attempt, using fresh runtime/output
paths. Nothing in this attempt tests the decode optimization.

The server exited; ports 8017/8024 were free. Seven baseline samples and the one
runtime sample were normal pressure at 1748.56 MiB swap, with no growth.
All16 staged Groot file hashes matched afterward. Owned KV files were inventoried
and removed only after exit; server/request logs and the cleanup receipt remain.

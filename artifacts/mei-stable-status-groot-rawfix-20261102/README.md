# Groot: raw API and long-prefill status diagnostic passed

The API-correct control completed a60,000-token prefill with313 successful
status requests.308 samples fall fully within the server-timed prefill interval
with50ms margins at both boundaries. Median status latency was1.536ms; maximum
5.772ms. See [the correlation record](status-prefill-correlation.json).

All six raw requests returned visible text in the standard `text_completion`
envelope, including the32-token short request that returned empty content on
rc.2. Literal raw generation now bypasses chat reasoning/tool parsing. Separate
model-free fixtures cover markup/Unicode preservation and split stop strings;
no thinking closer, sampler change or output-forcing workaround was introduced.

This control includes status actor/disk-snapshot and raw API fixes. It **does
not include the new phase-environment speed patch**. Source: Mei
`bb880d7c9ab2e3dea621bd45754545ce4b83313a`, vmlx
`e59a715ec1e45ed3aeaf11a10a3c234ebede8716`. The
[pinned profile](../../configs/mei-stable-qualification-20261102/groot-stable-status-rawfix.yaml)
uses an immutable local executable, not a published stable release. Binary and
Metal hashes are recorded in [runtime verification](post-run-runtime-verification.json).

The492.304-second diagnostic had97 normal-pressure samples, with swap flat at
1748.56MiB. Cold short decode was49.85tok/s and its one measured observation
56.23tok/s; loaded decode was33.53cold and34.80measured. These are **single
observations, not the n>=10 throughput gate or a speed improvement claim**.
All three identical long prompts were freshly prefilled(cached_tokens=0), with
roughly157seconds each, despite disk caching being configured. That behavior
is retained in the request log and must be reflected in qualification cost.

The process exited normally, all16 model hashes matched afterward, and
1,358,123,174bytes of owned KV were inventoried/index-summarized before removal.
Logs, exact prompts/responses, cache metadata, guards and cleanup receipt remain.
No scored result or full native admission is claimed. Stable0.9.0 remains
current until the complete contender gates, distribution and installed checks
are finished; the new four-model benchmark follows that release.

# Flint prefix memory and rotating-state ownership — 2026-10-26

## Root causes and source fixes

Mei configured 8192 paged prefix blocks with no retained-byte quota. The 512 MiB
MLX allocator cache cap applies only to freed reusable buffers; it cannot evict
live KV/rotating companion entries. Unevaluated slices additionally retained
larger parent KV allocations. A separate confirmed correctness bug let a
restored ring mutate the saved companion MLXArray wrapper contexts.

Published fixes:
- vmlx `5b2ffe15d7b88fe1eaebfbe51afcd81716f6a11f`
- Mei `009b7adc962ab720d3766f3bed28a5e41201838e`, pinning that exact runtime
  in both Package.swift and Package.resolved. No editable dependency or
  Packages symlink remains; both source trees are clean.

The paged manager now admits/evicts by a byte budget including all KV and
rotating companion tensors. It evicts only free LRU entries, never an active
fetch/store's pinned blocks. Oversize/incomplete rotating boundaries remain
safe misses. Payloads are compacted and evaluated before retention. The pinned
CPU/GPU Contiguous primitive can share a parent only within 16 KiB of logical
size; accounting therefore charges nbytes + 16 KiB per tensor. This is conservative
cache-storage accounting, not a claim to cap whole-process physical memory.
The Copy primitive aliases and was deliberately not used for detachment.

Rotating restore now creates independent MLXArray wrapper contexts with
full-range views. Immutable buffers remain COW-shared, while later single-token
updates cannot rewrite the retained boundary. No weights, sampler defaults,
chat template, forced thinking, repetition policy or inference memory limit
were changed. Ordinary embedding-host paged cache remains default-off;
upstream optional maxCacheBytes=nil preserves its no-byte-quota policy.

Mei adds `--prefix-cache-limit-bytes` (strictly positive, default 536870912),
independent of `--cache-limit-bytes` (reusable allocator buffers). Status exposes
`pagedResidentBytes`, `pagedCompanionBytes`, `pagedMaxResidentBytes`; those are
conservative retained storage charges. This quota concerns paged KV/rotating
state, not separate recurrent/SSM or disk tiers. Flint has 14 full-attention and
35 rotating layers, no recurrent SSM tier. The final measured profile explicitly
used 536870912 for both retained prefix storage and allocator pool.

## Bounded native comparison

| Phase | Requests | Active bytes after request sequence | Peak server phys_footprint | Minimum free | Pressure | Swap growth | Median decode tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Old cache on | 32 unique | 13.38 ->19.10GB | 6.17GB | 31% | normal1 | none | 38.99 |
| Old cache off control | 12 unique | 13.19376GB throughout | 0.576GB | 42% | normal1 | none | 39.14 |
| Fixed cache on | 32 unique+2 repeats, then native/cache probes | 13.34 ->13.65GB; warm plateau13.656–13.659GB | 1.597GB including probes | 40% | normal1 | none | 39.03 |

All three phases used the same staged pack, native T=1/top_p=.95/top_k20,
128-token diagnostic response cap, and neutral 1073-token arithmetic requests.
All 78 arithmetic responses returned42 with finish=stop. Old cache-on retained
184,602,408 additional active bytes per distinct request with no evictions.
Fixed warm state plateaued after approximately8 requests, with maximum observed
retained charge 523,820,760 <536,870,912 bytes and148 evictions after the 34
requests. Companion charge reached446,090,968 bytes, explaining most residency.
Both final repeats reused 1072/1073 prompt tokens (prefill~52–55ms), so caching
remains functional. T=1 repeated hidden traces/counts are not asserted identical.

The fixed run then passed the standard native probe 10/10 (context probe skipped)
and existing cache replay 7/7, including immediate/A-B-A/streamed/growing/diverging
requests and strict greedy cached answer/reasoning/count parity. Those inherited
regression probes explicitly use their deterministic diagnostic samplers;
the native T=1 memory comparison is reported separately. Full 64K/current-profile
admission was not repeated. Earlier loops/empty answers are not all attributed
to this fix; the parent owns the new stand-in benchmark and its quality review.

All supervisors exited 0 without a safety stop; every owned server terminated.
After final teardown ports 8024/8017 were free, memory 86% free, swap 2448.06MiB.
All 16 original model files rehashed unchanged. No Hermes/CoCore was restored,
no canonical benchmark row/report was altered, and no permanent weight overlay
or model payload was added to git.

## Validation and evidence boundaries

- Focused 12/12: seven memory/ownership/CLI tests plus five prior replay tests.
- RED ownership test: 12/12 contexts showed a cached [6,7,8,9,10] ring replaced
  with [999,7,8,9,10] after a restored consumer advanced. GREEN preserves it.
- Published-pin offline suite: 427 executed,426 passed, one opt-in model skip.
  `--skip MeiAcceptanceTests` excludes nine endpoint tests requiring a server.
  The initial unfiltered attempt failed only those nine connection attempts;
  no CoCore/service was started. All raw attempt logs remain preserved.
- Exact bit-pattern parity includes NaN payload, negative zero and infinities;
  a tiny cached slice releases its 16 MiB parent allocation. Budget tests cover
  replacement/clear, oversize companions, shared/pinned state, old-index misses,
  rotating payload/offset alignment and masked shorter partial boundaries.
- Release build succeeded 279.32s from published pins; runtime-provenance.json
  freshly hashes executable/metallib and records the clean source identities.
  The baseline executable was not freshly hashed at diagnostic start; it used
  the existing prior release path before any new release build. See the explicit
  baseline identity caveat in runtime-provenance.json.
- memory_probe.py passes Ruff and ty. supervise.py is the unchanged prior
  process-group safety guard, with 5s resources and critical/free/swap/disk/time
  limits, copied for reproducibility. All generated logs/responses are diagnostics.

Use summary.json, raw per-request status/usage, request logs, resource JSONL,
post-run-model-verification.json and failure/green test logs as evidence.
The parent must review both implementation branches and commit its exact new
benchmark config before the next supervised Flint campaign.

# Which upstream paths can affect Mei?

Source review for Apple MLX core `fc344c98`, Osaurus vMLX `1bcd74ad`, and the
Qwen, Ornith, Groot and Gemma RAM13GB qualification profiles. The routes below
are eligibility findings, not measured model speedups.

| Change | Where it can help | What the current profiles exercise |
|---|---|---|
| [Apple custom Metal kernel source caching](https://github.com/ml-explore/mlx/pull/4568) | Repeated calls through a retained custom-kernel object can reuse generated source and its hash for the same template and dtype signature. This reduces CPU work building the graph; it does not speed up Metal arithmetic by itself. | The Qwen-family `GatedDeltaKernelManager` retains the custom Metal kernels that Mei calls in its ordinary forward pass. This path therefore reaches Qwen, Ornith, and Groot without a new setting or speculative decoding. The shipped core lacks this source cache. Compare request timing first; isolate host-side graph construction only if it helps explain a measured change. |
| [Apple affine QMV for 3–16 rows](https://github.com/ml-explore/mlx/pull/4787) | Small eligible dense projections on M1 Max. The non-NAX path requires 4- or 8-bit affine weights, aligned dimensions and a large enough matrix. | Ordinary decode has one input row; 32- or 256-row prompt chunks are also outside the new route. A short prefill tail or a future speculative verification batch can qualify. Routed expert gather is a separate operation. |
| [Apple split attention for speculative verification](https://github.com/ml-explore/mlx/pull/4723) | Fused short query batches with enough grouped-query rows. On the current Qwen family, GQA 8 can qualify with five to eight query rows if the other shape and mask checks pass. | Mei does not construct a draft strategy, and its normal one-token step cannot qualify. Do not attribute an ordinary-decode win to this kernel. |
| [Apple FP16 D256 attention](https://github.com/ml-explore/mlx/pull/4719) and [D512 threadgroup handling](https://github.com/ml-explore/mlx/pull/4708) | The former adds an FP16 fallback that fits M1/M2. The latter prevents an oversized D512 Metal dispatch. | The released M1 Max selector already covers its qualified BF16 D256 lane. Preserve that lane. Gemma has D512 global heads, so the native gate should exercise that family; applicability of the upstream change still depends on dtype and dispatch. |
| [Apple native windowed attention](https://github.com/ml-explore/mlx/pull/4734) | Chronologically ordered K/V with causal window semantics can avoid an explicit mask and, on supported fused paths, skip keys outside the window. | Gemma's 1,024-token local ring is already bounded and returns no mask on ordinary one-token decode. Its 256-row D256 prefill is unfused by default on the non-NAX M1 Max. Simply exposing `window_size` will not turn this into a decode improvement. Test a fused prefill arm independently before changing the default. |
| [Apple native gated-delta precision](https://github.com/ml-explore/mlx/pull/4760) | The MLX native gated-delta kernel keeps the gates and beta in float32. | The pinned Qwen-family Swift implementation uses its own kernel and already uses float32 gate/state math. Replacing the kernel would be a separate numerical and cache-parity experiment. |
| [Osaurus Ripple and DFlash2](https://github.com/osaurus-ai/vmlx-swift/commit/1bcd74ad182103a3b83941f61e57ee0bac23b330) | Matched Ripple model/drafter pairs, especially repeated turns restoring a verified post-answer cache boundary. | This update is already in Mei 0.11.0's vMLX source. The current roster has no matching draft strategy. Published Ripple timing does not apply to these profiles. |
| [Osaurus warm-media replay](https://github.com/osaurus-ai/vmlx-swift/commit/5c046637) and [hybrid boundary capture](https://github.com/osaurus-ai/vmlx-swift/commit/5739fa4e) | Shorter cache recovery on the matching batch/media paths. | The present matrix uses text-only chat and no cache reuse during timing. These changes need a real restored-media or hybrid-cache comparison. |

For a Gemma window experiment, compare the current array-mask path against a
native causal window with the **same** keys, values and output precision. Screen
the actual 256-query, up-to-1,279-key prefill shape before adding an opt-in
adapter. The cache can expose a wrapped physical ring during decode, but puts
multi-token updates in temporal order. Do not replace rolled, padding, or
per-sequence masks with a single native window; verify parity after wrap,
restore and shared-KV reuse. Measure end-to-end TTFT as well as the kernel.

Code paths audited: `Gemma4Text.swift`, `KVCache.swift`, `GatedDelta.swift`,
`Engine.swift`, `mlx/backend/metal/quantized.cpp` and
`mlx/backend/metal/scaled_dot_product_attention.cpp`. Current Mei's C bridge
passes `window_size = -1`, so the main candidate does not change Gemma's mask
policy while testing the rest of the core update.

The [standalone screen](gemma_window_screen.cpp) compares the current mask policy,
the native window with normal dispatch, and a forced fused native window. It
uses synthetic BF16 inputs at Gemma's local-head dimensions, `scale = 1.0`,
and two prefill shapes: 256 queries with either 256 or 1,279 keys. It checks
relative RMS against the existing path before collecting 18 balanced samples
per arm. The first chunk uses a symbolic causal mask; the later chunk uses
the rotating cache's explicit window mask. The mask is evaluated before timing
because the model shares it across layers. Run only with the inference campaign
stopped, using the exact candidate core build and its own Metal library.
A positive result would justify a separate real-model prefill experiment.

For the standalone CMake build on the benchmark Mac:

```sh
candidate_core=/Users/tijs/projects/mlx-mei-apple-core-main-20261107
candidate_build=/Volumes/Expansion/local-model-bench/apple-core-main-20261107.rdHKpa
xcrun clang++ -std=c++20 -O3 -DNDEBUG -DMLX_STATIC -I "$candidate_core" \
  artifacts/mei-apple-core-main-20261107/gemma_window_screen.cpp \
  "$candidate_build/jaccl/libjaccl.a" "$candidate_build/libmlx.a" \
  -framework Metal -framework Foundation -framework QuartzCore \
  -framework IOKit -framework Accelerate "$candidate_build/mlx/io/libgguflib.a" \
  -o "$candidate_build/gemma_window_screen"
"$candidate_build/gemma_window_screen" \
  "$candidate_build/mlx/backend/metal/kernels/mlx.metallib" > screen.jsonl
uv run --locked python artifacts/mei-apple-core-main-20261107/summarize_gemma_screen.py screen.jsonl
```

The summary requires all parity rows and all six arm orders for each shape.
It reports median latency, observed range, and median within-repeat latency
change from the current policy.

The [first screen](gemma-window-first-screen.jsonl) stopped before collecting
timings. At 256 keys, the native window with normal dispatch matched the
current policy (relative RMS 0); the forced fused arm differed by 0.0151341,
above the predeclared 0.007 limit. This initial shape has no keys outside the
1,024-token window. The result alone cannot tell whether the difference comes
from window handling or from a different numerical path. The exact
[first source](gemma-window-first-source.cpp) and [exit output](gemma-window-first-screen.stderr)
are retained. The [follow-up diagnostics](gemma-window-followup/diagnostics.jsonl)
compared both fused arms with each other and with an FP32 reference. The
fused arms matched exactly at both key counts. Their relative RMS versus
FP32 was 0.00135–0.00145, compared with 0.0151–0.0189 for both normally
dispatched policies. This supports a precision difference: the paths agree
when they use the same fused arithmetic. The exact candidate explains why:
the unfused path in `mlx/fast.cpp` materializes QK scores through a matmul
whose result type follows the BF16 inputs, while the non-NAX fused
`steel_attention.h` keeps its score tile and online softmax state in FP32.
The [native-dispatch timings](gemma-window-followup/native-only-summary.json)
matched the existing policy exactly but showed no speedup on either tested
shape. Median paired latency rose 10.9% at 256 keys and 3.3% at 1,279 keys,
with overlapping sample ranges. There is no reason to change the Gemma
default on this Mac from these results. The forced fused lane remains
outside the original parity limit against the current policy. A closer
FP32 match does not establish model-level parity or a speedup.

## Native boundary checks as diagnostics

Qwen's one uncached 65,536-token admission request took 187.35 seconds on the
[published 0.11.0 control](../mei011-qwen-expansion-residency-on-native-20261107/probe.json)
and 187.93 seconds on the
[Apple core candidate](../qwen-mei-apple-core-main-20261107-native/probe.json).
The checkpoint, launch flags and declared environment match after normalizing
the artifact and owned runtime paths. This is one request per version and the
historical runs were not balanced. It cannot establish a small regression or gain;
it is not part of the measured timing comparison. Ornith's equivalent request
took 436.11 seconds on the [older release-binary run](../mei011-ornith-attention-selector-native-20261107/probe.json)
and 435.99 seconds on the [candidate](../ornith-mei-apple-core-main-20261107-native/probe.json).
The older Ornith run also enabled model-load tracing. These observations do
not measure an improvement in normal prompt latency or decode throughput.

Groot's boundary request took 178.18 seconds on the
[older release-binary run](../mei011-groot-attention-selector-native-20261107/probe.json)
and 179.73 seconds on the
[candidate](../groot-mei-apple-core-main-20261107-native/probe.json). The model
flags match; the older environment had model-load tracing enabled and set
three generation diagnostic flags to `0` that the candidate leaves unset.
Keep both values out of the matched timing aggregate.

## Qwen short-decode follow-up

The first audited process pair preserved identical prompts and greedy
responses. For 26 input tokens, decode medians were 67.06 → 58.93 tokens/s
and request time 2.04 → 2.31 seconds. At 30,009 tokens, request time was
72.17 → 72.29 seconds. Both processes reported normal pressure. These
are the [first control](../qwen-mei-apple-core-main-20261107-a1/qualification.json)
and [first candidate](../qwen-mei-apple-core-main-20261107-b1/qualification.json),
not the full ABBA result; normal pressure does not rule out host load or clocks.
The [completed Qwen comparison](COMPARISON-QWEN.md) confirmed the short-decode
loss in both orders. Ornith's first audited pair also showed a short-decode
loss (66.91 → 58.60 tokens/s) and a faster long prompt (166.98 → 161.88
seconds end to end). The [Ornith control](../ornith-mei-apple-core-main-20261107-a1/qualification.json)
and [candidate](../ornith-mei-apple-core-main-20261107-b1/qualification.json)
matched outputs and checkpoint hashes. The [completed Ornith comparison](COMPARISON-ORNITH.md)
confirmed both effects: short decode fell from 67.12 to 59.09 tokens/s and
long-prompt total time fell from 167.17 to 162.04 seconds. First token
accounted for nearly all of the long-prompt difference (164.75 → 159.66
seconds). The shared short-decode loss warrants investigating the runtime
path before changing either model's profile.

Trace these separately with the inference campaign stopped:

1. Check the actual D256 BF16 vector attention pipeline, query/key lengths,
   and threadgroup dimensions. Qwen has 16 query heads and 2 KV heads. Short
   decode ordinarily takes single-pass vector attention; long decode takes
   the separate two-pass route. The candidate gives single-pass attention
   a no-window specialization and a fallback if its threadgroup is too large.
   Compare with the exact control rather than assuming a fallback happened.
2. Check host time in the per-primitive command-buffer commit decision.
   The candidate's `CommandEncoder::needs_commit` resolves two dynamic
   configuration values. With no scoped override, each lookup consults a
   shared mutex and a map; the released core reads values cached on the
   device. The lookup of `MLX_METAL_RETAIN_BOUND_BUFFERS` still initializes
   a function-local static in both builds, so it is not paid on each binding.
   The candidate also looks up the BFS-width limit once per graph, rather
   than once per primitive. Check actual call counts and self time before
   changing these paths. To account for the first observed gap by
   themselves, the additional host costs would need to add up to roughly
   2.1 ms per generated token on the short prompt. A lookup microbenchmark
   without model call counts cannot establish that. Any optimization must
   preserve thread-scoped and global overrides as well as retention semantics.
3. If neither explains the gap, inspect the actually selected one-row
   affine and routed-expert kernels and command-buffer grouping. The
   upstream 3–16 row affine selection cannot directly explain a slowdown
   on the ordinary one-row decode path.

Before tracing any of those paths, isolate the
[release build's graph validation](RELEASE-BUILD-VALIDATION.md). The exact
candidate's Metal evaluator calls `CommandEncoder::verify_graph` even
though the executable is optimized. The as-built timing and native
qualification remain evidence for that executable. A separately built and
qualified candidate without the debug instrumentation should be the next
comparison.

Capture dispatch on isolated optimized diagnostic builds, with the same
prompt and the parity check. Keep their timing out of the release report.
The pinned vMLX tree already has a bounded Metal capture pattern in
`PublishedBundleForwardReplayTests.swift`: fill a new native KV cache,
synchronize, capture a single teacher-forced decode step, and stop
capture on exit. That fixture only admits K2 and Spark, so leave its
acceptance rules intact. Reuse the pattern in a dedicated Qwen diagnostic
on each [pinned release source revision](qwen-decode-trace-plan.json),
using [the opt-in capture test](QwenDecodeCaptureTests.swift) and the same
token IDs and native cache positions from the matched short request. Mei renders this text
request through `Engine.renderChatTemplate`; reuse that message/context
contract and require 26 actual input tokens and identical token ID hashes
before comparing traces. The short prompt fits inside the declared
256-token prefill step. Compare pipeline names,
dispatch counts and command-buffer grouping. Also capture one loaded step
as a negative control. A trace can show a change in routing but cannot
measure uninstrumented throughput; validate any fix with clean launch
timings and the existing observable check.

For the trace build, [the staging script](stage_qwen_trace.sh) assembles each
isolated package from its exact vMLX, MLX and mlx-c git objects, leaving the
existing worktrees untouched. Run it after timing. The 0.11.0
vMLX root lock and the candidate Mei lock agree on every external package
revision once the latter's self-pin for vMLX is excluded. Reuse those
verified external pins for both root builds, then verify the resolved
revisions and record the optimized test executable and Metal library hashes.
Use the Xcode `swiftbuild` backend so the package's Metal resources build
with the test. Once the timing and queued screens have released the machine,
stage a new directory on Expansion and build each arm without loading a model:

```sh
trace_tools=artifacts/mei-apple-core-main-20261107
trace_root=/Volumes/Expansion/local-model-bench/qwen-decode-trace-20261108
bash "$trace_tools/stage_qwen_trace.sh" "$trace_root"
for arm in control candidate; do
  env -i HOME="$HOME" PATH=/usr/bin:/bin:/usr/sbin:/sbin \
    DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
    /usr/bin/xcrun swift build --package-path "$trace_root/$arm" \
    --build-system swiftbuild --configuration release --jobs 4 \
    --disable-automatic-resolution --build-tests
done
```

Use [the guarded runner](run_qwen_trace.py) for the four captures. Pass the
actual XCTest executable inside `Contents/MacOS` and its bundled Metal
library via `--test-binary` and `--metallib`. It starts only the opt-in test,
using the committed Qwen capacity policy, and records build asset hashes and
checkpoint readback before and after. The trace and guard outcome are written
to the new capture directory on Expansion. Compare each control/candidate
receipt pair with [the trace auditor](audit_qwen_trace.py) before inspecting
the dispatch records.

The [CPU lookup screen](config_lookup_screen.cpp) isolates the exact
candidate's steady-state configuration calls, with no GPU or model. Run
only while the model benchmark is idle. The delta between the cached and
dynamic commit-limit arms estimates nanoseconds per commit decision in an
uncontended process. The single-lookup retention arms are sensitivity
controls; the actual retention flag is cached. The screen does not measure
call count, contention, or end-to-end overhead.

The [isolated CPU run](config-lookup-screen/lookup.jsonl) measured a median
65.7 ns per pair of dynamic commit-limit lookups and 0.3 ns for cached reads.
At that uncontended cost, explaining 2.1 ms per generated token would take
roughly 32,000 commit decisions per token. No such call count or contention
was measured, so this does not establish a material end-to-end cost.

```sh
xcrun clang++ -std=c++20 -O3 -DNDEBUG -DMLX_STATIC -I "$candidate_core" \
  artifacts/mei-apple-core-main-20261107/config_lookup_screen.cpp \
  "$candidate_core/mlx/config.cpp" -o "$candidate_build/config_lookup_screen"
"$candidate_build/config_lookup_screen" > config-lookup-screen.jsonl
```

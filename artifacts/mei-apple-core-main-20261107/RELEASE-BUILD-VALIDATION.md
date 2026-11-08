# Debug graph checks in the optimized SwiftPM build

The Apple-main candidate used by the original timing cohort contains
Metal graph validation introduced by Apple MLX commit `5ee1e8edf`
("Debug time graph verification", #4711) and compiled only when
`NDEBUG` is unset.
This is a build difference with a plausible cost, not a measured attribution
of the short-context slowdown.

The [binary receipt](release-build-validation.txt) identifies both executables
by SHA-256 and records the calls from the same Metal evaluation function.
The candidate's evaluator calls `CommandEncoder::verify_graph` after
`eval_gpu` and before `needs_commit`; the published 0.11.0 evaluator calls
`needs_commit` with no graph-verification call. The candidate checks whether
registered pointers refer to tracked allocations, with a shared lock and
ordered-map lookups, and checks temporary arrays against inputs and outputs.
It also tracks allocation lifetimes under a lock. These checks are useful
in Debug and should stay enabled there.

The Release define affects more than graph validation. It also disables
ordinary C/C++ assertions and debug logging options for dynamically
compiled Metal libraries on Metal 3.2 or newer. Reusing the shipped Metal
library holds the **precompiled** kernels constant. A measured difference
isolates the Cmlx Release setting as a whole; it cannot establish how
much time came from the graph checks alone.

The candidate's standalone CMake Release compile flags contain
`-O3 -DNDEBUG`, while the SwiftPM package does not explicitly set
`NDEBUG` on the Cmlx C++ target. The missing define is consistent with
the observed instructions in the optimized SwiftPM binary. Merely selecting
an optimized build configuration does not prove these checks are off.

Finish and preserve the original cohort. Then isolate the build difference:

1. Use the same pinned source, dependencies and Metal library. Build an
   optimized candidate with `NDEBUG` defined consistently for the Cmlx C++
   translation units. Keep it separate from the running candidate.
2. Check the new binary's Metal evaluator and allocator; verify the graph
   validation and allocation-tracking symbols are gone, and retain the
   working Debug build and its validation.
3. Repeat native admission and matched Qwen short/loaded timing. Compare
   the original candidate to the corrected build to size the effect, and
   use fresh published controls to decide whether any regression remains.
4. Trace attention or configuration hot paths only if a meaningful
   regression remains after that comparison.

The [build script](build_release_ndebug.sh) stages separate SwiftPM
checkouts on Expansion and inserts just the Release Cmlx define. It retains
the fresh build's Metal hash before reusing the original Metal bytes, then
requires the new executable's graph validation and allocation-tracking
symbols to be absent.

[The profile generator](prepare_release_ndebug.py) requires the completed
artifact hashes. It freezes native admission and six fresh Qwen timing
processes: published → instrumented → corrected → corrected →
instrumented → published. Each timing process retains the original
uncached 26/30,009-token prompts and five measured repeats per context.
The two outer controls establish whether the short-context gap is present
in the new session. The original and corrected builds share the MLX source
and Metal bytes; that pair isolates the Release Cmlx build change.

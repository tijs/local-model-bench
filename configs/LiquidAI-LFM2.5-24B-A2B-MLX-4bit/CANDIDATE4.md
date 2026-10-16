# Candidate 4 — bounded paged prefix cache (model-free preparation)

**Prepared, not live-admitted.** Based on benchmark commit
`0b68ce2d960e8d6754a52ea780c8fec2c57cde3c` / candidate-3 config
`63f2b2fa27ff`. Candidate-4 `mei.yaml` SHA-256 is
`516c26e481e0c22f32b728eef4e632187a1bd9c7030c8877c70c7805d665170f`
(config hash `516c26e481e0`). No results, model artifacts, tasks, thresholds,
weights, Kiem records or other-model configs were changed.

## Source and integration prerequisite

Mei implementation commit: `faf48a331b6bede352c334e0c6e3d4d4d7e10372`, on
`work/lfm25-mei-cache-bound-candidate4-20261016` in
`/Users/tijs/projects/mei-lfm25-cache-bound-candidate4`, based on
`57d87f52c3ce5b605882d06a8acf36def3bc27e7`.

The config intentionally retains candidate 3's `--mei-repo`, `--build-dir`,
model, runtime and vMLX paths: the only runtime-vector changes must be cache
policy. **The parent must review/integrate that Mei commit into the configured
`/Users/tijs/projects/mei-lfm25` before any live use.** This preparation does
not modify the clean baseline checkout. The historical release binary/hash in
`mei.yaml` is explicitly not a candidate-4 binary; a later authorized release
build must be re-recorded independently. vMLX stays unchanged at
`22969e9555b5e86df862e43e3d7356575d3dd053`.

## Exact launch delta

Actual candidate-3 and candidate-4 wrapper `--dry-run`s exited 0. Full argv
comparison, without path normalization, found only:

- `--cache-reuse false` → `--cache-reuse true`;
- added `--max-cache-blocks 4097`.

Deleting the added pair and restoring `false` reproduces the complete
candidate-3 argv exactly. Passing the immutable candidate-3 config through
the new wrapper also reproduces the immutable old wrapper's argv exactly.
Prefill 1024, fusion cache 0 (child-only environment), mmap false, allocator
32000000000, vendor sampler, context/output, connect timeout 300 and the
4.0 tok/s speed gate remain unchanged. All 130 other previously tracked files
under `configs/` are byte-identical; full fixture dry-run vectors match for
all 51 other Mei configs.

The new metadata `max_cache_blocks: 4097` mirrors the explicit launch flag;
the runner already executes `benchmark_launch_command` and needs no new
implicit override/default. Model-free orchestration tests verify the flag
reaches the runner's mocked launch call.

## Bound and validation

`--max-cache-blocks` / `ServerConfig.maxCacheBlocks` controls only
`CacheCoordinatorConfig.maxCacheBlocks`, passed directly to the existing
paged cache manager. Default: **8192**, unchanged for every omitted option,
including all named profiles. Only explicit wrapper options are forwarded.
Accepted CLI values are ASCII unsigned decimal integers in
`2...9223372036854775807`; missing, zero/one, signed, noninteger, Boolean/null,
whitespace and overflow values fail closed, including with cache reuse off.
Programmatic invalid configs are rejected before model/allocator work.
Startup logs the effective pool size and unchanged 16-token block size.

The 4097 slots include one null sentinel plus 4096 usable blocks: enough for
65536 tokens **in principle**, not a memory-safety guarantee. This is not a
limit on active per-generation KV, backing tensor bytes, SSM/disk tiers, the
MLX buffer pool or total process/system memory. No vMLX changes were needed.
Actual eviction, retained-byte savings, answer parity and speed are unmeasured.

## Verification performed

Evidence root (local scratch, not benchmark results):
`/Users/tijs/.hermes/cache/scratch/lfm25-candidate4-verification/`.

- SwiftPM `ServerConfigParsingTests|PrefixCacheConfigurationTests`: **48/48
  passed** (40 existing + 8 new), no model or GPU-array evaluation. Real
  updated Engine and tests compiled against the pinned local vMLX. Commands
  used a copy-on-write clone of baseline build caches in scratch, never its
  build directory. The repository's `use_local_vmlx.sh` verified the resolved
  dependency path and restored the unchanged tracked lockfile. Tests ran
  inside macOS `sandbox-exec` with `(deny network*)`.
- Mei local-vMLX helper: **8/8 passed**, network-denying Python audit and OS
  sandbox, zero socket attempts (`mei-helper-tests.json`). Swift in these
  helper tests is an explicit recorder, not a real build/server.
- Benchmark focused config/wrapper/runtime/orchestration/speed/connect/common
  and pure generation tests: **117/117 passed**, zero skips/errors/failures,
  zero socket attempts, locked offline uv environment plus Python audit and
  OS sandbox (`benchmark-focused-tests.json`). Wrapper non-dry-run tests use
  inert recorders; no listener or inference process is started.
- Real immutable-predecessor and candidate wrapper dry-runs and config/source
  invariants passed (`dry-run-comparison.json` / `.log`); these inspect only
  model-directory metadata and clean local vMLX identity, never weights or
  an inference endpoint.
- `bash -n runner/start_mei_server.sh` and Git diff whitespace checks passed.

Reproduction commands are recorded in the final handoff and local logs. The
Swift command uses `MEI_SWIFT=<evidence-root>/swift-outer-sandbox.sh` (adds
`--disable-sandbox` to avoid nesting SwiftPM's sandbox inside the OS denial),
then `scripts/use_local_vmlx.sh --path /Users/tijs/projects/vmlx-swift-lfm25
--revision 22969e9555b5e86df862e43e3d7356575d3dd053 --build-dir
<evidence-root>/mei-build -- test --skip-update --disable-automatic-resolution
--filter 'ServerConfigParsingTests|PrefixCacheConfigurationTests' -j 4`.
All commands set `TMPDIR=<evidence-root>/tmp`.

Initial verification setup was corrected, not hidden: direct strict SwiftPM
resolution tried to materialize the public dependency's absent submodules;
the network-denying sandbox blocked it. Using the supported local-vMLX graph
helper resolved that setup without network access or pin/source changes.
An initial overbroad Python selection included 13 loopback-server tests; the
audit denied all binds before any listener existed. Final selection excludes
those service-backed classes rather than weakening the no-network boundary.
The failed initial Python report/log are retained as
`benchmark-initial-network-denied.json` / `.log`. No full service/model
acceptance suite was run or claimed green.

## Remaining live gates (parent-owned, not executed here)

After source integration and independent review: fresh sustained resource,
disk, owner/port gates; full admission **including cache and exact context**
(no `--skip-cache` or `--skip-context`); bounded one-task/resource review.
Only then consider the unchanged full benchmark and speed gate. CoCore remains
unloaded: do not restart or restore it. This preparation demonstrates plumbing
and validation only, not cache correctness, memory safety or performance.

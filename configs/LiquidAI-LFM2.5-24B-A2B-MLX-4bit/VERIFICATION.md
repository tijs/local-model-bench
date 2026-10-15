# Staged/build provenance, model-free verification and current gates — 2026-10-15

The model-free checks recorded below performed no model download, staging,
inference-server launch, canary, or benchmark, and wrote no global/named Hermes
profile state. They preserved existing results, tasks, fixtures, checks and
ledger pins. Separate parent/operator model staging, release build and profile
provisioning after the initial checks are recorded below; they were not test
side effects. This repository-only follow-up reads that evidence and updates
config/provenance/runtime wiring without altering model or profile files.

## Hermes Ops connect-watchdog correction (latest gate status)

This section supersedes the pending-live status of the earlier staging/build
records below. **Prior live evidence is parent/operator-reported**, supplied to
this repository-only repair; it was not produced by these model-free tests:

- Separate native admission passed **12/12**, including full context and tools.
- The canonical attempt loaded **Mei 0.9.0**; exact model identity and plain
  completion passed, then sanity passed **2/2**.
- **Four Hermes Ops rows** repeatedly failed with `timeout_phase=connect`, no
  prompt/completion token usage, and
  `stream stalled (connect): no qualifying progress for 60.0s`.
- **Four later Hermes Ops harness errors** followed the parent's server stop;
  they are not additional evidence of the original watchdog failure.
- The incomplete attempt's identity is config **`0fb346ed9077`** / runner
  **`edda01df84c3`**. All raw rows, snapshots, speed-gate records and generated
  leaderboard artifacts remain untouched. No completed battery is claimed.

Source review establishes the harness boundary, not a measured prefill cause:
`runner/run_prompt.py` keeps `DEFAULT_CONNECT_TIMEOUT = 60.0` and calls
`urllib.request.urlopen(..., timeout=min(connect_timeout, timeout))`, which
waits for response headers as well as TCP/request setup. A backend that delays
headers during a long prompt cannot yet use the separate first-progress budget.
`tasks/hermes_ops.yaml` keeps **1000s per turn**, **600s first progress**,
**300s stream idle**, and **14400s per task**. The 1000s value is the turn budget,
not the whole-task deadline.

The only new execution setting is top-level **`hermes_ops_connect_timeout: 300`**:

- Explicit bounded harness policy for this model, **not** vendor sampling,
  vendor advice, a measured optimum, or proof that 300s is sufficient.
- `run_prompt_suite.py` validates positive finite numeric seconds (int/float,
  no bool; explicit null, strings, zero, negatives, infinity, NaN and integers
  outside the client's float range fail closed before snapshots/tasks/rows).
- Applies **only** to `--suite hermes_ops`, overriding an explicit suite connect
  value if present, and uses the existing `--connect-timeout` forwarding path.
  On other prompt suites a declared value is validated but never applied.
- Without the field, suite-specific connect values and the client **60s default**
  remain unchanged. Sanity/coding, sampler/effort, context, cache, mmap, launch
  identity, turn/task budgets, other watchdogs and retries are unchanged.
- The config's changed bytes give the corrected retry hash **`a4be8e840181`**
  (`sha256(mei.yaml bytes)[:12]`, computed without creating a result snapshot),
  distinct from **`0fb346ed9077`**. Commit it before a retry; never rewrite or
  coalesce the incomplete old attempt.

### Executed model-free regression checks

In the isolated repair worktree, using its own locked uv environment:

```bash
env -u PYTHONPATH -u PYTHONHOME TMPDIR=/Users/tijs/.hermes/cache/scratch \
  uv run --locked python -m unittest runner.tests.test_run_prompt_suite \
  runner.tests.test_generation_overrides runner.tests.test_lfm25_setup -v
# exit 0: 62 tests (11 connect/config, 36 generation overrides, 15 LFM setup).
env -u PYTHONPATH -u PYTHONHOME TMPDIR=/Users/tijs/.hermes/cache/scratch \
  uv run --locked python -m unittest runner.tests.test_run_prompt_timeouts \
  runner.tests.test_generation_policy runner.tests.test_run_bench \
  runner.tests.test_bench_common -v
# exit 0: 72 tests (38 timeout/liveness, 11 generation policy, 20 orchestration,
# 3 shared helpers). Combined: 134 tests, 0 failures/errors/skips.
git diff --check
# exit 0.
```

The new connect/config tests mock every child runner/grader/RSS call; they prove
the real LFM override reaches the CLI, all **122 existing model configs without
the field** omit the override, absent/no-config clients retain 60s, invalid
values fail before snapshots/tasks/rows, explicit suite-budget precedence is
preserved, and sanity/next-config invocations cannot inherit the override.
LFM setup checks pin the new attempt identity and unchanged vendor/context/
mmap/runtime/profile controls; coding invocations receive no connect flag.
The adjacent existing SSE tests use only loopback **scripted HTTP fixtures**,
not an inference backend; synthetic rows/snapshots stay under disposable roots.

The new LFM-forwarding regression was also replayed against the original
`edda01df84c36ad658d2ad4de839b5fd08e0f16c` source loaded in memory, with the same
mocks. It produced the **expected single assertion failure** for the missing
`--connect-timeout`; the verifier exited 0 after confirming that failure and no
errors. The fixed source's regression passes in the 62-test group above.
This is a model-free red/green check, not a failed live run or benchmark row.

A parsed before/after config comparison confirmed that **only**
`hermes_ops_connect_timeout`, `settings` and `known_gaps` changed: the sampler,
context/cache/mmap/launch identity and other execution settings are identical.
Full discovery was not rerun; the historical ledger-count caveat below is not
resolved or hidden by these focused checks.

### Current remaining gates

**Live recovery remains unverified.** No inference/model-server/full-benchmark,
launch/stop/unload, Hermes profile or CoCore change, external result-ledger write,
or push is part of this repair. A future authorized retry must recheck resources
and build identity, retain admission/sanity/speed gates, and independently verify
the full 25-task inventory, new config hash/runner SHA, failure classes and
exact-runtime teardown. Prior admission does not bypass those checks or establish
performance; no sampler/cache/context/mmap/task-timeout tuning is included here.

## Exact source/build selection

- vMLX: `22969e9555b5e86df862e43e3d7356575d3dd053`, based on router fix
  `ed49a4daf1d30cb31a7a38f4f06feceada23cced`.
- Mei: `57d87f52c3ce5b605882d06a8acf36def3bc27e7`, with v0.9.0 base
  `6b632ebea3b2b843085ad4f37a0e75b31df3e4d7` verified as an ancestor.
- The real SwiftPM resolved graph reports `vmlx-swift` in editable mode at the
  `vmlx-swift-lfm25` worktree, not the public `633fe166` checkout. The compiled
  `MLXLLM-t.build/Objects-normal/arm64/LFM2MoE.d` lists that worktree's
  `Libraries/MLXLLM/Models/LFM2MoE.swift` as an actual compile dependency.
  Router source SHA-256:
  `e2ceebefcfb55c7d0e3f0763be9b3ffd3c56c7d042b346641edd0a3d986f89d2`.
- The built **debug**, model-free Mei executable is 147130992 bytes, SHA-256
  `aa8df0c125a5e0b364cdb602c65ba5e7008958c5fa853b87a35aa7753b029e45`.
  This is not release/metallib provenance or live compatibility evidence.
- Mei `Package.swift` / `Package.resolved` retain the public pin byte-for-byte.
  `Packages/` editable symlinks and `.build/` state are ignored, machine-local.

### Verified release artifacts (supersedes the debug-only build gate)

The parent built the release from the exact Mei/vMLX source identities above.
The repository-only follow-up independently read back the following sizes and
SHA-256 values and ran only `mei --version` (**`mei 0.9.0`**, exit 0; no load):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/Users/tijs/projects/mei-lfm25/.build/release/mei` | 92,419,520 | `158f65675e9cd6aee55beeab73b89cdb303e0888cf1aeba5562998cece1aadde` |
| `.build/release/mlx.metallib` | 2,422,136 | `0f6bdc29ff9afb81369eb5ca6f6561e0fdbb63228db0d4520c91e3c281738da3` |
| `.build/release/mlx-swift_Cmlx.bundle/Contents/Resources/default.metallib` | 2,422,136 | `0f6bdc29ff9afb81369eb5ca6f6561e0fdbb63228db0d4520c91e3c281738da3` |

The `.build/release` alias resolves to `.build/out/Products/Release` in the
`mei-lfm25` worktree. The source Cmlx library and packaged library are
byte-identical. The read-back `.build/release/mlx.metallib.provenance` records:

- Label **SwiftPM Cmlx build product**, with structural MTLB/size/file checks.
- Installed at **2026-10-15T14:58:11Z**.
- Vendored MLX **0.32.2**, from
  `/Users/tijs/projects/vmlx-swift-lfm25/Source/Cmlx/include-framework/mlx-version.h`.
- `vmlx_checkout_revision` **22969e9555b5e86df862e43e3d7356575d3dd053**.
- The exact packaged-library SHA-256 shown above.

The parent confirmed the public Mei `Package.resolved` remains unchanged and
SwiftPM editable state points to the local vMLX worktree. The launcher builds
again on a real launch: recheck resulting artifact identity before treating
these hashes as the served binary/library. Build success and artifact identity
do **not** establish loadability or speed.

## Completed authorized staging and integrity

The official quant is staged at:

```text
/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-MLX-4bit
```

Artifact repository **LiquidAI/LFM2.5-24B-A2B-MLX-4bit**, immutable revision
**667408d494bde191c2cb9dd4f4549827816b9275**; source-model provenance revision
**1769516ac588c4c558089c94f27d96b0dc67b183**. The parent ran
`/Users/tijs/projects/mei-lfm25/tools/stage_mlx_checkpoint.py --verify-only`
against this target and independently hashed the local files. Its pinned-revision
Hub `HfApi.list_repo_tree(..., recursive=True, expand=True)` check confirmed all
three local weight hashes and byte counts match LFS metadata exactly:

| Weight shard | Bytes | SHA-256 |
|---|---:|---|
| `model-00001-of-00003.safetensors` | 5,318,453,801 | `17e953456c62314a498f1ef5ee8a5f1b51ac83f6b6bb684f160dde4f92cd11c0` |
| `model-00002-of-00003.safetensors` | 5,344,895,125 | `c3ae09dba31b3786c325425435021cf5d5bf06c1a79acb31a741e15a47e5bb14` |
| `model-00003-of-00003.safetensors` | 2,903,945,409 | `9814144af5045ea8c96e2f1352148fdbe9f8a0085b76df6d6760efbe916e9840` |

- Verification: **`ok=true`, `reasons=[]`**, 3 shards, exact weight-file set.
- File bytes **13,567,294,335** = tensor payload/index **13,567,188,992** +
  header overhead **105,343**. Index totals exclude safetensors headers.
- Architecture **Lfm2MoeForCausalLM**, model type **lfm2_moe**; quantization
  **4-bit affine, group size 64**.
- `config.json` SHA-256:
  **4901707c3cef43e3cf68a0dedc3e39687de43413cab30578a32c63c643984244**.
- **12 staged files**, exactly **13,585,304,293 bytes** including sidecars
  within the model bundle (config/tokenizer/template/index/README/license/etc.).
- Durable machine-local sibling evidence: `<model-dir>.integrity.json`
  (all 12 byte sizes/hashes and Hub comparison) and `<model-dir>.provenance.json`
  (container/index result; recorded **2026-10-15T15:21:23.631740Z**).
- Tracked **metadata only**: `staging-provenance.json` mirrors those identities
  and explicitly records **staged-complete-loadability-pending**. No weights,
  model copies or generated runtime files are added to Git.

The follow-up called only the verifier's pure `verify(target)` function using
`python -B`, not its CLI (even `--verify-only` rewrites the external provenance
sidecar). That read-only check again returned **ok=true / reasons=[]**, matched
all 12 file sizes, and rehashed the 9 non-weight files against the integrity
manifest; the 3 full-shard hash/remote-match results above are the parent's
completed check, not a newly repeated download/hash. Free disk after staging
was **20.104 GiB** per the parent's measurement, above the **10 GiB** floor.
This is historical headroom, not a future launch guarantee. **No model load,
generation, canary or benchmark has started.**

### Dtype alignment audit and explicit non-mmap safety policy

The parent and the follow-up independently called only `audit()` and
`parse_header()` from `mei-lfm25/tools/align_safetensors.py` on the **exact
staged root**, imported with `python -B`. Its repack/CLI entry point was not
executed and **no original file was modified**:

| Shard | Absolute `data_start` | Dtype-unaligned / total tensors | Unaligned tensor bytes |
|---|---:|---:|---:|
| `model-00001-of-00003.safetensors` | 43049 | 358 / 358 | 5,318,410,752 |
| `model-00002-of-00003.safetensors` | 40341 | 331 / 331 | 5,344,854,784 |
| `model-00003-of-00003.safetensors` | 21953 | 181 / 181 | 2,903,923,456 |

All **870/870 tensors**, totaling **13,567,188,992 payload bytes**, are
dtype-misaligned. This is not corruption or a failed integrity check: a valid
safetensors container need not have dtype-aligned absolute tensor offsets.

The LFM launch now pins **`--load-mmap false`**, using the wrapper's existing
explicit-only option. Source-backed rationale on the exact pinned stack:

- Mei `57d87f52c3ce5b605882d06a8acf36def3bc27e7`,
  `Sources/MeiCore/ServerConfig.swift:101-105,275-276`: the mmap loader defaults
  on, the source warns about aligned-copy memory costs, and the parser accepts
  the explicit false value.
- Same Mei pin, `Sources/MeiCore/Engine.swift:119-137`: `Engine.load` forwards
  `config.useMmapSafetensors` into `LoadConfiguration`.
- vMLX `22969e9555b5e86df862e43e3d7356575d3dd053`,
  `Source/Cmlx/mlx/mlx/io/safetensors.cpp:712-758`: naturally aligned tensors can
  use mapped views; otherwise `allocator::malloc(byte_length)` and `std::memcpy`
  materialize aligned tensor storage. All tensors in this artifact would take
  that copy branch, increasing resident-storage/OOM risk on this large pack.

This is an explicit **memory-safety policy**, separate from vendor sampler
settings and not a measured optimization, speedup or loadability claim.
Other configs and generic defaults are unchanged. **No repack or original-file
healing is authorized**; the official model directory, byte counts and shard
hashes above remain unchanged. Metadata includes the exact read-only audit.

### Passed sustained pre-load resource gate (immediate recheck still required)

The parent's full 11-sample JSONL was read and parsed, not inferred from a
single sample. It spans **2026-10-15T15:31:16.470298+00:00** through
**2026-10-15T15:35:48.550447+00:00**:

- **PASSED 11/11 samples**, reclaimable memory **min 21.151 / max 21.546 GiB**,
  every sample above the **10 GiB** floor (free + inactive pages).
- Physical RAM **34,359,738,368 bytes**; swap used **0 throughout**.
- No inference owners and **port 8029 free throughout**.
- Original evidence:
  `/Users/tijs/.hermes/cache/scratch/lfm25/memory-gate-2026-10-15.jsonl`.
- Tracked verbatim metadata-only copy: `preload-memory-gate.jsonl`, **3345 bytes**,
  SHA-256 **16df588407205516d6ae922ef62cf3659fe87b58b0966cfd4099e2075feda12a**.
  The summary and evidence hash are also in `staging-provenance.json`.

This records a **passed historical pre-load gate**, not continuing ownership
of a clean window. **Immediately recheck clean-GPU/memory/disk/listener state
before launch**; keep the 10 GiB disk floor and preserve all original artifacts.
No model load, canary or full-battery result is implied or performed.

## Executed checks

Initial source/build checks, before the repository-only profile-policy
follow-up, in the respective isolated worktree roots:

```bash
# vMLX: install only a build-tree alias from the already-generated metallib.
MLXPRESS_MLX_METALLIB="$PWD/.build/out/Products/Debug/mlx-swift_Cmlx.bundle/Contents/Resources/default.metallib" \
  bash scripts/prepare-mlx-metal.sh .build/out/Products/Debug/mlx.metallib
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test --filter LFM2MoE
# exit 0: 7 Swift Testing cases (5 router including forward + 2 legacy
# sanitization), plus 1 matching XCTest reasoning/template case.

# Mei (same override tested twice, including idempotent selection):
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  bash scripts/use_local_vmlx.sh --path ../vmlx-swift-lfm25 \
    --revision 22969e9555b5e86df862e43e3d7356575d3dd053 \
    -- test --filter ServerConfigParsingTests
# exit 0: 40 tests, 0 failures. Includes LFM profile and generic sampler checks.
python3 -m unittest discover -s scripts -p test_use_local_vmlx.py -v
# exit 0: 8 tests, 0 failures (explicit fake Swift + real temporary Git repos).

# Benchmark focused suites, each exit 0:
uv run --locked python -m unittest discover -s runner/tests -p test_lfm25_setup.py -v
# 8 tests
uv run --locked python -m unittest discover -s runner/tests -p test_start_mei_server_sh.py -v
# 8 tests
uv run --locked python -m unittest discover -s runner/tests -p test_run_bench.py -v
# 20 tests
uv run --locked python -m unittest discover -s runner/tests -p test_run_fixture_suite.py -v
# 30 tests
uv run --locked python -m unittest discover -s runner/tests -p test_generation_overrides.py -v
# 36 tests; focused benchmark total 102 tests, 0 failures.
```

`bash -n` passed for both modified shell helpers. The actual YAML launch argv was
also run with **`--dry-run` only**, substituting a temporary metadata-only fixture
(`config.json = {}`, no weights) for the unstaged model directory. It validated
the real clean vMLX revision and printed the expected local path, port 8029,
context 65536, output budget 4096, model profile and vendor sampler. No build,
runtime directory or server was started by this check.

The offline orchestration test mocks all side effects and proves suite inventory
`2 + 8 + 5 + 3 + 4 + 3 = 25`, forwarding profile `bench-lfm25` and provider
`lfm25-mei` to all four coding suites without resetting the shared bench profile.
It does not produce or claim 25 actual result rows.

## Repository-only profile-policy follow-up

```bash
env -u PYTHONPATH -u PYTHONHOME uv run --locked python -m unittest \
  runner.tests.test_lfm25_setup runner.tests.test_start_mei_server_sh -v
# exit 0: 18 tests, 0 failures/errors (10 LFM config/profile + 8 launcher dry-run).
```

The added regression checks pin all benchmark CLI controls, terminal cwd and
memory flags in the repository template, and parse README provisioning arguments
to verify every template leaf has the matching explicitly scoped CLI command.
List arguments remain a single shell argument, and approvals mode remains the
string `"off"`, not YAML's boolean `false`. These checks do not execute the
provisioning recipe or access installed profile state. No inference/server or
benchmark launch is involved. Full discovery was not rerun in this follow-up;
the historical broader-suite caveat below is unchanged.

## Broader-suite caveat (not an LFM regression)

An additional full model-free Python test discovery was attempted:

```bash
env -u PYTHONPATH -u PYTHONHOME uv run --locked python -m unittest discover -s runner/tests -v
```

**408 tests ran, 3 failures, 0 errors (exit 1)**. All failures are the existing
`test_quant_ledger_audit.LiveLogReproductionTest` count pins:

- Qwen3.6 vision: pinned 1/14, derived 1/15.
- Qwen3.6 text-only: pinned 1/10, derived 1/13.
- Ornith: pinned 0/40, derived 0/42.
- MLX-uniform-4bit aggregate: pinned 4/69, derived 4/75.
- All-Mei aggregate: pinned 5/91, derived 5/97.

`git diff --exit-code 76e8497fc68ef8e053b93eb0b1014af1710b710b -- results tasks fixtures checks runner/quant_ledger_audit.py runner/tests/test_quant_ledger_audit.py`
passed: these inputs and pins are unchanged by this work. Updating historical
ledger conclusions is outside this repair, so those failures are reported, not
hidden or "fixed" by rewriting results/pins.

The first broad attempt inherited Hermes's Python-3.14 `PYTHONPATH` in the
project's Python-3.12 process, causing 2 NumPy import errors (365 discovered tests,
3 ledger failures, 2 errors). Removing only `PYTHONPATH` / `PYTHONHOME` for the
retry fixed the environment errors; no packages or global settings were changed.
Full compatibility/full-suite-green is **not** claimed.

## Runtime evidence isolation and regression follow-up

The parent found retained logs in the historical
`/Users/tijs/.local/share/local-model-bench/mei-runtime` tree, including a
**2,660,922-byte server.log**, and no `server.pid`. Reusing the launcher default
would truncate its build log and append to its server log. This follow-up did
not use or modify that historical tree.

The LFM config's top-level `mei_runtime_base` **and** launch `--runtime-base`
now select **`/Users/tijs/.local/share/local-model-bench/mei-runtime-lfm25`**.
The launcher owns `server.pid` there and `logs/build.log` / `logs/server.log`.
Shared `bench_common.mei_stop_command` now passes the configured path for:

- `run_bench.py`'s pre-launch stop.
- `run_bench.py`'s unconditional `finally` cleanup, including early returns.
- `run_mei_acceptance.py` cleanup, still **before wrapper termination**.

Without the new optional field the stop command remains unchanged, preserving
the shell script's existing default/`MEI_RUNTIME_BASE` behavior. Explicit
null/empty/non-string/relative paths fail closed rather than silently selecting
the shared PID file. Paths with spaces remain a single argv argument. The
config/launcher values are consistency-tested; new configs must set both.

The LFM launch paths are literal absolute paths, not `$HOME`/`$PWD` shell
expressions: acceptance launches an argv list, so it cannot expand those
expressions like `run_bench`'s shell does. Both runners now identify the same
staged model, source worktrees, build directory and isolated runtime.

Executed regression checks (exit 0):

```bash
env -u PYTHONPATH -u PYTHONHOME uv run --locked python -m unittest \
  runner.tests.test_lfm25_setup runner.tests.test_mei_runtime \
  runner.tests.test_start_mei_server_sh runner.tests.test_run_bench \
  runner.tests.test_run_fixture_suite runner.tests.test_generation_overrides \
  runner.tests.test_bench_common runner.tests.test_retired_lanes -v
# 132 tests, 0 failures/errors, 0 skips.
# LFM config/profile/provenance/alignment/memory 14; runtime/cleanup 11; launcher dry-run 10;
# orchestration 20; fixture runner 30; generation overrides 36;
# bench_common 3; retired-lane compatibility 8.
bash -n runner/start_mei_server.sh runner/stop_mei_server.sh
git diff --check
```

The 35-test LFM/runtime/launcher subset also passed independently. All
launch/stop/unload/health/probe calls in runtime orchestration tests are explicit
mocks, and acceptance records/results are written only under temporary fixture
roots. No real stop/unload script, profile provisioning or inference ran.
The real config was additionally parsed with acceptance's `split_launch_command`
and passed to the wrapper with **`--dry-run` only**, using the already-staged
model path. It exited 0, verified the exact clean local vMLX revision, printed
the isolated runtime/PID/log paths, explicit **`--load-mmap false`**, and expected
**8029 / 65536 / 4096** vendor sampler argv. The new runtime directory was absent
both before and after.
No build, runtime directory, server, model load or benchmark was created by
that dry-run. Full discovery was not rerun; the historical ledger caveat above
is preserved, not resolved or hidden by this focused pass.

## Pre-live remaining gates (historical; superseded by latest status above)

**Profile provisioning/readback is complete**, verified separately by the
parent/operator, not by the model-free tests. A fresh, non-cloned `bench-lfm25`
profile was provisioned outside this repository, and
`hermes --profile bench-lfm25 config check` passed. Readback confirmed:

- Main-model and named-provider routing agree on `lfm25-mei`,
  `http://127.0.0.1:8029/v1`, `chat_completions`, the exact served model
  `LiquidAI/LFM2.5-24B-A2B-MLX-4bit`, and context **65536**.
- Vendor `extra_body` is temperature **0.1**, top_k **50**, top_p **0.0**,
  min_p **0**, repetition_penalty **1.05**, max_tokens **4096**, and
  reasoning_effort **null**; thinking-template behavior is unchanged.
- Benchmark CLI policy matches the existing `bench` profile:
  `agent.max_turns: 40`, `approvals.mode: "off"`, `platform_toolsets.cli:
  [clarify, code_execution, connections, file, terminal, todo]`,
  `skills.external_dirs: [/Users/tijs/.hermes/skills,
  /Users/tijs/.hermes/shared-skills]`, `plugins.enabled: []`, and
  `model.max_tokens: 4096`. `terminal.cwd` is `.`, and both
  `memory.memory_enabled` and `memory.user_profile_enabled` are **false**.
- The profile's `.env` has no non-comment entries. No history, channels, or
  credentials were copied, and shared `bench` / `default` profiles are unchanged.

The repository template and README now reproduce these explicit controls.
Their model-free regression tests only read repository files and mock runner
side effects; they neither provision nor alter any installed profile.

**Model staging/integrity and release build/artifact provenance are complete**
as recorded above. The **11-sample sustained pre-load gate passed**, with an
immediate pre-launch recheck still required. **Model loadability and inference
behavior are still pending**; neither staging, a passed memory poll nor a
version/build check proves them.

Still required, with no benchmark results claimed:

1. Immediately recheck clean-GPU/memory/disk/listener state (including the
   10 GiB launch floor) before loading, without further deletion. Keep the
   config committed, use only the dedicated LFM runtime, and retain the explicit
   `--load-mmap false` policy without repacking/healing the official artifact.
   Recheck binary/metallib identity if the launcher rebuilds them.
2. Pass bounded text/SSE/native-tool/reasoning/multi-turn/cache/context canaries,
   including live profile/provider routing and sampler preservation.
3. Only after correctness, measure prefill/cache/memory/decode choices on the
   exact model/stack before any optimization or speed claim; preserve vendor
   sampling and use at least three repeats for performance claims.
4. Run the real full **25-row** battery through the normal sanity/speed gates,
   then independently audit counts, config hash, runner/source/artifact identity,
   failure classes, exact-runtime teardown, process exit and port closure.

Vendor sampler and **4096/65536** output/context policy are unchanged. No model
or profile file change, staging/download, server launch/stop, canary, benchmark,
`unload_all.sh` execution, CoCore action or historical-ledger edit is part of
this repository-only follow-up. No push or further storage cleanup is authorized.

# LFM2.5-24B-A2B community OptiQ — cache-off speed-gate candidate

**The pinned local artifact is integrity-verified; no live model has been
loaded.** Loadability, speed, resource safety and native tool parsing remain
unverified. This is a distinct community OptiQ variant of
`LiquidAI/LFM2.5-24B-A2B`, not a Liquid-official quant.[1][4][6]

## Pinned identity and provenance

- Benchmark base: `83d06b3978210b850c42e61e09d28c240a86d7e5`.
- Local worktree: `/Users/tijs/projects/local-model-bench-lfm25-optiq-speed-gate`.
- Local branch: `work/lfm25-optiq-speed-gate-20261016`.
- Config: `configs/LiquidAI-LFM2.5-24B-A2B-OptiQ-4bit/mei.yaml`.
- Config SHA-256 after the local-staging record was added:
  `00993a15f20e94fc72912f12ff3ec1994118d96a37527fa818bb40cdc5539af1`;
  short config hash **`00993a15f20e`**.
- Artifact: `mlx-community/LFM2.5-24B-A2B-OptiQ-4bit`, immutable revision
  `b5552f7f7e597e2ca02653f89098dea86b8818af`.[1]
- Mei source: `faf48a331b6bede352c334e0c6e3d4d4d7e10372`;
  effective vMLX: `22969e9555b5e86df862e43e3d7356575d3dd053`.
  The config work did not change or rebuild these source trees.
  `mei_source_commit` names Mei; `mei_commit` names vMLX.

`source-provenance.json` records the complete pinned remote tree, parsed model
config including both quantization maps, remote LFS expectations, index summary,
generation/KV/tokenizer metadata, and retrieval byte hashes/URLs/timestamps.
It is **not a staging or local-integrity manifest**. The original config-prep
work used ten GETs only for small public metadata/sidecars; that phase did not
access weight URLs/data or the local model directory. Parent staging and local
checks are separately recorded in `local-staging-verification.json`.

### Exact remote inventory

The revision's recursive tree has **16 entries: 15 files and the `optiq/`
directory**; all files total **16,690,854,530 bytes**. Its four safetensors files
total **16,672,710,010 bytes**, distinct from the index's tensor payload
**16,672,595,968 bytes** (946 indexed tensors). Remote LFS SHA-256 values below
are expected checksums; the separately staged local files later matched all
four exactly.[2][7] See the local-staging addendum below.

| Shard | File bytes | Expected remote LFS SHA-256 |
|---|---:|---|
| `model-00001-of-00004.safetensors` | 5304487785 | `4d7098a0724e7366d465bd6f27a049cb02a283d4b175b508eb487925bbd162c9` |
| `model-00002-of-00004.safetensors` | 5366869129 | `0618aa025a4d5f61317f342ec24fcd4bd1c3f57602e57623c0c805fbec2680db` |
| `model-00003-of-00004.safetensors` | 5303873260 | `8255962bf517936bae8741218c201796c91f4089c1e32eb54dc00b6597fc0d3c` |
| `model-00004-of-00004.safetensors` | 697479836 | `a1677ef46d752b53b1b0cdfd980cfa305f1fc39c0d8418450cd6a53704c24e2d` |

The pinned `config.json` identifies `Lfm2MoeForCausalLM` / `lfm2_moe` and contains
**identical `quantization` and `quantization_config` objects**: affine, default
4-bit, group64, with 259 module overrides (**94 at 4-bit, 165 at 8-bit**; all
group64). The fetched config is 61,692 bytes with SHA-256
`4feddba177b137076d08b01c087c3d6b2acbe2913c6395154536539a92bf47fc`.[3]

OptiQ's separate metadata reports `optiq_mixed_precision`, target 5.0 bpw,
achieved 5.013271628972867 bpw, 158 high-bit layers and 94 low-bit layers.
Those layer counts are not the config's complete module-map count. The
metadata names the upstream base model but does not supply its immutable
conversion-input revision; this config therefore leaves that revision null
rather than borrowing the official quant's provenance.[6]

The card's size comparison is against bf16, **not against the retired official
4-bit artifact**.[4] Against the predecessor config's historical 13,567,294,335
weight bytes, this OptiQ quant is **3,105,415,675 bytes larger (22.889%)**.
No speed or memory benefit follows from size or publisher capability scores.
No such scores were independently reproduced.

`generation_config.json` contains temperature 0.1, top_k 50 and repetition
penalty 1.05.[5] Top-p 0 and min-p 0 are deliberately retained from the
predecessor's vendor-faithful execution contract, not inferred OptiQ server
defaults. The bundled `kv_config.json` describes OptiQ serving policy; no
per-layer KV quantization or OptiQ runtime is enabled in Mei by this config.[8]
The tokenizer metadata and chat template were fetched and hashed only; their
presence does not prove correct Mei prompt construction or tool parsing.[9][10]

## Exact execution contract

The immutable predecessor is base-commit file
`configs/LiquidAI-LFM2.5-24B-A2B-MLX-4bit/mei-cache-off-revalidation.yaml`, SHA-256
`e6be308f5709d4a0ef3a49cc158b50d44bd9c2047a8a47594873c038c3f1babb`.
All parsed execution fields and the complete raw command string are preserved
except the **model directory and served/model IDs**. Only source/quant
provenance and documentary fields otherwise change. Endpoint, port, Mei/vMLX
pins, build/source paths, runtime, Hermes profile/provider and task budgets are
unchanged. `orchestration.viable: full` preserves eligibility, not admission.

Fixture-verified wrapper output, with only scratch paths mapped back to the
literal configured paths (the following vector was **not executed**):

```text
env VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 /Users/tijs/projects/mei-lfm25/.build/release/mei --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-OptiQ-4bit --served-model-id mlx-community/LFM2.5-24B-A2B-OptiQ-4bit --host 127.0.0.1 --port 8029 --context-cap 65536 --temperature 0.1 --top-p 0 --top-k 50 --emit-reasoning true --cache-reuse false --max-tokens 4096 --prefill-step-size 1024 --min-p 0 --repetition-penalty 1.05 --model-profile lfm2.5-24b-a2b --memory-limit-bytes 32000000000 --load-mmap false
```

No `--max-cache-blocks` or `max_cache_blocks` metadata is added. No KV/disk
cache, anchors, seed, reasoning effort or thinking override is added.
Fusion-cache0 is child-only, not a global environment change. Context65536,
output4096, prefill1024, allocator32000000000, mmap false, vendor sampler and
Hermes Ops connect300 remain fixed. An allocator ceiling is not a process/system
memory bound. Repeated long prompts can be slower with prefix reuse off.

## Offline regression scope

The existing inventory test admits exactly this one new YAML in addition to
the already-authorized cache-off YAML. Its original candidate-3 byte comparison
loop and all cache-off parsed/raw-command/full-vector assertions remain intact.
The generic no-fusion-defaults test excludes only the exact new path; every
pre-existing lane still runs unchanged. The full candidate-3-wrapper comparison
continues to exercise the new config as well. New tests pin the entire parsed
execution mapping, raw command, complete wrapper input/emitted argv, all baseline
config bytes, exact new-file inventory, remote metadata and full mixed-precision
maps. Follow-up assertions pin the separate local manifest's exact bytes/hash,
all 15 file paths/sizes, every recorded LFS digest, payload/header accounting,
and the still-unchecked loadability boundary. The remote-only provenance stays
byte-identical. Mocked prompt/acceptance tests preserve budgets, context, identity,
`--skip-cache`-only behavior and failed-probe status. Mocks are fixtures, never
benchmark results.

## Historical model-free config-prep verification

The checks and setup notes in this section describe the original model-free
config-prep commit `c30201352931a7561d7a0ffa7f8b5f35f124e367`, before parent staging.
They are not local weight-integrity evidence or fresh live admission. The later
staging record and this follow-up's offline checks are separate addenda below.

Evidence root: `/Users/tijs/.hermes/cache/scratch/lfm25-optiq-speed-gate-prep-20261016/`.
Those tests used task-scoped `TMPDIR`, an isolated local CPython3.12.13 environment,
`uv --locked --offline --no-sync`, and a macOS network-denying sandbox. Python
audit hooks additionally deny/record socket operations. The sandbox also denies
real model/HF weight reads, protected checkout/results/runtime/profile writes,
and real inference/Swift execution; only metadata fixtures/inert recorders run.

### Executed checks and preservation

- Exact inventory regression plus `runner.tests.test_lfm25_setup` and
  `runner.tests.test_lfm25_optiq_setup`: **26/26 passed**, 0 failures/errors/skips,
  exit 0 (`exact-config-setup-tests.log`, 4.447s).
- The predecessor's same 117-test offline selection plus all seven new OptiQ
  tests: **124/124 passed**, 0 failures/errors/skips, exit 0
  (`focused-offline-tests.log`, 12.654s). Both audit reports record **zero
  Python socket attempts**; the OS denies network for the process tree.
- The original closed-inventory assertion was first exercised unchanged:
  **1 failure, 0 errors**, naming only the authorized new OptiQ YAML
  (`inventory-authorized-addition-red.log`). The original byte comparisons
  passed. The narrow explicit-path repair then passed with the full suites.
- `config-validation.json`: wrapper dry-run exit0, complete **37-token** emitted
  vector, all **134 pre-existing config files (125 YAML)** byte-identical to
  the requested base, exact config and provenance hashes. Fixture echo guards
  are explicitly not real source-selection/build validation.
- `bash -n runner/start_mei_server.sh runner/stop_mei_server.sh` and
  `git diff --check`: exit0.
- `protected-state-before.json` versus `protected-state-after-tests.json`:
  **`PROTECTED_STATE_UNCHANGED=true`**. Every inventoried protected checkout's
  HEAD/branch/status/diff hashes and file bytes/modes/mtimes match, including all
  ignored result files. The results-dirty parent contains **2,514 result files**;
  its status and every inventoried result are unchanged. Existing runtime/live
  evidence trees and configured build artifacts match. Retired official model
  paths and HF weight caches were deliberately excluded and never inspected.

Exact focused selection (run from this worktree; `E` is the evidence root):

```bash
export TMPDIR="$E/tmp" PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
export UV_PROJECT_ENVIRONMENT="$PWD/.venv" UV_PYTHON_DOWNLOADS=never UV_NO_PROGRESS=1
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
EVIDENCE_SUMMARY="$E/focused-offline-tests.json" \
  sandbox-exec -f "$E/offline.sb" uv run --locked --offline --no-sync python -B \
  "$E/offline_unittest.py" \
  runner.tests.test_start_mei_server_sh \
  runner.tests.test_lfm25_setup \
  runner.tests.test_lfm25_optiq_setup \
  runner.tests.test_mei_runtime \
  runner.tests.test_run_bench \
  runner.tests.test_run_prompt_suite \
  runner.tests.test_bench_common \
  runner.tests.test_generation_overrides.BuildChatBodyTests \
  runner.tests.test_generation_overrides.NormalizeGenerationOverridesTests \
  runner.tests.test_generation_overrides.RunBenchProfileArgTests \
  runner.tests.test_generation_overrides.RunFixtureSuiteReasoningTests \
  runner.tests.test_generation_policy.PolicyConfigCoverageTests
```

Full discovery was not run: HTTP/loopback service tests, live model/endpoint
acceptance and Swift/Metal builds are outside this model-/service-free scope.
No existing tests were changed to invent live successes or hide failures.

### Setup issues resolved without network or source changes

`uv sync --locked --offline` could not find the transformers5.15.0 wheel in the
local cache; its exit1 was retained as a setup limitation, not a passing sync.
Instead, matching `pyproject.toml`/`uv.lock` were verified against the existing
cache-off preparation environment. Its installed site-packages were copied
read-only into this new worktree's isolated `.venv` (no shared writes or package
downloads). CPython3.12.13, all **36 installed distribution versions** against
`uv.lock`, and all four direct dependencies were checked. Final tests explicitly
use that isolated environment with `--no-sync`; manifests and lockfiles did not
change. The incomplete initial environment was not deleted.

The initial scratch sandbox denied all Xcode executables, which also blocked
macOS's `/usr/bin/python3` and Git shims. The scratch-only policy was narrowed to
actual Swift/compiler/inference executables; model-read, protected-write and
network denials remained. The first inventory invocation consequently had a Git
shim error; the subsequent unchanged-test invocation reached the genuine
single-file inventory failure recorded above. These were setup-policy issues,
not config, runner or model failures.

## Live boundary for the parent

Commit/review this updated config identity before any attempt. The historical
model-free config-prep commit neither staged nor checked the model directory.
Parent has since staged and locally verified the pinned files/containers; the
parent addendum below is the evidence. Before loading, recheck current
source/build identity, fresh sustained resource admission, owner/port8029 absence,
swap trend and the existing 10-GiB disk floor.
Later authorized canonical acceptance must use **`--skip-cache` only**, not
`--skip-context`; keep exact-context/cap+1, native tools both ways and all other
non-cache probes. Preserve unchanged sanity and 4.0 tok/s speed gates. No live
admission, parsing, correctness, speed or full-battery outcome is claimed here.
Installed Hermes profiles were not changed; review the served-model mapping
before any coding stage. No result edits, official-retirement path access,
model/server/endpoint, staging/download of weights, cache cleanup, CoCore
invocation, push or public activity is part of the isolated config-prep commit.

## Sources

[1] https://huggingface.co/api/models/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/revision/b5552f7f7e597e2ca02653f89098dea86b8818af
[2] https://huggingface.co/api/models/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/tree/b5552f7f7e597e2ca02653f89098dea86b8818af?recursive=true&expand=true
[3] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/config.json
[4] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/README.md
[5] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/generation_config.json
[6] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/optiq/metadata.json
[7] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/model.safetensors.index.json
[8] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/kv_config.json
[9] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/tokenizer_config.json
[10] https://huggingface.co/mlx-community/LFM2.5-24B-A2B-OptiQ-4bit/resolve/b5552f7f7e597e2ca02653f89098dea86b8818af/chat_template.jinja

## Parent local-staging verification addendum — 2026-10-16

The pinned public snapshot was staged after the model-free config-preparation
commit at `/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-OptiQ-4bit`.
The companion sidecar is
`/Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-OptiQ-4bit.provenance.json`;
the exact same 5,347-byte manifest is committed as
`local-staging-verification.json` (SHA-256
`664f52331286087bf3057ecfc0b09374bf57d5a8ecf9fbdd5121d4dc7079a93a`).

Parent recorded all 15 pinned files (16 tree entries) with API-matching sizes and
SHA-256/LFS object digests. Four shards total 16,672,710,010 bytes; local
safetensors headers and every tensor offset passed bounds checks, and the index's
16,672,595,968-byte payload matched. The config contains identical 4/8-bit
quantization maps. The manifest records no incomplete downloads and a
`staged_at_utc` of `2026-10-16T13:33:07.027633+00:00`. No tensor dtype/alignment
compatibility, model loading, endpoint, resource admission, speed, or tool parsing
was tested; those remain live gates. The staged integrity result does not imply
loadability or a benchmark pass. This follow-up checks the committed manifest
against the parent's supplied digest and pinned remote expectations only; it
does not reopen the staged model or independently rehash current weight files.

## Post-staging follow-up offline verification

Evidence root:
`/Users/tijs/.hermes/cache/scratch/lfm25-optiq-post-staging-20261016-ejtlglz8/`.
The local manifest's 5,347 bytes match the parent's supplied SHA-256 exactly.
`source-provenance.json` remains the original remote-only document, unchanged at
SHA-256 `010347c5b824ad0d71d53e1dc42c47a1420c02cf86dc5c2597b9825c36c6f07f`.
The stale config statement about no staged files was replaced with explicit
historical-preparation/later-parent-staging boundaries; execution settings and
the raw launch command remain unchanged from the cache-off predecessor except
the previously authorized model directory and served/model IDs.

- Exact closed-inventory regression plus the two LFM setup modules: **26/26
  passed**, 0 failures/errors/skips, exit 0, **3.614s**
  (`exact-config-setup-tests-verified.log` and `.json`).
- The same focused offline selection listed above: **124/124 passed**, 0
  failures/errors/skips, exit 0, **10.741s**
  (`focused-offline-tests-verified.log` and `.json`). Both Python audits recorded
  **zero socket attempts**; the outer OS sandbox denied network for descendants.
- Scope readback: all **134 baseline config files (125 YAML)** are byte-identical;
  all **2,866 protected worktree files**, including **2,452 result files**, retain
  their bytes/modes/mtimes. No generated build/cache directories appeared outside
  the existing `.venv` (`scope-before-commit.json`). Shell parse checks for both
  Mei wrappers and `git diff --check` returned exit 0.

Both invocations used the existing read-only `.venv` (CPython 3.12.13; all 36
installed distribution versions match `uv.lock`), task-local `TMPDIR` and uv
cache, and `uv run --locked --offline --no-sync python -B`. No dependency sync,
download or build ran. `offline-strict.sb` allows writes only inside this task's
scratch root (plus terminal/null devices), denies real model/runtime and installed
profile reads, and denies real compiler/inference/CoCore execution. Only explicit
metadata fixtures, inert shell recorders and existing orchestration mocks run.

Initial broader attempts retained 5 then 1 sandbox-setup failures, not config or
model failures (`focused-offline-tests.log`, `focused-offline-tests-final.log`).
Metadata-only traversal of the three scratch ancestors resolved fixture `mkdir`
denials. Apple's Bash 3.2 ignores `TMPDIR` for heredoc temporaries; rather than
permit system-temp writes or change repository code, the scratch-only test runner
uses task `TMPDIR` as its working directory and the sandbox hides Bash's four
system-temp candidates, forcing its `.` fallback into that same task directory.
Repository/Git paths in the selection remain absolute. The real legacy-flag test
and both full selections then passed without relaxing network/model/profile or
protected-write boundaries. Mocked child-sandbox warnings do not mean a real
agent was started or the outer sandbox was removed.

The exact setup selection was:

```bash
export E=/Users/tijs/.hermes/cache/scratch/lfm25-optiq-post-staging-20261016-ejtlglz8
export TMPDIR="$E/tmp" PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
export UV_PROJECT_ENVIRONMENT="$PWD/.venv" UV_PYTHON_DOWNLOADS=never UV_NO_PROGRESS=1
export UV_CACHE_DIR="$E/uv-cache" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export SANDBOX_POLICY="$E/offline-strict.sb"
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
EXPECTED_TEST_COUNT=26 EVIDENCE_SUMMARY="$E/exact-config-setup-tests-verified.json" \
  sandbox-exec -f "$SANDBOX_POLICY" uv run --locked --offline --no-sync python -B \
  "$E/offline_unittest.py" \
  runner.tests.test_start_mei_server_sh.MeiConfigDryRunTests.test_all_other_configs_are_byte_identical_to_immutable_candidate3 \
  runner.tests.test_lfm25_setup runner.tests.test_lfm25_optiq_setup
```

The 124-test run used the identical environment and command prefix, with
`EXPECTED_TEST_COUNT=124`, `focused-offline-tests-verified.json` as its summary
path, and the exact twelve focused targets listed in the historical section.
Reports refuse to overwrite earlier evidence; use fresh output names on a rerun.
These results verify config/documentary contracts, not live loadability, resource
admission, tool parsing or speed. No model load, endpoint, benchmark, staged-model
modification, installed profile operation, result edit, cache cleanup, CoCore,
network request, push or public activity was performed by this follow-up.

# LFM2.5-24B-A2B community OptiQ — model-free speed-gate preparation

**Prepared only. Loadability, speed, resource safety and native tool parsing are
unverified for this artifact.** This is a distinct community OptiQ variant of
`LiquidAI/LFM2.5-24B-A2B`, not a Liquid-official quant.[1][4][6]

## Pinned identity and provenance

- Benchmark base: `83d06b3978210b850c42e61e09d28c240a86d7e5`.
- Local worktree: `/Users/tijs/projects/local-model-bench-lfm25-optiq-speed-gate`.
- Local branch: `work/lfm25-optiq-speed-gate-20261016`.
- Config: `configs/LiquidAI-LFM2.5-24B-A2B-OptiQ-4bit/mei.yaml`.
- Config SHA-256: `f67f1ad43f6e42781d099e7479a1336bd4efd0e72c86d770c132ce22dc46d2d2`;
  short config hash **`f67f1ad43f6e`**.
- Artifact: `mlx-community/LFM2.5-24B-A2B-OptiQ-4bit`, immutable revision
  `b5552f7f7e597e2ca02653f89098dea86b8818af`.[1]
- Mei source: `faf48a331b6bede352c334e0c6e3d4d4d7e10372`;
  effective vMLX: `22969e9555b5e86df862e43e3d7356575d3dd053`.
  These existing local source HEADs were read back clean, not built or executed.
  `mei_source_commit` names Mei; `mei_commit` names vMLX.

`source-provenance.json` records the complete pinned remote tree, parsed model
config including both quantization maps, remote LFS expectations, index summary,
generation/KV/tokenizer metadata, and retrieval byte hashes/URLs/timestamps.
It is **not a staging or local-integrity manifest**. Ten GETs retrieved only
small public metadata/sidecars; no weight URL, weight data, local model directory
or Hugging Face weight cache was accessed.

### Exact remote inventory

The revision's recursive tree has **16 entries: 15 files and the `optiq/`
directory**; all files total **16,690,854,530 bytes**. Its four safetensors files
total **16,672,710,010 bytes**, distinct from the index's tensor payload
**16,672,595,968 bytes** (946 indexed tensors). Remote LFS SHA-256 values below
are expected checksums, not locally measured weight hashes.[2][7]

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
maps. Mocked prompt/acceptance tests preserve budgets, context, identity,
`--skip-cache`-only behavior and failed-probe status. Mocks are fixtures, never
benchmark results.

Evidence root: `/Users/tijs/.hermes/cache/scratch/lfm25-optiq-speed-gate-prep-20261016/`.
All tests use task-scoped `TMPDIR`, an isolated local CPython3.12.13 environment,
`uv --locked --offline --no-sync`, and a macOS network-denying sandbox. Python
audit hooks additionally deny/record socket operations. The sandbox also denies
real model/HF weight reads, protected checkout/results/runtime/profile writes,
and real inference/Swift execution; only metadata fixtures/inert recorders run.

## Executed checks and preservation

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

Commit/review this config identity before any attempt. This preparation neither
stages nor checks whether the new model directory exists. Parent must verify
staged containers, exact remote SHA-256/bytes/shard set and sidecars separately;
recheck current source/build identity, fresh sustained resource admission, owner/
port8029 absence, swap trend and the existing 10-GiB disk floor before loading.
Later authorized canonical acceptance must use **`--skip-cache` only**, not
`--skip-context`; keep exact-context/cap+1, native tools both ways and all other
non-cache probes. Preserve unchanged sanity and 4.0 tok/s speed gates. No live
admission, parsing, correctness, speed or full-battery outcome is claimed here.
Installed Hermes profiles were not changed; review the served-model mapping
before any coding stage. No result edits, official-retirement path access,
model/server/endpoint, staging/download of weights, cache cleanup, CoCore
invocation, push or public activity is part of this preparation.

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

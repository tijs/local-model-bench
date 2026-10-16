# LFM2.5-24B cache-off revalidation — model-free local preparation

**Prepared only, not live-admitted and not a performance fix.** The new
`mei-cache-off-revalidation.yaml` recovers candidate 3's actual cache-off
execution vector on the current Mei source. Existing `mei.yaml` remains the
cache-enabled candidate-4 config; no historical config, task, result or gate
was changed.

## Exact identity

- Worktree: `/Users/tijs/projects/local-model-bench-lfm25-cache-off-revalidation`.
- Branch: `work/lfm25-cache-off-revalidation-20261016` (local only).
- Benchmark base: `81daaf5150d75bef09284531b567d891adf7b818`.
- New file: `configs/LiquidAI-LFM2.5-24B-A2B-MLX-4bit/mei-cache-off-revalidation.yaml`.
- New config SHA-256:
  `e6be308f5709d4a0ef3a49cc158b50d44bd9c2047a8a47594873c038c3f1babb`.
- New short config hash: **`e6be308f5709`**.
- Immutable candidate-3 benchmark commit:
  `0b68ce2d960e8d6754a52ea780c8fec2c57cde3c`.
- Candidate-3 config SHA-256:
  `63f2b2fa27ffbc18a895ae7bde8561f9f26bcf0fd4d2be2caaf2116b4976386d`
  (hash `63f2b2fa27ff`).
- Current Mei source, including the configured `--mei-repo` checkout:
  `faf48a331b6bede352c334e0c6e3d4d4d7e10372`, clean.
- Effective local vMLX: `22969e9555b5e86df862e43e3d7356575d3dd053`, clean.
  `mei_commit` names this dependency; `mei_source_commit` names Mei itself.
- Official artifact: `LiquidAI/LFM2.5-24B-A2B-MLX-4bit` at
  `667408d494bde191c2cb9dd4f4549827816b9275`; full-precision source provenance
  `1769516ac588c4c558089c94f27d96b0dc67b183`. No model substitution.

The parsed fields changed from candidate 3 are **only** `mei_source_commit`,
`settings`, and `known_gaps`. Every other parsed field, including the complete
launch-command string, is identical. Comments also label this new identity as
cache-off revalidation and remove stale/current-build ambiguity. Runtime tuning
remains `experimental-unmeasured`.

Read-only current artifact verification found the existing configured release
binary to be 92,421,408 bytes, SHA-256
`e6945ebb20ff95ed8c4e4baf6bce51e4463ac8c9b74c2ff97d1aae54a6916888`;
packaged metallib 2,422,136 bytes, SHA-256
`0f6bdc29ff9afb81369eb5ca6f6561e0fdbb63228db0d4520c91e3c281738da3`.
Neither binary was executed or rebuilt. This is artifact identity, not fresh
loadability evidence.

## Exact launch comparison

The canonical `run_mei_acceptance.split_launch_command` parsed both configs.
Their **46-token wrapper argv** are exactly equal, with no path substitution
or normalization. Three actual wrapper `--dry-run` invocations each exited 0:

1. Immutable candidate-3 config through its immutable original wrapper,
   extracted from Git into scratch.
2. The same immutable config through the current base wrapper.
3. The new revalidation config through the current base wrapper.

All emitted the same **37-token launch vector**, also exactly matching the
historical actual dry-run printed in candidate-3 `VERIFICATION.md`:

```text
env VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 /Users/tijs/projects/mei-lfm25/.build/release/mei --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/LFM2.5-24B-A2B-MLX-4bit --served-model-id LiquidAI/LFM2.5-24B-A2B-MLX-4bit --host 127.0.0.1 --port 8029 --context-cap 65536 --temperature 0.1 --top-p 0 --top-k 50 --emit-reasoning true --cache-reuse false --max-tokens 4096 --prefill-step-size 1024 --min-p 0 --repetition-penalty 1.05 --model-profile lfm2.5-24b-a2b --memory-limit-bytes 32000000000 --load-mmap false
```

**This printed vector was not executed.** No `--max-cache-blocks` flag or
`max_cache_blocks` metadata is present. No KV/disk tier, cache-limit, anchors,
seed or thinking override is added. Fusion-cache 0 is the wrapper's child-only
environment assignment, not a Mei flag or global export. Runtime, source,
build and vMLX selection paths are exactly candidate 3's paths. The real
revision-checked local-vMLX guard ran read-only and printed SwiftPM editable
selection **not applied**; no helper stub was used for these three dry-runs.

The vendor sampler remains temperature 0.1 / top-p 0 / top-k 50 / min-p 0 /
repetition penalty 1.05; context 65,536, output 4,096, prefill 1,024,
allocator 32,000,000,000 bytes, mmap false and Hermes Ops connect timeout 300
are unchanged. There is no invented reasoning effort. The unchanged
`orchestration.viable: full` is eligibility metadata, not a safety/admission
verdict. The 4.0 tok/s speed gate, normal sanity gate and all task budgets remain.

## Executed offline checks and actual outcomes

Evidence root (outside Git and outside benchmark results):

`/Users/tijs/.hermes/cache/scratch/lfm25-cache-off-revalidation-prep/`

All final validation/test commands used:

```bash
# Run from the new worktree. E is the evidence root above.
E=/Users/tijs/.hermes/cache/scratch/lfm25-cache-off-revalidation-prep
export TMPDIR="$E/tmp" PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
export UV_PROJECT_ENVIRONMENT="$PWD/.venv" UV_PYTHON_DOWNLOADS=never UV_NO_PROGRESS=1
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
```

- `sandbox-exec -f "$E/offline.sb" uv sync --locked --offline`:
  **exit 0**; isolated CPython 3.12.13 environment, 36 packages installed from
  local cache, no manifest/lockfile changes.
- `sandbox-exec -f "$E/offline.sb" uv run --locked --offline python "$E/verify_cache_off.py"`:
  **exit 0**; exact config/source contracts, vendor generation normalization,
  runtime/profile resolution, unchanged full task inventory and three actual
  dry-runs passed. `config-validation.json` records the complete vectors,
  exit codes, hashes and assertions. All **132 pre-existing config files**
  (**124 YAML files**) are byte-identical to the base.
- Existing focused offline selection below: **117 tests run, 116 passed,
  1 failed, 0 errors, 0 skips; exit 1; zero network attempts**. This is
  deliberately not reported as an all-green suite.
- Additional new-config-specific scratch tests:
  `sandbox-exec -f "$E/offline.sb" uv run --locked --offline python "$E/offline_unittest.py" test_cache_off_revalidation`:
  **7/7 passed, 0 errors/failures/skips; exit 0; zero network attempts**.
  These cover full predecessor equality/current source, exact add-only config
  inventory, cache-off controls/flag omission, sampler/profile/runtime, real
  canonical prompt-config parsing with a zero-task scratch suite, mocked
  acceptance forwarding `--skip-cache` without `--skip-context` while preserving
  a failing probe status, and explicit fresh-resource-gate/evidence boundaries.
  Mock outcomes are fixtures only, never real benchmark results.
- `bash -n runner/start_mei_server.sh runner/stop_mei_server.sh`: **exit 0**.
- Git whitespace checks: **exit 0**.
- Protected-state before/after verification: **exit 0**,
  `PROTECTED_STATE_UNCHANGED=true`.

The exact existing focused command was:

```bash
EVIDENCE_SUMMARY="$E/benchmark-focused-tests.json" \
  sandbox-exec -f "$E/offline.sb" uv run --locked --offline python \
  "$E/offline_unittest.py" \
  runner.tests.test_start_mei_server_sh \
  runner.tests.test_lfm25_setup \
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

### One existing test incompatibility — not hidden or patched

The sole failure is:

```text
runner.tests.test_start_mei_server_sh.MeiConfigDryRunTests.
  test_all_other_configs_are_byte_identical_to_immutable_candidate3
runner/tests/test_start_mei_server_sh.py:552
AssertionError: Items in the first set but not the second:
'configs/LiquidAI-LFM2.5-24B-A2B-MLX-4bit/mei-cache-off-revalidation.yaml'
Ran 117 tests in 9.342s
FAILED (failures=1)
```

That historical test requires the **entire YAML filename inventory** to equal
candidate 3's inventory and therefore rejects the explicitly requested new
filename. Its preceding byte comparisons pass. The dedicated additive-inventory
gate passes: every original config is byte-identical, with exactly the new YAML
added. No file was hidden, removed, renamed to evade the glob, or test assertion
weakened. Updating that existing test is outside this config/documentation-only
scope. This remains a test-suite blocker, not an argv or config-validation failure.

Full discovery, loopback-server tests, Swift/Metal tests, live acceptance,
benchmark tasks and inference were not run. Existing offline launch tests use
metadata-only fixtures or inert shell recorders, not real Swift or Mei engines.
The OS sandbox denies network, weight reads, real inference/CoCore executables
outside scratch, and writes to protected worktrees/runtime/model/evidence/profile
paths and this new worktree's results. Python audit hooks record and deny socket
connect/bind/DNS operations; both test reports and the config report contain
zero attempts.

### Setup issues retained as evidence

- The first worktree checkout was blocked by the protection on the *new*
  results directory. Git rolled back that incomplete checkout and retained the
  newly created branch. A local checkout of the same branch under a
  network-denying creation sandbox succeeded; the stricter read-only results
  policy was then used for validation/tests. No parent/result/evidence cleanup
  or branch/history rewrite was performed.
- The inherited `UV_PROJECT_ENVIRONMENT` initially selected the primary
  checkout's already-synchronized environment (36 packages checked, no installs).
  This was detected before validation/tests; every final command explicitly
  selects the new worktree's `.venv`, and clears inherited Python/virtualenv
  variables. The explicit isolated offline sync installed 36 cached packages.
- The initial scratch validator incorrectly compared a raw YAML command's
  trailing newline against `server_command()`, which intentionally strips it.
  That scratch-only assertion was corrected to compare both runner-resolved
  commands and exact token vectors, while retaining the separate raw-command
  equality check against candidate 3. `config-validation.log` retains the
  initial assertion failure; `config-validation-rerun.log` records the passing
  run. No repository config or runner fix was needed.

## Preservation and live boundary

Before creating the worktree, workspace/repository `AGENTS.md`, full statuses,
base/source commits and read-only Kiem state were inspected. Protected manifests
include HEAD/branch/full status, tracked/nonignored file bytes/modes/mtimes and
**all** result files, including ignored files. The before/after audit confirms:

- Results-dirty parent `/Users/tijs/projects/local-model-bench-lfm25`:
  **2,502 result files**, original dirty status and all inventoried files unchanged.
- Primary benchmark checkout, candidate-3 and candidate-4 checkouts and current
  Mei/vMLX source checkouts: inventoried bytes/metadata and Git state unchanged.
- Historical/selected runtime trees and existing LFM live-evidence bundles:
  inventoried bytes/metadata unchanged; existing build-artifact hashes unchanged.
- Model directory file metadata unchanged; weights were not opened. No original
  cache/evidence was deleted. New worktree changes are only this document and
  the new config. No service or installed profile was modified.

Read-only process/listener inspection after testing found no exact inference or
CoCore executable owners and no port-8029 listener. No endpoint request was made.
This is **not** a resource gate or permission to load.

The parent reports candidate 3's prior 40-turn chain failed task convergence after
repeated unavailable mock-tool calls, at about 14.94 GB peak. Candidate 4 passed
full admission but its chain was resource-stopped at 16% system free memory /
Mei peak 21.529 GB, with swap subsequently elevated and declining. Those records
are preserved, not reclassified as successful tasks. Recovering the historical
cache-off vector on newer source is not evidence of a memory or performance fix.

**Keep the model unloaded until a new 11-sample sustained resource gate passes.**
Review swap recovery, clean owners/port and the existing 10-GiB disk floor;
never force a reset or delete caches/evidence. Any later authorized admission
must use `--skip-cache` only, retain exact context and all non-cache probes, then
review bounded unchanged-task/resource behavior before considering the canonical
25-task battery. No fresh resource gate or live admission was performed here.
CoCore remains untouched. Everything is local and unpushed.

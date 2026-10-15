# Model-free verification — 2026-10-15

No model download, staging, inference-server launch, canary, or benchmark was
performed. No global/named Hermes profile state was written. Existing results,
tasks, fixtures, checks and ledger pins were preserved.

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

## Executed checks

In the respective isolated worktree roots:

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

## Remaining gates

Profile provisioning/readback, release binary/metallib identity, approved pinned
model staging/integrity, clean disk/memory admission, text/SSE/tools/reasoning/
cache/context canaries, and a real full 25-row battery plus teardown/provenance
audit remain unperformed. Vendor sampler and 4096/65536 output/context policy are
unchanged. No further storage cleanup is authorized or needed for this task.

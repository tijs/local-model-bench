# Flint / Mei native admission and full-run preparation

**Native admission: PASSED, 12/12. Full benchmark: PENDING; no scored rows were
added.** This archive preserves the already-completed gate; preparation did not
start a server, rerun admission, load the model, or run the canonical benchmark.

Config: [`configs/Flint-mixed-3-4bit-full-20261024/mei.yaml`](../../configs/Flint-mixed-3-4bit-full-20261024/mei.yaml).
It is `viable: full`, routes coding through `bench-mei`, requests the exact served
ID, and remains rank-eligible under the normal completeness/scoring rules.

## Identity and build

- Artifact: `mlx-community/flint-mixed-3-4bit@b1c305855ae7c3464813815be4dbd544b22c36aa`.
  The community card names **RecursiveSI/flint-int4** as conversion parent;
  the separate upstream base/architecture pin is
  `RecursiveSI/flint@2a247be0c0aec895ccb0ac7ca92229ec6df37288`.
- Exact published tree: **16 files, 17,848,888,635 bytes**. Four safetensors
  shards: **17,837,740,282 bytes**; index tensor payload: **17,837,530,688 bytes**.
  Mei verifier: `ok=true`, `model_type=flint`; 4-bit base/group 64 with per-layer
  3-bit routed-expert overrides. All 16 whole-file hashes/sizes match the
  pre-admission staging report in the fresh post-admission integrity check.
  Local `.cache/huggingface/` download metadata is enumerated separately and
  excluded from published-tree counts; no weights were modified or copied here.
- Mei: `c9b6013958cbc838b156b717f3b49a0045f84064`, clean isolated checkout
  `/Users/tijs/projects/mei-flint-20261023`.
  vmlx: `633fe166630ef04310aea7d5a1795555ab32970d`, clean checkout in the isolated
  build; vendored MLX **0.32.2**.
- Build: `/Users/tijs/.local/share/local-model-bench/mei-build-flint-full-20261024`.
  Gated `release/mei`: **92,750,736 bytes**, SHA-256
  `c6dea15433512b9c488eab026858946a1d9d3347055848c4faeefd1086ee54bd`.
  Consumer Cmlx `release/mlx-swift_Cmlx.bundle/Contents/Resources/default.metallib`:
  **2,422,136 bytes**, SHA-256
  `0f6bdc29ff9afb81369eb5ca6f6561e0fdbb63228db0d4520c91e3c281738da3`.
  Colocated `mlx.metallib` and `default.metallib` match that library byte-for-byte.
  The old prebuilt Release binary in `mei-build-flint-c9-20261023` was **not** used.
  Only provenance/logs are archived, never executable/library/model payloads.
- Runtime: `/Users/tijs/.local/share/local-model-bench/mei-runtime/flint-gate-20261024`.
  The canonical wrapper **builds on launch**; it is not a prebuilt/no-build mode.
  Parent must retain/recheck these clean source pins and artifact identity.

## Observed admission, not benchmark scores

[`native/probe.json`](native/probe.json) records all 12 probes passing: exact
`/v1/models` identity and status, plain chat completion, native nonstreaming and
streaming `add_numbers` calls with numeric arguments, stream/nonstream visible
output and token-count parity, repeated/growing-turn cache reuse, and exact
context-boundary behavior. The run directory ID is `native-gate-20261024T154127Z`;
its raw probe epochs correspond to **2026-10-24 19:12:31.945557–19:29:20.776056 UTC**.
The directory label and raw timestamps are preserved rather than normalized.

- Repeated prompt: **6,160 cached tokens**; growing-turn slot: **779**.
- **65,536 prompt tokens + 1 completion token accepted**, prefill
  **824,411.5099906921 ms**, peak **25,868,095,082 bytes**.
- **65,537 prompt tokens rejected with HTTP 400**.
- Device: `applegpu_g13s`, **34,359,738,368 bytes (32 GiB)** unified memory.
- Server startup independently confirms context 65,536, prefill step 64 and
  max-tokens 8,192; the raw status probe does not expose the first two settings.

These are bounded native/API admission observations, not coding-suite quality,
speed-gate success, sustained decode benchmarks, long-output resource guarantees,
or a completed ranking result.

## Pinned operating point and limits

- Vendor sampler: temperature **1.0**, top-p **0.95**, top-k **20**, from the
  [pinned community card](https://huggingface.co/mlx-community/flint-mixed-3-4bit/blob/b1c305855ae7c3464813815be4dbd544b22c36aa/README.md)
  and [generation_config.json](https://huggingface.co/mlx-community/flint-mixed-3-4bit/blob/b1c305855ae7c3464813815be4dbd544b22c36aa/generation_config.json).
  Config applies these to the server/coding baseline and explicitly selects the
  same Hermes Ops profile; sanity retains its deterministic harness settings.
  No unsupported reasoning effort or extra vendor sampler is invented.
- Context **65,536**, generation cap **8,192** (also explicit for Hermes Ops),
  prefill step **64**, matching the gate's effective auto-profile prefill.
  The 8,192 runaway bound is a harness choice, not the card's 32,768-token example;
  the card warns of long thinking trajectories, so truncation remains possible.
- `--enable-flint true --compiled-decode false --load-mmap true`,
  `VMLX_ENABLE_UNSAFE_COMPILE=0`, `VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0`.
  Cache reuse is on with **no disk KV directory**, no allocator override, and no
  explicit model-profile/SSM-anchor/KV-quantization flags.
- `MLXPRESS` and `JANGPRESS` remain **unset**. Pinned `Engine.swift` passes
  `jangPress: .default`; preserve its normal file-backed/automatic policy rather
  than disabling it. This routed bundle exceeds half of physical memory, so an
  automatic tier may activate, but **actual tier engagement is not established
  by these logs**. Observe/log the actual full run; do not claim activation.
- Fresh header-only audit: **1,751 tensors**, **46 naturally unaligned**, totaling
  **1,616,510,976 bytes**, all in shard 4. The raw server log reports those exact
  tensor-copy counts. Its separate coarse “3 of 4 shards” alignment warning is
  not a per-tensor copy estimate. No aligned duplicate was created. The archived
  audit explicitly labels itself a fresh post-admission re-audit, not the original pre-load audit JSON.
- Transformers warned about the custom/unknown `flint` type. The extra local
  `apply_chat_template` audit **could not run because jinja2 is absent** in the
  locked environment; its `parity:false` artifact is retained, not relabeled a
  native-gate failure or a parity pass. **Do not install/change the lockfile.**
  The separate raw `/v1/completions` check passed at **1 local token = 1 server
  token**; actual chat/plain/tool/stream probes passed. This is not full local
  chat-template parity or broader tool-schema convergence evidence.
- Historical staging reports still say “loadability NOT CHECKED (GPU-gated)”:
  that was their truthful status before admission. They are copied verbatim;
  the later probe above supersedes that status, not their recorded bytes.
- The separate bench-profile Hermes CLI route was not revalidated during this
  preparation. Parent owns provider/live-CLI verification before coding, fresh
  resource/owner checks, the full run, and teardown. No profile/Kiem plan changed.

## One authorized full run (not executed here)

The user's **disk-floor-only, one-run** waiver must not create a diagnostic or
ranking veto. The committed literal authorization is accompanied by
`rank_eligible: true`, with no forced/exploratory flags. The normal **10 GiB**
floor and all other gates remain unchanged. The canonical runner must append
its own measured prelaunch audit (free bytes, floor, shortfall, immutable config
identity, ranking eligibility). Above floor it must record **zero shortfall** and
**`disk_gate_overridden:false`**. Historical clean-window samples and the
preparation receipt are not that future launch audit and do not consume consent.

**Set `MEI_RUNTIME_BASE` on the `run_bench.py` process itself**, not just its
server child, so stop scripts target the isolated runtime. The config also
passes that exact `--runtime-base` and pins `MEI_VMLX_CHECKOUT` under its build.
After reviewing/committing this config, parent may use the single authorized
invocation from the repository root:

```sh
env -u MLXPRESS -u JANGPRESS \
  MEI_RUNTIME_BASE=/Users/tijs/.local/share/local-model-bench/mei-runtime/flint-gate-20261024 \
  uv run --locked python runner/run_bench.py \
  --config configs/Flint-mixed-3-4bit-full-20261024/mei.yaml \
  --allow-disk-floor-override --stage all
```

No sweep, retry, coding-only waiver, PR, or other publication is authorized by
this command. At preparation verification, port 8024 was free, the runtime PID
file was absent, and the exact canonical log path
`/tmp/bench_Flint-mixed-3-4bit-full-20261024_mei_server.log` was absent. Recheck
immediately before launch; the unique slug prevents overwriting an older log.

## Evidence index and preparation verification

| Evidence | Purpose |
| --- | --- |
| [archive-manifest.json](archive-manifest.json) | Original absolute source paths, exact sizes/SHA-256 for 16 verbatim small-file copies |
| [native/probe.json](native/probe.json), [probe-runner.log](native/probe-runner.log) | Raw admission results, responses, timings and tokenizer warnings |
| [launcher.log](native/launcher.log), [server.log](native/server.log), [launch-provenance.txt](native/launch-provenance.txt) | Actual gated build/runtime/model/flag selection and startup observations |
| [raw short parity](native/tokenizer-raw-short-parity.json), [unavailable local chat-template audit](native/tokenizer-short-parity.json) | Separate passing raw-token check and preserved Jinja limitation |
| [tree manifest](staging/tree-manifest-verified.json), [staging verification](staging/staging-verification-20261024.json), [original sidecar](staging/flint-mixed-3-4bit.provenance.json) | Exact pinned tree, pre-admission per-file hashes and Mei verifier report |
| [post-admission integrity](staging/post-admission-integrity.json), [alignment audit](staging/alignment-audit.json) | Fresh read-only whole-file identity comparison and dtype-aware header audit |
| [staging supervisor](staging/staging-supervisor-result-20261024.json), [disk samples](staging/staging-disk-samples-20261024.jsonl), [worker log](staging/staging-worker-20261024.log) | Historical staging process/disk evidence, not a new floor policy |
| [clean window](resources/clean-window-20261024.json) | Twelve historical passing resource/owner/port samples; swap did not grow |
| [runtime provenance](build/runtime-provenance.json), [metallib sidecar](build/mlx.metallib.provenance), [build log](build/build.log) | Actual binary/Cmlx hashes, pinned clean sources and build chain |
| [verification receipt](validation/verification.json), [wrapper dry-run](validation/wrapper-dry-run.log), [focused tests](validation/focused-tests.log) | Locked preparation checks, exact emitted argv, safety assertions and 45 passing tests |
| [evidence inventory](evidence-inventory.json) | Hash/size inventory of every other archive file and the exact config |

Preparation used the worktree's Python 3.12 locked environment with
`uv run --locked --offline --no-sync`; no dependency install or lockfile change.
YAML identity/ranking/sampler checks passed. The **exact config's wrapper
`--dry-run` exited 0** and matched the complete expected argv, including mmap,
Flint, safe compilation controls, prefill and sampling. It did not bind a port,
build, or change the existing build/runtime artifacts. **45 focused tests
passed, 0 failures/errors/skips**, across launcher forwarding, authorized disk
waivers, pure generation-body/validation helpers and config workflow checks.
Server-backed tests were not selected. A macOS sandbox denied network, writes
outside task scratch, and inference/Swift/Metal execution; Python's network audit
recorded **0 attempts**. All **2,671 protected existing files** retained their
bytes/modes/mtimes and results/runner inventories remained unchanged. Raw logs
retain their original whitespace; do not rewrite evidence to satisfy a linter.

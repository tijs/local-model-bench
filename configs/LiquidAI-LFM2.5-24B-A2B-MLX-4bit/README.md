# LFM2.5 setup and remaining live gates

This lane uses the official MLX artifact at
`667408d494bde191c2cb9dd4f4549827816b9275` (source model revision
`1769516ac588c4c558089c94f27d96b0dc67b183`). Model-free tests do **not**
establish loadability, tool correctness, useful speed, or benchmark results.
No model or Hermes profile is installed by these tests.

## Current memory-relief candidate: fusion cache off (experimental/unmeasured)

The only execution change from **`e4f67e0554e2`** is
**`--fused-gate-up-cache-limit-bytes 0`** in this LFM config's launch command.
Matching top-level `fused_gate_up_cache_limit_bytes: 0` is provenance metadata,
not an automatic override. The wrapper translates the CLI option into:

```text
env VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 /Users/tijs/projects/mei-lfm25/.build/release/mei
```

This is the start of the exact launch vector printed in both `--dry-run` and
startup output, followed by the unchanged Mei flags. The assignment applies
**only to the Mei executable**, not SwiftPM, source-selection/metallib helpers,
the caller's environment, or any other config. The optional wrapper argument
is **not a Mei CLI flag**. Omitting it preserves the original launch and any
inherited environment; no default is injected or cleared. Existing configs
that already use outer `env` assignments retain those assignments unchanged.

The wrapper accepts only nonnegative decimal integers, **including zero**,
within Swift's signed 64-bit `Int` range (`0..9223372036854775807`). Missing,
empty, signed, fractional, boolean/null-like, whitespace, shell-expression and
overflow values fail closed before build or launch. Leading zeros are accepted
and forwarded literally. Do not confuse this per-layer fusion cache with
`--cache-limit-bytes` (MLX buffer pool) or KV/prefix reuse.

Pinned vMLX `SwitchLayers.swift:291-369` lazily concatenates and retains
quantized gate/up weights/scales/biases on first forward. Its default is
**512 MiB per layer**, not a global memory bound; zero skips every nonempty
concat cache. `LFM2MoE.swift:293-298` constructs `SwitchGLU` with default fusion
enabled. Both sources are at `22969e9555b5e86df862e43e3d7356575d3dd053`.
Avoiding retained duplicate banks is a source-backed hypothesis, **not measured
memory savings, a safe fix, numerical/tool parity, or a speedup**; unfused
projections may reduce decode speed.

Config identity is now **`137b34e01f9f`**; keep it separate from e4 and every
earlier partial attempt. Prefill **512**, allocator **32000000000 bytes**,
cache reuse **true**, **mmap=false**, vendor sampler, context/output/connect
budgets and all source/build/runtime/artifact pins remain unchanged. No model
or server is launched and no endpoint, acceptance or benchmark is run by this
follow-up. A future authorized load still requires a fresh sustained resource
gate, bounded native admission and isolated chain-task/resource review before
considering the full battery. See `VERIFICATION.md` for executed offline checks.

## Inherited prefill/allocator candidate (unchanged)

`mei.yaml` now explicitly requests **`--prefill-step-size 512`** and
**`--memory-limit-bytes 32000000000`**. Top-level `prefill_step_size`,
`memory_limit_bytes` and `runtime_tuning_status: experimental-unmeasured` are
matching provenance metadata, not automatic launch overrides: the flags in
`benchmark_launch_command` are what Mei receives. **Neither value is proven
safe or optimal for this LFM model.** This is runtime tuning, not a new vendor
sampling lane or a performance result.

The connect-only baseline was config **`a4be8e840181`**, benchmark commit
**`8e17e3a33ec8b66b12808c35d4d6368f1bd8cfdb`**. The parent reports that its
retry wrote **3 rows**: sanity **2/2** and `hermes_ops-selection` passed at
**142.058s**, **40,899 prompt / 134 completion tokens**, **0.94 end-to-end tok/s**.
This confirms the connect fix for selection, not pure decode speed or full
recovery. `hermes_ops-chaining` stayed in flight for about 15 minutes with no
result row; the parent intentionally stopped for resource pressure. Last
successful status reported **28.712 GiB active peak** versus **24.96 GiB
recommended / 32 GiB physical**, with active + queued generations; swap reached
**3.319 GiB** and disk **16.022 GiB**. Teardown freed the port and pressure
recovered. Preserve its bundle unchanged:

```text
/Users/tijs/.local/share/local-model-bench/results-mei/LiquidAI/LFM2.5-24B-A2B-MLX-4bit/full-run-20261015T170436Z-connect300-resource-stop/
```

The baseline used the profile's **unmeasured generic prefill 64** and the
loader's effective default allocator limit, about **22.4 GiB**. Pinned Mei
`Engine.swift` reapplies explicit memory limits after loading, and
`docs/BENCHMARKING.md` warns that allocations can wait when a limit sits below
the working set. That is a plausible investigation direction, **not proof of
the chaining stall's cause**. `docs/MODELS.md` uses prefill 512 / explicit limits
for other models, not LFM-specific evidence.

The candidate **32000000000 bytes = 32e9 bytes, about 29.802 GiB**, above the
observed 28.712 GiB peak but below **34359738368 bytes (32 GiB)** physical RAM.
It is **not 32 GiB**, a total-system/process cap, or a guarantee of OS/runtime
headroom. Larger prefill chunks can increase peak memory or alter output;
raising both knobs can worsen pressure and cannot attribute a benefit to one.
The source/model profile and wrapper defaults are unchanged. Model-free
regressions check the **exact emitted LFM argv**, independent omission of either
flag, and explicit/absent settings in every other Mei config, using only
metadata-only scratch fixtures and a stubbed local-vMLX guard.

Vendor sampler, **65536 context**, **4096 output**, connect budget **300s**,
cache reuse, **mmap=false**, runtime/build/source/artifact pins and all other
models stay unchanged. The candidate has a new config hash; never fold the
`a4be8e840181` or older `0fb346ed9077` partial rows into it. No model/server,
endpoint call, admission probe or benchmark is part of this follow-up. Before
any future authorized load: commit the candidate, pass a fresh sustained
resource gate, then bounded admission/one-task checks and review their resource
evidence **before a full retry**. No safe/optimal/speedup claim is made.

## Prior harness correction: Hermes Ops connect budget

The parent reports that the separate native admission passed **12/12** (including
full context/tools), and the first canonical attempt loaded Mei 0.9.0 with exact
identity/plain completion and **sanity 2/2**. Hermes Ops then repeatedly failed
at the **60-second pre-header/connect watchdog** with no token usage; later
server-unreachable rows followed the operator's stop. This supersedes the
earlier pending-live language in the staging/build sections below, but is **not
a complete benchmark result**. The prior attempt remains append-only under
config **`0fb346ed9077`** / runner **`edda01df84c3`**.

The baseline added **`hermes_ops_connect_timeout: 300`**, retained here. This is a
bounded client harness policy, not vendor tuning or a measured optimum. The connect
budget includes waiting for response headers, so the suite's 600-second
first-progress budget cannot help until headers arrive. The model override is
validated as positive finite numeric seconds (no bool) and forwarded only for
Hermes Ops as `--connect-timeout 300`; absent fields retain the existing
60-second client default (or a suite's own explicit connect budget). Sanity,
coding, sampling, context/cache/mmap, all other liveness/turn/task budgets and
retries are unchanged. See `configs/README.md` for precedence and validation.

That corrected config hashed to **`a4be8e840181`** and was committed before its
retry. Selection recovery is now parent-reported as described above; chaining
and the full battery remain incomplete. `VERIFICATION.md` preserves the earlier
model-free repair record separately from this unmeasured runtime candidate.

## Build selection

Run launch/dry-run commands from the benchmark worktree root. `mei.yaml` selects
sibling worktrees via `--mei-repo`, `--vmlx-repo`, and the full
`--vmlx-revision`, with a worktree-local SwiftPM scratch directory. No shared
SwiftPM mirror is changed. Mei's `scripts/use_local_vmlx.sh` checks clean Git
identity, uses the supported SwiftPM editable API, verifies the resolved graph
path, and restores the tracked public lockfile. It wraps the **actual build**,
not just a printed source label. The selected vMLX path also reaches metallib
provenance. A wrong revision or dirty tree fails before compilation/launch.

The public `633fe166` lockfile pin remains the normal Mei default. It lacks the
router fix and must not be mistaken for this lane's effective dependency.
Keep `mei_commit`, `mei_source_commit`, launch argv and provenance notes in sync
when promoting these worktrees. The release build and byte-level binary/metallib
identity are now verified in `VERIFICATION.md`; neither that build nor the
historical debug executable establishes model loadability or performance.

## Staged artifact and isolated runtime

At the earlier staging-only checkpoint the authorized pinned artifact was
**staged-complete, loadability-pending** (the staging metadata retains that
historical status; see the current parent-reported admission status above).
`staging-provenance.json` is a tracked metadata-only record of all **12 files**,
including the **3 weight shards / 13,567,294,335 bytes**, their SHA-256 matches
against pinned Hub LFS metadata, and the container/index verification. Weights
and machine-local staging sidecars remain outside Git. No model load, canary,
or benchmark result is claimed.

The read-only dtype-alignment audit found **870/870 tensors** misaligned.
`--load-mmap false` is explicit for this lane because the pinned mmap loader
would allocate aligned copies for these tensors, increasing resident-storage/
OOM risk. This is a source-backed memory-safety setting, **not vendor sampling
or a measured optimization**. Do not repack, heal or edit the official shards;
their original sizes and hashes remain the artifact identity. Exact per-shard
audit and source references are in `staging-provenance.json` / `VERIFICATION.md`.

The **11-sample sustained pre-load gate passed** at 15:31:16–15:35:48 UTC on
2026-10-15: **21.151–21.546 GiB** reclaimable (10 GiB floor), zero swap, no
inference owners and port 8029 free throughout. `preload-memory-gate.jsonl`
preserves the original metadata-only evidence verbatim. This is a past gate,
not a launch permit: **immediately recheck** memory/owners/disk/listener state
before launch. All live gates for the current runtime candidate remain pending.

`mei_runtime_base` and the launch command's `--runtime-base` both select:

```text
/Users/tijs/.local/share/local-model-bench/mei-runtime-lfm25
```

The wrapper writes `server.pid` there and build/server logs under its `logs/`.
Both `run_bench.py` stop sites and `run_mei_acceptance.py` cleanup pass that same
base to `stop_mei_server.sh`; acceptance still stops the server **before** the
launcher wrapper. Never use or clean the historical sibling `mei-runtime` tree.
Configs without the optional field keep the stop script's existing defaults.
The launcher prints the selected runtime even in `--dry-run`, without creating
it. The LFM command uses literal absolute model/build/runtime/source paths so it
also works with acceptance's direct argv (which does not expand `$HOME`/`$PWD`).
Commit the config and provenance before any launch.

## Isolated Hermes coding profile

`orchestration.hermes_profile: bench-lfm25` and
`orchestration.hermes_provider: lfm25-mei` are non-null. The runner forwards that
profile to **every coding suite**, `hermes chat`, session export, and transcript
headers. Configs without `hermes_profile` still use `bench`. An isolated selection
never runs the destructive shared `reset_bench_profile.sh`; operators must
provision a fresh profile explicitly for each independent comparison. The
fixture runner also accepts `--hermes-profile NAME` (CLI > config > `bench`).
The user's `default` profile and path-like/empty/null names are rejected.

`hermes-profile.example.yaml` is a repository template, **not profile state**.
It defines the matching keyless loopback provider on port **8029**, exact served
model, context **65536**, vendor sampler (**0.1 / top_k 50 / top_p 0.0 /
repetition_penalty 1.05**, min_p 0), and explicit output budget **4096**.
`extra_body` keeps Hermes request defaults from overriding those server settings;
`reasoning_effort: null` supplies no invented effort level. It does not alter the
thinking template. Generic Mei/Hermes defaults are unchanged.

The template also pins the existing benchmark CLI policy: `agent.max_turns: 40`,
`approvals.mode: "off"`, CLI toolsets `[clarify, code_execution, connections,
file, terminal, todo]`, the two shared skill roots under `/Users/tijs/.hermes`,
no enabled plugins, `model.max_tokens: 4096`, `terminal.cwd: .`, and both memory
flags disabled. These are explicit comparison controls, not Hermes defaults.
The skill roots are host-local references, not cloned profile state; preserve
their exact paths for this host. Approval checks are disabled **only for
isolated benchmark fixtures**, never for the user's normal profile.

Even a fresh, non-cloned profile can inherit stale main-model routing defaults.
Explicitly set `model.base_url` and `model.api_mode` to match the named provider's
`api` and `transport`; setting only the provider leaves is not sufficient.

The parent/operator has separately provisioned and read back a **fresh,
non-cloned** `bench-lfm25` profile; see `VERIFICATION.md` for the current gate
status. To reproduce that state, create a fresh profile (do not overwrite an
existing comparison profile or run `profile use`) and apply **every** template
key through the named-profile CLI. This recipe is documentation only; the
model-free tests parse its arguments but never execute it:

```bash
# Reproduction recipe only — NOT executed by model-free tests.
hermes profile create bench-lfm25
hermes --profile bench-lfm25 config set model.provider lfm25-mei
hermes --profile bench-lfm25 config set model.default LiquidAI/LFM2.5-24B-A2B-MLX-4bit
hermes --profile bench-lfm25 config set model.base_url http://127.0.0.1:8029/v1
hermes --profile bench-lfm25 config set model.api_mode chat_completions
hermes --profile bench-lfm25 config set model.context_length 65536
hermes --profile bench-lfm25 config set model.max_tokens 4096
hermes --profile bench-lfm25 config set providers.lfm25-mei.api http://127.0.0.1:8029/v1
hermes --profile bench-lfm25 config set providers.lfm25-mei.transport chat_completions
hermes --profile bench-lfm25 config set providers.lfm25-mei.default_model LiquidAI/LFM2.5-24B-A2B-MLX-4bit
hermes --profile bench-lfm25 config set providers.lfm25-mei.context_length 65536
hermes --profile bench-lfm25 config set providers.lfm25-mei.discover_models false
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.temperature 0.1
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.top_k 50
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.top_p 0.0
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.min_p 0
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.repetition_penalty 1.05
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.max_tokens 4096
hermes --profile bench-lfm25 config set providers.lfm25-mei.extra_body.reasoning_effort null
hermes --profile bench-lfm25 config set agent.max_turns 40
hermes --profile bench-lfm25 config set approvals.mode off
hermes --profile bench-lfm25 config set platform_toolsets.cli '["clarify", "code_execution", "connections", "file", "terminal", "todo"]'
hermes --profile bench-lfm25 config set skills.external_dirs '["/Users/tijs/.hermes/skills", "/Users/tijs/.hermes/shared-skills"]'
hermes --profile bench-lfm25 config set plugins.enabled '[]'
hermes --profile bench-lfm25 config set terminal.cwd .
hermes --profile bench-lfm25 config set memory.memory_enabled false
hermes --profile bench-lfm25 config set memory.user_profile_enabled false
hermes --profile bench-lfm25 config check
```

Read back that exact named profile before a canary: verify `model.base_url`
matches `providers.lfm25-mei.api` (`http://127.0.0.1:8029/v1`) and `model.api_mode`
matches `providers.lfm25-mei.transport` (`chat_completions`). Use
`hermes --profile bench-lfm25 config get KEY` to compare every template leaf,
including all CLI policy values above, the **4096** cap in both `model.max_tokens`
and provider `extra_body.max_tokens`, `terminal.cwd`, and both memory flags.
Keep the fresh profile credential-free; do not clone history, channels, or
credentials from `bench` or `default`. No model-free test creates profiles,
changes the sticky/global provider, or copies user credentials.
Provider/profile routing and sampler preservation still need a live wire canary;
passing forwarding tests are not inference compatibility proof.

## Coverage and gates

The canonical `run_bench.py` default inventory is **25 tasks**:

- sanity: 2
- hermes_ops: 8
- kiem_mini: 5
- hearth_mini: 3
- kipclip_mini: 4
- hearth_full: 3

Model-free tests mock all launch/health/grade calls and prove that the real config
selects every suite after normal sanity/speed gates pass. They produce **no real
benchmark rows**. Sanity failure or the normal speed gate can still stop a real
run; nothing here bypasses those policies. Results remain append-only.

Remaining candidate gates: sustained clean-GPU/memory/swap/disk headroom
(10 GiB disk floor) without further deletion, and binary/metallib identity if
rebuilt; bounded native admission and one-task resource check, reviewed before
a full retry. Retain normal sanity/speed gates and audit any later full battery's
distinct config/runner identity, rows and teardown. Controlled sweeps and at
least three repeats are required for performance claims, separating TTFT/prefill,
decode and end-to-end speed. Prior admission and selection recovery are
parent-reported, not a new resource guarantee or evidence for this candidate.
Do not run these live stages as part of model-free verification.

Model-free checks:

```bash
env -u PYTHONPATH -u PYTHONHOME TMPDIR=/Users/tijs/.hermes/cache/scratch \
  uv run --locked --offline python -m unittest runner.tests.test_lfm25_setup \
  runner.tests.test_start_mei_server_sh runner.tests.test_mei_runtime \
  runner.tests.test_run_bench runner.tests.test_run_prompt_suite \
  runner.tests.test_bench_common -v
bash -n runner/start_mei_server.sh runner/stop_mei_server.sh
git diff --check
```

These focused suites use mocks, metadata-only wrapper dry-runs and inert shell
recorders replacing the build, metallib helper and executable. The recorders
prove actual child-environment forwarding without Swift, Mei, a model, a
listener or endpoint calls. Dry-runs cover all other wrapper configs, including
research variants and their inherited env prefixes. Do not substitute broad
discovery for this restricted check: some adjacent suites start loopback HTTP
fixtures.

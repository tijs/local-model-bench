# LFM2.5 setup and remaining live gates

This lane uses the official MLX artifact at
`667408d494bde191c2cb9dd4f4549827816b9275` (source model revision
`1769516ac588c4c558089c94f27d96b0dc67b183`). Model-free tests do **not**
establish loadability, tool correctness, useful speed, or benchmark results.
No model or Hermes profile is installed by these tests.

## Current harness correction: Hermes Ops connect budget

The parent reports that the separate native admission passed **12/12** (including
full context/tools), and the first canonical attempt loaded Mei 0.9.0 with exact
identity/plain completion and **sanity 2/2**. Hermes Ops then repeatedly failed
at the **60-second pre-header/connect watchdog** with no token usage; later
server-unreachable rows followed the operator's stop. This supersedes the
earlier pending-live language in the staging/build sections below, but is **not
a complete benchmark result**. The prior attempt remains append-only under
config **`0fb346ed9077`** / runner **`edda01df84c3`**.

`mei.yaml` now opts into **`hermes_ops_connect_timeout: 300`**. This is a bounded
client harness policy, not vendor tuning or a measured optimum. The connect
budget includes waiting for response headers, so the suite's 600-second
first-progress budget cannot help until headers arrive. The model override is
validated as positive finite numeric seconds (no bool) and forwarded only for
Hermes Ops as `--connect-timeout 300`; absent fields retain the existing
60-second client default (or a suite's own explicit connect budget). Sanity,
coding, sampling, context/cache/mmap, all other liveness/turn/task budgets and
retries are unchanged. See `configs/README.md` for precedence and validation.

The corrected config has a distinct content hash and must be committed before
any fresh gated retry. **Live recovery at 300 seconds is unverified**: this
follow-up performs only model-free tests, no inference/server/full benchmark,
and never alters the existing result artifacts. `VERIFICATION.md` distinguishes
the parent's prior evidence from the harness tests and remaining retry gate.

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
before launch. Model load, canary and full-battery gates remain pending.

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

Remaining retry gates: recheck clean-GPU/memory/disk headroom (10 GiB launch
floor) without further deletion, and binary/metallib identity if rebuilt; retain
native admission, sanity and speed gates; verify the corrected connect budget
on a fresh complete battery with a distinct config/runner identity and independent
row/provenance/teardown audit. Prior admission is parent-reported, not a new
guarantee, measured tuning result, or proof of recovery. Do not run these live
stages as part of model-free verification.

Model-free checks:

```bash
env -u PYTHONPATH -u PYTHONHOME TMPDIR=/Users/tijs/.hermes/cache/scratch \
  uv run --locked python -m unittest runner.tests.test_run_prompt_suite \
  runner.tests.test_generation_overrides runner.tests.test_lfm25_setup -v
uv run --locked python -m unittest discover -s runner/tests -p test_lfm25_setup.py -v
uv run --locked python -m unittest discover -s runner/tests -p test_start_mei_server_sh.py -v
uv run --locked python -m unittest discover -s runner/tests -p test_mei_runtime.py -v
```

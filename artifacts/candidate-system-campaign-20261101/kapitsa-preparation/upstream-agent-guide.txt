# Kapitsa: instructions for coding agents and reviewers

This file is the one source of truth for agents (Claude Code, Cursor, Codex, Devin and the like). `CLAUDE.md` and
`.cursor/BUGBOT.md` point here or repeat the review rules; do not grow a second copy of these rules elsewhere.
Contributor-facing details (build, tests, layout, style) are in [CONTRIBUTING.md](CONTRIBUTING.md); the design is in
[docs/architecture.md](docs/architecture.md), the commands and switches in [docs/usage.md](docs/usage.md).

Kapitsa is a native C++20 inference engine for Apple silicon (Metal kernels, the Neural Engine, no MLX or llama.cpp
runtime). Speed and exact outputs are the product. A change that is faster but not the same tokens is a different
change and has to say so.

## What an agent can and cannot check

- **You can** build, run the CPU tests, run `prek`, read and edit code. Do these before every push.
- **You cannot** know a Metal kernel is right or fast without running it on a GPU, and the Metal sources are embedded
  as text and compiled at run time: a successful build says nothing about them. If you did not run it on a Mac with a
  GPU, say so in the PR ("Not verified on a GPU", in the title too; precedent: PR #170). Never write speedups,
  "bit for bit" or "the same outputs" for something you did not run.
- Do not load a model or touch the GPU unless the task says you may. A run takes the machine's GPU for minutes and
  other people's measurements are on it.
- `.dsh/skills/verify-kapitsa` drives the CLI and server and keeps evidence; its `vk checks` reads the diff
  against `origin/main` and says whether a PR needs a GPU run and on which models.

## Build and test (exact commands)

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release          # CMake 3.24+, Xcode Command Line Tools, macOS 14+ target
cmake --build build -j --target kapitsa                  # the CLI only; drop --target for every tool too
```

`all` also builds tools that need a newer macOS SDK than 15.x (`tensor_probe` uses `MTLLanguageVersion4_0`): on an older
SDK build the named targets, as CI does.

CPU tests (no model, no GPU), after building `kapitsa api_test execution_session_test http_stream_test bench_test
update_test prefix_cache_test grammar_test structured_check fn_store_test fn_dflash_test tokenizer_test iq_layout_test
exl3_test remote_test cluster_test split_place_test qwen4_config_test json_file_test systemone systemone_test
systemone_codes_probe_test systemone_codes_driver splash_protocol_test splash_runtime_test splash_discover_test splash_plan_test logit_dump`:

```bash
build/api_test
build/prefix_cache_test
build/fn_store_test                          # the streamed-expert cache (src/model/expert_store.h)
build/fn_dflash_test                         # DFlash2's stream_mean reduction checks (Flash-Next drafts)
build/tokenizer_test                         # Flint's pre-tokenizer split
build/iq_layout_test                         # GGUF IQ experts in the GPU layout (src/kernels/wfmt_iq.metal)
build/exl3_test                              # the EXL3 reference decoder (src/model/moe_exl3.h), Flash-Next's norm check
build/remote_test                            # a split model's reserve on its other Macs (src/model/remote.h)
build/cluster_test                           # several Macs (src/cluster/): TXT, JSON, routing, kapitsa cluster's table
build/split_place_test                       # where a split model's layers go (src/cluster/place.h)
build/qwen4_config_test                      # what a Qwen 4 config asks that Flash-Next's path does not run (src/model/qwen4_config.h)
build/json_file_test                         # config.json parsed once per file (src/util/json_file.h)
build/affine_pack_test                       # MLX affine pack helpers: bit width from shapes, f16 -> bf16 (src/model/affine_pack.h)
build/systemone_test                         # System One's pointer heads, readout (Drex Max v1) and projected (Drex v2.0) (src/systemone/systemone.cpp)
build/systemone_codes_probe_test             # controlled option-code regression, built and run explicitly in CI
build/execution_session_test                 # one-shot sessions: start, cancel, terminal order, join (src/engine/execution_session.h)
build/http_stream_test                       # HTTP streaming: framing, keepalive, disconnect, meters (src/server/http_stream.cpp)
build/ws_upgrade_test                        # a WebSocket upgrade on /v1/responses gets 426, the rest passes through (src/server/ws_upgrade.h)
build/splash_protocol_test                   # Splash protocol v11 frames against Splash 1.4.0's goldens (src/splash/protocol.h)
build/splash_runtime_test                    # the Splash engine child: start, requests, cancel, death (src/splash/runtime.h)
build/splash_discover_test                   # finding Splash's engine and model on a throwaway tree (src/splash/discover.h)
build/splash_plan_test                       # what Kapitsa adds to `splash serve-native`, and when (src/splash/plan.h)
python3 tests/test_server.py --cli build/kapitsa
python3 tests/test_sidecar.py build/kapitsa
python3 tests/test_bench.py build            # needs: jsonschema; on a real Mac only (CI's VM runners fail it)
python3 tests/test_update.py build
python3 tests/test_community.py build        # needs: jsonschema
python3 tests/test_reasoning.py
python3 tests/test_drex_max.py --cli build   # Drex Max v1: head extraction, tokenizer-only request layouts (no model, no GPU)
python3 tests/test_pr_size.py
python3 tests/test_splash_patches.py --apply   # packaging/splash/: clones Splash and applies the patches; no build
python3 tests/test_logit_compare.py
python3 tests/test_logit_dump.py build      # its output directory only, before the lock and the model
python3 tools/qwen4_exp_pack_test.py         # needs: numpy; the Flash-Next converter's n-gram table from a config.json
python3 tests/test_structured.py --cli build    # with a model folder's tokenizer when one is downloaded
```

Both `systemone_codes_probe_test` and `systemone_codes_driver` are `EXCLUDE_FROM_ALL` targets. CI explicitly builds
and runs the controlled probe. The driver is for per-change old-versus-new evidence, not a standing differential CI
check. Build it explicitly for that evidence. `vk` has separate hardcoded build and test lists. Editing this file
does not update those lists.

For an option-code change, build candidate and reference drivers with the same compiler flags and the same driver
and tokenizer sources. Replace only the reference's [systemone.cpp](<src/systemone/systemone.cpp>) with the
pre-change source and record its commit.

CMake Release uses `-O3`. The standalone `-O0` example in [test_systemone_codes.py](<tests/test_systemone_codes.py>)
is a CPU correctness build, not the Release configuration. Neither configuration measures inference speed.
Compare all 104 requests:

```bash
python3 tests/test_systemone_codes.py --candidate build/systemone_codes_driver --reference /path/to/reference-driver
python3 tests/test_systemone_codes.py --candidate build/systemone_codes_driver --reference /path/to/reference-driver --tokenizer /approved/drex-max-v1/tokenizer.json
python3 tests/test_systemone_codes_harness.py  # script checks with stand-in driver results, not encoder evidence
```

Without `--tokenizer`, the script creates the three synthetic fixtures and checks their goldens. With `--tokenizer`,
both drivers load the specified existing file unchanged. That mode skips only synthetic goldens. Both modes compare
complete outputs and require the known-valid two-option request to produce nonempty tokens in both drivers.
The script reports accepted and rejected counts per driver, the tokenizer SHA256, its parent `model_dir`, and the
JSON's `model.type`, `ignore_merges`, and `pre_tokenizer`. The logged `model_type` is the tokenizer model type,
not the neural model architecture. The script checks the tokenizer digest after each driver run.

Real-vocabulary evidence for Drex Max requires the actual Drex Max v1 metadata identity. A Drex v2 tokenizer is a
substitute only with evidence that its bytes are identical. A Qwen control is optional. Directory names and a
matching tokenizer type do not establish identity. This CPU coverage does not waive the model output, GPU, or
interleaved speed gates below, and does not establish an inference speedup.

Everything else needs a model folder, often the GPU too (`parser_test MODEL_DIR`, `tests/vision/check_cpu.py`, `logit_dump`,
`batch_check`, `ni_v8check`, `tests/test_server.py URL`, `tests/test_disk_cache.py`, `tests/test_draft.py`,
`tests/test_structured.py URL`, `logit_mask_check`, `split_check`, `tests/test_split.py`, `tests/test_pair.py`,
`tests/test_ane_split_abort.py`, `tests/test_systemone.py`): run it only when allowed, and report it as run.

Lint: `uv tool install prek && prek install` once, then `prek run --all-files` (the same hooks CI runs).

## Rules that bite here

**GPU lock.** Anything that loads a model takes the exclusive flock on `$BENCH_GPU_LOCK` (default
`/tmp/kapitsa-gpu.lock`), as `lockf -k -t <ms> <file> <command>` does, and a caller that already holds it says so with
`NI_LOCK_HELD=1` / `NACE_GPU_LOCK_HELD=1`, which every tool that takes the lock, and `kapitsa bench`, read through
`GpuLock::held_by_caller()`. Say it: `flock` is per open file description, so a tool wrapped in `lockf ... <tool>`
that does not is blocked by the lock it already holds. A tool that takes no lock itself (`tools/flint_moe_check.cpp`,
`fn_check.cpp`, `fn_q2_bench.cpp`, `ni_handshake.mm`: their headers say so) is meant to be run under
`lockf -k /tmp/kapitsa-gpu.lock`, and needs no marker. A new script, workflow or test that uses the GPU takes the lock;
a test points `BENCH_GPU_LOCK` at a temporary file. See `src/bench/system.mm` (`GpuLock`), `bench/shortpf/locked.sh`.

**Metal kernels.** A kernel that reads or writes out of bounds can fault the GPU and take the desktop down. Run a new or
changed kernel at small sizes first, with `MTL_SHADER_VALIDATION=1 MTL_DEBUG_LAYER=1`, and say that you did in the PR.
Kernel sources live in `src/kernels/` (including `nemotron/`, `dory/`, `tensor/`) and are concatenated into one string
by `cmake/embed_*.cmake`; a new `.metal` file is picked up by the glob.

That layer counts a kernel's static threadgroup memory **twice** on this macOS and compares the sum against the device's
32,768 B threadgroup cap, so a dispatch aborts whenever a kernel's static allocation is above 16,384 B, whatever the
change under review. Measured on 2026-10-22, M5 Pro / macOS 26.5.2 (build 25F84): `attn_prefill11`'s 20,480 B reads as
`total used threadgroupMemoryLength(40960) must be <= 32768` and aborts, while `attn_prefill11_k16x`'s 16,384 B reads as
exactly 32,768 B and runs with the layer on. A full prefill therefore aborts with the layer held on `attn_prefill11g`
(20,480 B static, read as 40,960) and `moe_gate_up3_r2` (16,448 B, read as 32,896) no matter what the PR touches; the
driver's own check agrees with the real limit, which `tools/ni_kstats --limits` reports. So: hold the layer at small
sizes when the changed kernel's static memory is 16,384 B or less, and when it is more say in the PR that the layer's
doubling makes a run impossible, with the kernel's size; a PR is not "unverified" for saying that.

**New features ship on by default somewhere.** Every opt-in switch is code to maintain and a setting nobody tunes. The
goal is per-model, per-Mac settings, perhaps several per pair someday (minimal, optimal, max; today Kapitsa pursues max).
There is no config system for opt-in features yet. So a feature merges only when at least one of these holds:

1. **It is a default.** The feature is on by default for at least one model on at least one Mac, earned with the
   interleaved A/B and the output check below. The PR names the setting it is the default for. Other models may reach it
   opt-in.
2. **It is widely established.** A well-known paper or a major engine (llama.cpp, MLX, vLLM, SGLang, TensorRT-LLM) has
   it, and it makes sense for Kapitsa: Apple silicon, exact outputs, single-stream speed. The PR cites the source and
   says why it fits.

Here a feature means a kernel path, a decode, drafting or verify strategy, a cache or memory policy, or a new user-facing
flag or environment variable. Three things are not features, so this rule does not apply to them: a kill switch for an
existing default (`NI_X=0`), a debug or profiling switch, and a measuring tool. A feature that is promising but not yet
faster in any setting stays an open PR (a draft is fine) and keeps improving until it wins a default. It does not merge
opt-in "for later". If the author could not test many models, the PR turns the feature on for what it measured. A later
PR widens the default as other models and Macs are measured.

**Changing speed or numerics.** One change per PR. Measure only on an idle GPU (nothing else running), interleave old
and new builds (A B A B), report every run with the Mac, macOS version and commit. A default changes only after an
interleaved A/B *and* the output check of CONTRIBUTING.md ("Output check"): `build/logit_dump` of the old and the new
build, `tools/logit_compare.py` between them, gated at twice the model's noise floor on this Mac
(`tools/logit_floors/<model>.json`). Put its output in the PR. "The same outputs to the bit" is a claim with evidence
("every row bitwise identical") or it is not made; a change that fails the gate on purpose says it moves outputs.
Never re-measure or edit a floor to let a change pass: `tools/logit_floor.py` re-measures one, in a PR of its own.
One change cannot pass that gate and is still legitimate: a kernel that keeps every product and only reassociates the
K reduction (the experts' GEMM on the M5's tensor units instead of the simdgroup kernels), where half*half products are
exact in fp32 and a different order moves ~0.5% of the sums by one half ulp. Gate it with
`tools/logit_compare.py --reorder` instead, whose bounds are twice the first such change's measured drift, as the floor's
gate is twice its measured floor (a floor file's own `reorder_gate` replaces them for its model: Flint on the M5,
CONTRIBUTING.md), and show in the PR that the diff is a reassociation rather than a precision change: the
per-GEMM check in `tools/bench_moe.cpp` (`vs qrm` columns, every output within one half step of the shipped path's, and
both paths' error the same against a double-precision reference) plus what the temperature-0 continuations did (cold 4K
and 16K prompts: the 35B-A3B's came out identical). That flag is a claim about the diff:
anything that changes *what* is computed stays on the floor's gate.

Historical measurements, known gate exceedances and model coverage are recorded in
[docs/numerical-history.md](docs/numerical-history.md), with links to the public changes. Those records do not
waive the output check for a new change or authorize changing a default.

Requests decoded together can legitimately differ at near-ties from alone (docs/architecture.md); a single-stream path
must not change.

**SSD prefix cache.** Conversations' states stay on users' disks across updates (`src/engine/engine_disk.cpp`). A change
to what a state's bytes mean (KV row order or precision, the recurrent state's layout, the drafter's ring, what a
snapshot holds) that the model's `disk_format()` does not show must bump `kStateFormat` there, or new binaries read old
states wrongly.

**Dependencies.** None without a strong reason: Kapitsa builds with Xcode CLT and CMake alone. `third_party/` is
vendored; do not edit it.

**Python.** Tools, benchmarks and tests are stdlib-first scripts. `ruff` runs as a correctness gate only (`ruff.toml`);
do not reformat files you are not changing.

**Frozen data.** Prompts, token ids, corpora and recorded results under `bench/` are inputs to published numbers. Do not
reformat, regenerate or "clean" them; hooks and editors must not touch them. A results folder that gains a run, a row or
a chart is normal, and only additions are invisible. A commit that also *changes* a file already under `bench/results/` or
`bench/community/results/` says so in its subject and why ("re-measured …", "supersedes …", "erratum: …"): the branch no
longer holds the old copy, so a reader cannot tell a declared erratum from an accident. Transcripts are where that bites
hardest: a run script that tees `transcripts/<label>.out` overwrites that label's frozen transcript when the label is
re-run, so commit the new run under a new label, or say in the subject that the transcript is replaced.

**Docs follow numbers.** When a measured number, a default, a flag or a catalog entry changes, grep the repo for the old
value (README, docs/usage.md, docs/benchmarks.md, `tests/`, the catalog in `src/hub/catalog.cpp`) and update every copy.

## Pull requests

- One change per PR. Branch off the current `origin/main`; `main` takes squash merges only, and the title becomes the
  commit: state the change and its measured effect (the repo's titles carry numbers and "(#NNN)").
- A new feature says which model and Mac it is the default for, or which paper or engine establishes it ("New features
  ship on by default somewhere" above). An opt-in feature with neither stays an open PR.
- The description says what changed, the measured before/after with a `Runs:` line (Mac, macOS, model), and what was
  checked how. A separate "Not verified" section lists what was not run, above all anything needing a GPU.
- Benchmark submissions carry the `benchmark` label, the results table, `Kapitsa version (commit)`, `Flags:`, and say
  `kapitsa bench` produced them. Results come only as pull requests from a fork, never as issues.
- PRs of more than ~1000 changed lines (generated data and vendored code excluded) fail the `PR size` check. Split them.
  Only a reviewer overrides it (`size/override` label and a `Size override: <why>` line in the description); an author
  does not label their own PR through it.
- Never merge your own PR and never use admin bypasses. Do not change repository settings, rulesets, secrets or runners.
- Workflows: keep the posture of `community-bench.yml`. `pull_request_target` only when the job never runs PR code
  (checkout the base, read the PR as data); never put PR-controlled text (titles, branch names, file names, bodies) into a
  `run:` line, pass it through `env:`. New GPU-using workflows take the GPU lock. Pin tool versions.
- Do not commit agent memory, plans or personal settings (`*-local*`, `.claude/`, `.cursor/plans`). Do not commit
  `build/`, models or `*.bin`.

## Reviewing

`.cursor/BUGBOT.md` carries the review checklist for Cursor Bugbot, which reads only that file. If you change a rule
here that a reviewer must enforce, change it there too.

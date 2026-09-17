# AXQ 6-bit Mei source/build pin reconciliation, 2026-09-18

Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2` (todo 20), blocked AXQ6 native
gate: runner/start_mei_server.sh ALWAYS builds on demand
(`swift build -c release --scratch-path "$BUILD_DIR" --package-path "$MEI_REPO"`),
so a launch is reproducible only when `--mei-repo` names an exact-source
boundary. This unit makes that pin reproducible; it does NOT rerun the gate.
No model, Mei server, probe, or benchmark ran in this unit.

## Pinned commits (unchanged from the config's existing provenance)

- Mei source: `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` = tag `v0.5.0`
  (re-verified `git -C ~/projects/mei rev-parse v0.5.0`).
- vmlx-swift: `44461ffdf8dca836b624b2d0d268c800dedea05e`, read from the clean
  export's `Package.resolved` (verified 2026-09-18).

## Clean benchmark-owned source export (created this unit)

- Path: `/Users/tijs/.local/share/local-model-bench/mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`
- Created solely from `git archive` of the pinned commit in the read-only
  `/Users/tijs/projects/mei` checkout (that checkout was NOT modified: still
  HEAD `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` with only the pre-existing
  untracked `Casks/` and `tap/`).
- Verification: 378/378 commit files exported (commit tree
  `df3b6d7f5af66169aaccf78d5589d815df95ab3a`); `Package.swift`,
  `Package.resolved`, `scripts/prepare_metallib.sh` present; NO `.git`;
  `Package.resolved` pins vmlx-swift to `44461ffdf8dca836b624b2d0d268c800dedea05e`;
  `Sources/Mei/main.swift` blob hash `3a7d1952609327c0d57685b8f7bfbce24643a15c5662d22491ad26062deca380`
  == the commit blob. `git archive` tar sha256 `760d61e718d9da3b3748e5a6d31da2353b371e23270b5dca7860e6f4a008c0c8`.
- Export lives outside Git (runtime artifact, not committed); no model weights
  were copied. `~/projects/mei` tracked tree remains untouched.

## Old vs new build path

- OLD (contaminated, HISTORICAL EVIDENCE ONLY):
  `/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-optiq-050` —
  the prebuilt scratch binary was built from the pre-reconciliation working
  tree; its strings embed the post-tag alignment-warning text (scan of the
  binary in this unit matched alignment-related strings), so it is NOT a
  safe exact-source boundary. Never use it as a build source again.
- NEW (fresh dedicated): `/Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050`
  in the config's launch command; the dry-run confirmed it does not exist yet
  and nothing writes it in a dry-run (see validation).

## Prior timeout — preserved evidence (NOT rewritten)

`artifacts/qwen36-axq6-native-gate-timeout-20260917.md` plus raw gate dir
`/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260917T204408Z/`
(`record.json`: `status: "error"`, `TimeoutExpired ... timed out after 3600
seconds`, no `probe.json`; `launcher.log`). Untouched by this unit.

## Config change (configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml)

`benchmark_launch_command` now passes
`--mei-repo /Users/tijs/.local/share/local-model-bench/mei-source/mei-1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`
and `--build-dir /Users/tijs/.local/share/local-model-bench/mei-build-qwen36-axq6-pinned-050`
instead of `--mei-repo /Users/tijs/projects/mei` +
`--build-dir .../mei-build-qwen36-optiq-050`. ALL safe flags and the exact
served identity are byte-identical (verified by diff of the launch block minus
those two lines). Comments/settings/known_gaps updated minimally to state:
builds come from the clean exported pinned source; the old scratch binary is
historical evidence only; this is a fresh pre-gate setup with no benchmark
rows. Config hashes (sha256[:12]): previous committed `703118869d87` (no
results/configs snapshot, no rows), new final `942fd0c767d0` (no snapshot, no
rows — created at first benchmark run only). Neither hash has any
results/log.jsonl row or results/configs snapshot.

## Validation results (this unit)

- YAML parse via locked interpreter (`uv run --locked python` + PyYAML 6.0.3):
  OK; served_model_id `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`, port
  8025, context 65536, all safe controls present in the extracted launch
  command.
- `bash -n runner/start_mei_server.sh`: OK. `bash -n` of the assembled config
  launch command (+ --dry-run): OK.
- Non-destructive `bash start_mei_server.sh --dry-run` with the exact config
  launch command: exit 0, printed the full isolated launch line
  (`.../mei-build-qwen36-axq6-pinned-050/release/mei --model-dir
  .../mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP --served-model-id
  AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP --host 127.0.0.1 --port 8025
  --context-cap 65536 --temperature 0.6 --top-p 0.95 --top-k 20
  --emit-reasoning true --cache-reuse true --prefill-step-size 512
  --enable-thinking true --kv-cache-dir .../mei-runtime/kv-axq6-mtp
  --memory-limit-bytes 30000000000 --compiled-decode false --load-mmap false`).
- Port 8025 FREE before and after; `pgrep -fl 'mei|probe_mei|swift'` empty
  before and after; fresh build dir NOT created by the dry-run; no server, no
  model load, no probe, no benchmark.
- Unit incident (recorded transparently): the FIRST dry-run attempt appended
  `--dry-run` on its own line (the YAML block scalar's trailing newline split
  it off), so the real launch ran and began a `swift build` (dependency fetch
  only; killed at 120 s; zero compilation, no server). The partial scratch dir
  `mei-build-qwen36-axq6-pinned-050` and the stray `mei-runtime/logs/build.log`
  written by that interrupted attempt were removed, restoring pre-unit runtime
  state; the corrected dry-run (the line above) then passed. No benchmark
  evidence or historical artifact was touched.

## Follow-up

Next unit may run the native gate against this config/hash
(`942fd0c767d0`); no rerun happened here.
# Bonsai 2 MLX — isolated attn-chunk build boundary gate — 2026-09-20

## Verdict

The isolated build boundary for the Bonsai 2 MLX track is **reconciled** against
the exact `vmlx-swift-bonsai-attnchunk` source at `f9fb21c0`, wired as a local
SwiftPM dependency named `vmlx-swift`:

- Narrow focused gates reproduce the parent's recorded numbers on an
  independent throwaway checkout: `Qwen35FAAttentionChunkParityTests` **6/6**
  and the PrismBonsai suites **93/93** (5 suites), both exit 0.
- The canonical broader `MLXLMTests` boundary now **builds** cleanly (it was
  previously blocked at the Mei-pinned `44461ffd` rev by a pre-existing
  `Evaluate.swift` type-check timeout; the in-branch fix commit `12121099`
  resolves it). Running the target per-suite under bounds: **301/310 suites
  pass, 9 fail fast on pre-existing non-Bonsai issues, 0 timeouts**.
- The **Mei release executable was produced** against the local dependency:
  exit 0, Mach-O arm64, SHA-256
  `271e9a949f2785f1213e6655c07d9178db5b2039eebc7f181b6358dc884cc780`.
- `VMLX_BONSAI_PRISM_HADAMARD` default-off behavior preserved (never set;
  removed from the test-driver env explicitly). `VMLX_QWEN35_FA_CHUNK` never
  set (the parity suite toggles the chunking knob in-process under the shared
  MLX lock). No model was loaded, no server launched, no port opened, no
  benchmark run, no weights downloaded/copied, no unsafe compile, no publish.

## Exact source pins

- Mei HEAD: `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` (throwaway clone).
- vmlx branch: `f9fb21c0274083612887e4c7d8b3fe07743141fa` (throwaway clone,
  dir basename `vmlx-swift` → SwiftPM identity `vmlx-swift`, matching Mei's
  product references; verified via `swift package describe`).
- vmlx git submodules (required, initialized in the throwaway at the pinned
  commits): `Source/Cmlx/mlx` @ `73312d3e9ad0bd2e1bdf9a08d91e25571e255964`,
  `Source/Cmlx/mlx-c` @ `7bede8f1491384bb580f87d1d510f80cbd53660d`.
- Mei manifest change (throwaway only): `url+revision` vmlx dependency →
  `.package(path: "../vmlx-swift")`.
- Toolchain: Apple Swift 6.4 (swiftlang-6.4.0.34.1), Xcode 27.0 (27A266a),
  `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer`, macOS 27.0.

## Throwaway paths (kept for parent inspection)

- Root: `/private/tmp/bonsai2-attnchunk-gate-20260920`
- `mei/` — throwaway Mei clone at 950e8c2f (manifest patched to local dep)
- `vmlx-swift/` — throwaway branch clone at f9fb21c0 + initialized submodules
- Logs: `log-qwen35-parity.txt`, `log-prismbonsai.txt`, `log-mlxlm-tests.txt`,
  `log-metal-prep.txt`, `log-mei-release.txt`, `log-submodules.txt`
- Suite sweep: `suites.txt` (310 suites), `suite-results.tsv`,
  `suite-logs/*.log`, `sweep.log`
- Artifacts: `mei-release-arm64-bin` (binary copy),
  `vmlx-swift/default.metallib` + `mlx.metallib` (freshly compiled),
  `mei-describe.json`

## Commands and results

| # | Command (workdir = throwaway) | Exit | Result |
|---|-------------------------------|------|--------|
| 1 | `git clone --shared /Users/tijs/projects/mei mei` | 0 | HEAD 950e8c2f, clean |
| 2 | `git clone --shared /Users/tijs/projects/vmlx-swift-bonsai-attnchunk vmlx-swift` | 0 | HEAD f9fb21c0, clean |
| 3 | patch `mei/Package.swift` → `.package(path: "../vmlx-swift")` | — | identity `vmlx-swift` resolved |
| 4 | `swift package describe --type json` (mei) | 0 | dep identity=vmlx-swift → ../vmlx-swift |
| 5 | `git submodule update --init --recursive` (vmlx-swift) | 0 | mlx + mlx-c at pinned SHAs |
| 6 | `swift test --filter Qwen35FAAttentionChunkParityTests` | 0 | 6/6 passed (90.4 s) |
| 7 | `swift test --filter PrismBonsai` | 0 | 93/93 in 5 suites |
| 8 | `./scripts/prepare-mlx-metal.sh default.metallib` | 0 | fresh metallib, 3,154,810 B, md5 b58691329be5c5b3b7b7823b190b3016 |
| 9 | `swift test --filter MLXLMTests` (one-shot) | killed | deadlocked at `BucketKeyTests` "hashable…" start, 0% CPU; freeze artifact below |
| 10 | `python3 run_suites.py` (310 suites, 300 s cap each, semaphore reset per suite) | 0 | 301 pass / 9 fail / 0 timeout; 2,199 tests |
| 11 | `swift build -c release --product mei` (mei) | 0 | Build complete 287.5 s → `.build/release/mei` SHA-256 271e9a94… |

## MLXLMTests boundary detail

- Build: `Build complete! (167,60 sec)` for the debug test bundle (one-shot
  run), then incremental for per-suite runs; the MLXLMTests target compiles
  and links with the local vmlx dependency.
- One-shot full-target run freezes mid-stream (last output `◇ Test "hashable
  —…` started, then idle at 0% CPU for 5+ minutes; sampled stack shows the
  test framework parked in the runloop with a cooperative worker blocked —
  consistent with Swift Testing's default cross-suite parallelism colliding
  on the shared `/vmlx_mlx_lock` Metal semaphore). Per-suite serialized runs
  complete cleanly, so this is a runner-interference artifact, not a build
  blocker. The failing suites below fail in ~seconds, deterministically.
- 9 failing suites (all pre-existing, none on the Bonsai/Qwen3.5-attn path):
  - `DeepseekV3MoEDtypeTests` — config decode `keyNotFound: norm_topk_prob` (fixture/decoder drift)
  - `DeepseekV4ModelSmokeTests` — E4M3 KV activation goldens mismatch (7 issues)
  - `Glm5NextConstructionTests` — layer/MTP construction expectations (11 issues)
  - `Glm5NextRealConfigForwardTests` — requires real Glm5Next model files on disk (6 issues, environment-gated)
  - `LoadConfigurationTests` — source-contract test (exact `Load.swift` text) drift (4 issues)
  - `MiMoV2FlashRuntimeTests` — source-contract drift (4 issues)
  - `NativeMTPDepth3AutoLaunchTests` — MTP auto-launch policy drift (8 issues)
  - `NativeMTPManualDepthTests` — MTP launch-mode expectations (10 issues)
  - `Qwen4ExpFusedAffineMoETests` — Qwen4Exp reducer/construction contract (4 issues)

## Remaining gate (for the later feature-on memory/capacity probe)

1. The SwiftPM release `mei` binary does not embed `default.metallib`; MLX's C++
   loader needs one reachable via its fallback paths (colocated
   `mlx.metallib`/`default.metallib`, SwiftPM bundle resources, or cwd
   `default.metallib`). Serve the next probe with a metallib prepared by
   `scripts/prepare-mlx-metal.sh` (or reuse the proven xcodebuild recipe from
   the 6a81 gate, which embeds it). The binary was **not** launched.
2. 9 unrelated MLXLMTests suite failures are pre-existing on this branch; they
   are not blockers for the bonsai load path but should be attributed before
   any "suite green" claim.
3. `VMLX_QWEN35_FA_CHUNK=64` and `VMLX_BONSAI_PRISM_HADAMARD=1` remain
   deliberately unset for this gate; the capacity probe decides those knobs
   separately under the parent's plan.

## Preservation and scope

- `/Users/tijs/projects/mei` main: HEAD unchanged `950e8c2f`; only the
  pre-existing user-owned untracked `Casks/` and `tap/` remain; nothing else
  modified.
- `/Users/tijs/projects/vmlx-swift-bonsai-attnchunk` worktree: HEAD unchanged
  `f9fb21c0`, clean, submodules at pinned commits — untouched.
- Staged pack `…/mei-models/Ternary-Bonsai-2-27B-mlx-2bit`: untouched (no
  files newer than session start; nothing copied).
- No benchmark runner, no shared bench port, no `results/log.jsonl` writes.
- Benchmark repo change: this file only.
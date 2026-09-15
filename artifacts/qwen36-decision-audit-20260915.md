# Qwen3.6 track — decision audit, 2026-09-15

Append-only decision-audit artifact for the Qwen3.6 research track. Scope: ONE
durable, CPU-only audit report — no model run, no download, no destructive
cleanup. Everything below marked **Measured** was re-verified live in this
tick (log parsing, config hashes, disk/memory, Hub API/manifest); everything
marked **Decision** is this audit's judgment. Nothing was unavailable that the
task required; where a value is a claim carried by a third party (the AXQ
card), it is labeled as a claim, not a local measurement.

Audit date: 2026-09-15 (CEST / UTC+02:00). Repository:
`/Users/tijs/projects/local-model-bench` (only repo touched). Benchmark HEAD
**before** this report: `21a03ff12493299c6c4e58dca0a9dc24a55553d4` (clean
`main`, 28 commits ahead of origin; verified `git status --short --branch`
clean before and after the audit work). No benchmark/server process and no
listener on port 8024 were present at audit time (read-only `ps`/`lsof`;
consistent with the tick pre-check). Existing row SHAs cited below
(`b5b7f49bcb62`, `f713b29fc5c7`, …) are **historical fragments** recorded in
`results/log.jsonl` — they are NOT the next run's SHA.

---

## 1. Current benchmark methodology (Measured)

- Full eligible run shape = **25 rows**: `sanity` 2 + `hermes_ops` 8 +
  `kiem_mini` 5 + `hearth_mini` 3 + `kipclip_mini` 4 + `hearth_full` 3
  (re-verified by counting `tasks/*.yaml` task lists: 2+8+5+3+4+3 = 25).
- `runner/run_bench.py --help` (recorded verbatim this tick):
  - `--coding-suites CODING_SUITES` — "comma-separated tasks/<suite>.yaml names
    to run EVERY task from (**default: all four, benchmark-v3 —
    kiem_mini,hearth_mini,kipclip_mini,hearth_full**)"; `'none'` gives the old
    single-task spot-check.
  - `--stage {all,coding}` — default `all` (source: `run_bench.py:845`,
    `default="all"`): the normal full config matrix; `coding` runs only the
    coding fixture stage (identity/cold-load/completion gates still run).
- Scoring/grading context (from `LEADERBOARD.md` header, not re-derived):
  `sanity`/`hermes_ops` run at hardcoded temperature 0; coding suites run at
  the config's declared temperature. Grouping is by
  (model, inference_engine, quant, config_hash, runner_git_sha); rows predating
  the 2026-08-21 grading fixes and pre-`benchmark-v2` runs are not comparable.

## 2. Log inventory — `results/log.jsonl` (Measured)

Total rows: **4064**. Rows whose `model` contains `Qwen3.6`: **916**. All eight
distinct Qwen3.6 model strings, with row counts:

| rows | model (exact string) |
|---:|---|
| 418 | `mlx-community/Qwen3.6-35B-A3B-4bit` (stock MLX) |
| 316 | `Tostibrown/Qwen3.6-35B-A3B-4bit-textonly` (text-only MLX) |
| 96 | `HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M` (llama.cpp GGUF) |
| 25 | `EigenLabs/Qwen3.6-35B-A3B-MLX-mixed-4bit` (mixed46) |
| 21 | `unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL` (community GGUF) |
| 20 | `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit` (OptiQ) |
| 15 | `mlx-community/Qwen3.6-35B-A3B-4bit-DWQ` (DWQ) |
| 5 | `ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M` (official GGUF) |

(418+316+96+25+21+20+15+5 = 916 ✓.) Grouped fragments (model, engine,
config_hash, runner_git_sha → rows, suite shape, fails, harness errors),
parsed from every Qwen3.6 row — key legs:

| group | cfg hash | runner SHA | rows | suite shape (rows) | fails | herr |
|---|---|---|---|---:|---|---|---:|
| OptiQ mei `31a7f0b6a256` | `31a7f0b6a256` | `b5b7f49bcb62` | 15 | hearth_full:3, hearth_mini:3, kiem_mini:5, kipclip_mini:4 | 1 | 0 |
| OptiQ mei `31a7f0b6a256` | `31a7f0b6a256` | `f713b29fc5c7` | 5 | kiem_mini:5 | 2 | 0 |
| mixed46 mei `4f91b7aee214` | `4f91b7aee214` | `377e1af4c7cf` | 15 | kiem_mini:15 | 5 | 0 |
| mixed46 mei `4f91b7aee214` | `4f91b7aee214` | `152872acb630` | 10 | kiem_mini:10 | 10 | 0 |
| DWQ mei `b6b5824d3567` | `b6b5824d3567` | `1c8ea189fdb2` | 15 | kiem_mini:15 | 4 | 0 |
| community GGUF llama.cpp `436d6d25d30c` | `436d6d25d30c` | `8d4f1f85f106` | 21 | sanity:2, hermes_ops:8, kiem_mini:5, hearth_mini:3, kipclip_mini:3 (no hearth_full — pre-v3 suite) | 3 | 0 |
| official GGUF llama.cpp `6824b87f5e21` | `6824b87f5e21` | `19aee89cd756` | 5 | kiem_mini:5 | 3 | **2** |
| stock MLX mei `277258e7326f` | `277258e7326f` | `258148c2d48a` | 25 | sanity:2, hermes_ops:8, kiem_mini:5, hearth_mini:3, kipclip_mini:4, hearth_full:3 | 2 | 0 |
| stock MLX mei `d35863fa1b50` | `d35863fa1b50` | `258148c2d48a` | 25 | full | 3 | 0 |
| stock MLX mei `d35863fa1b50` | `d35863fa1b50` | `0cb59d6a039f` | 25 | full | 5 | 0 |
| stock MLX mei `cfb4a5d79008` | `cfb4a5d79008` | `d2d191e25579` | 25 | full | 4 | 0 |
| stock MLX mei `e2770ac7d2c4` | `e2770ac7d2c4` | `3e8f2dbb5101+dirty` | 25 | full | 3 | 0 |
| text-only mei `0e7c3d44eade` | `0e7c3d44eade` | `d2d191e25579` | 25 | full | 2 | 0 |
| text-only mei `2e8b1d29956e` | `2e8b1d29956e` | `3e8f2dbb5101+dirty` | 25 | full | 0 | 0 |
| text-only mei `d39c29f2d74b` | `d39c29f2d74b` | `19250cc2f87b` | 25 | full | 1 | 0 |
| text-only mei `510c3d1a44eb` | `510c3d1a44eb` | `14cd77bf6b99` | 25 | full | 2 | 0 |
| text-only mei `4eacff1c767c` | `4eacff1c767c` | `14cd77bf6b99` | 25 | full | 1 | 0 |
| text-only mei `bf88c5f70b58` | `bf88c5f70b58` | `258148c2d48a` | 25 | full | 1 | 0 |
| text-only mei `271c7ee694e8` | `271c7ee694e8` | `258148c2d48a` | 25 | full | 1 | 0 |
| uncensored GGUF llama.cpp `6fa6f52fdc56` | `6fa6f52fdc56` | `6bb085a043fe` | 21 | sanity:2, hermes_ops:8, kiem_mini:5, hearth_mini:3, kipclip_mini:3 | 3 | 0 |
| uncensored GGUF llama.cpp `98fbff8ca864` | `98fbff8ca864` | `0adb046c1c3e+dirty` | 25 | full | 4 | 0 |

(The remaining stock/text-only/uncensored fragments below 25 rows are earlier
or partial legs; the full machine-derived inventory is reproducible with the
parse script pattern in §10. Total of the listed rows plus the remaining
smaller fragments = 916.)

**OptiQ eligibility read (Measured + Decision):** the OptiQ artifact is
**coding-only**: 15 rows at runner `b5b7f49bcb62` (hearth_full 3/3,
hearth_mini 3/3, kiem_mini 4/5, kipclip_mini 4/4; sole fail
`kiem_mini-testwrite`, `harness_error: false` — see §4) **plus** an earlier
5-row `kiem_mini` fragment at runner `f713b29fc5c7` (3/5). It has no
`hermes_ops` and no `sanity` rows under current methodology, so it is **not a
current 25-row eligible result** and cannot enter the headline tables.

## 3. Config identity / hash evidence (Measured)

- `configs/Qwen3.6-35B-A3B-OptiQ/mei.yaml` SHA-256:
  `31a7f0b6a256e0f316e6648415d3b515e37033d7e4d8f565ba53c033f365798c` → config
  hash `31a7f0b6a256`. `results/configs/31a7f0b6a256.yaml` is **byte-identical**
  (`cmp` → BYTE-IDENTICAL; same SHA-256); both files are tracked in git
  (`git ls-files` confirmed).
- Identity fields in that config:
  - `model`: `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`; orchestration
    `served_model_id`: the same string; `hermes_provider: bench-mei`;
    `needs_proxy: false` (native tool calls required); `viable: full`.
  - Pinned HF revision (`source_revision`):
    `70a3aa32c7feef511182bf16aa332f37e8d82014`
    (`~/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit/snapshots/70a3aa32c7feef511182bf16aa332f37e8d82014`).
  - `model_bytes`: 22155958660 (config's claim; locally verified — see §7).
  - Port **8024** (shared with Ornith / stock-Qwen3.6 / Nemotron Mei configs —
    never concurrent), `context_cap` 65536, `prefill_step_size` 512,
    temperature 0.6 / top-p 0.95 / top-k 20, `reasoning_mode: thinking`,
    `cache-reuse true`, max-tokens NOT set (0.5.0 auto profile applies 4096).
  - Safe controls (exact gate set, re-verified in the gate log):
    env `VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0
    BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0`; flags
    `--compiled-decode false --load-mmap false --memory-limit-bytes
    30000000000 --prefill-step-size 512 --context-cap 65536`; **no
    `--model-profile`** (a profiled wrapper run is the recorded OOM history).
    KV dir: `~/.local/share/local-model-bench/mei-runtime/kv-qwen36-optiq-safe`.
  - Build provenance: `mei_source_commit`
    `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` (Mei tag **v0.5.0**; gate binary
    reports `mei 0.5.0`) and `mei_commit`
    `44461ffdf8dca836b624b2d0d268c800dedea05e` (vmlx-swift pin read from the
    gate's scratch build `mei-build-qwen36-optiq-050/checkouts/vmlx-swift`).
- Control configs — current-file SHA-256 (live files; run-time config hashes
  above are the historical, snapshot-pinned values):
  stock Mei `configs/Qwen3.6-35B-A3B/mei.yaml`
  `5189920b6e9e5c64432e90004f6442036ac1756507ec893ffcc2bb2a0e99f8b0`;
  mixed46 `configs/Qwen3.6-35B-A3B-mixed46/mei.yaml`
  `8a1c098d128ed1419f065a1996feb74cf2ce75ccf3ad409028706564315c394c`; DWQ
  `configs/Qwen3.6-35B-A3B-DWQ/mei.yaml`
  `b0e7677bc6c285bd5729d5dead6cd65fca611e4ad959a70265ba11c11244b17f`; uncensored
  GGUF `configs/Qwen3.6-35B-A3B-Uncensored/gguf.yaml`
  `0a06644123474854ef9d94c946a94a2b4310f06e1a2c82215870aff56deeb3dc`; stock GGUF
  `configs/Qwen3.6-35B-A3B/gguf.yaml`
  `8a810c4258fb32f300d704d15a8b36a0038f4615963a9e2d862888bb11a4dfed`.

## 4. Raw/derived evidence paths and conclusions

All paths under `artifacts/` unless noted. Gates and canaries are
**functional evidence, NOT ranking evidence** — none of them appends a
`results/log.jsonl` row.

- **Deterministic six-task canary, 12/12 per leg** —
  `qwen36-deterministic-canary-20260914.md` + raw JSONL in
  `qwen36-deterministic-canary/` (2 identical trials × 6 tasks = 12 rows/leg;
  temperature 0, logprobs/top 5, reasoning hashes). 12/12 pass, 0 errors on
  all four 8192-cap legs: official GGUF Q4_K_M (`085886557e10`, llama.cpp,
  port 8017), stock MLX (`1447a232cb6f`), text-only MLX (`1447a232cb6f`),
  OptiQ MLX (`1447a232cb6f`, prefill 512, load-mmap false, 30 GB limit).
  Determinism: per-task `final_text_sha256`/`tool_calls_sha256` byte-identical
  between trials on every 8192 leg. The 4096-cap diagnostic llama leg
  (`3118f18eccc9`) had 2 `kiem_mini-testwrite` truncation errors — the
  motivation for the 8192 correction. **Canary ≠ ranking:** it launches no
  server and writes no benchmark rows.
- **OptiQ native gate + cache probes** —
  `qwen36-optiq-native-gate-20260914.json` (models/plain/stream/tool/
  tool_stream/cache_1/cache_2 all HTTP 200; exact served model ID on every
  response; native `get_weather` tool call on non-stream AND stream paths;
  `mei_memory_active_bytes` 23.09–23.18 GB under the 30 GB limit) and
  `qwen36-optiq-cache-probe-20260914.json` (growing-conversation cached_tokens
  0 → 1076 → 1092 → 1108 via the disk KV tier). Narrative:
  `qwen36-optiq-gate-20260914.md` — including the first **wrapper-run failure
  (do-not-hide)**: `--model-profile qwen3.6-35b-a3b-text` + mmap realignment of
  5/5 unaligned shards → **Metal Insufficient Memory**, `Trace/BPT trap: 5`;
  the safe control set (§3) is that post-mortem.
- **OptiQ 14/15 coding result** — `optiq-full-coding-20260914.md`: 15 rows at
  runner `b5b7f49bcb62` (2026-09-14T08:51–09:40Z), kiem_mini 4/5, hearth_mini
  3/3, kipclip_mini 4/4, hearth_full 3/3; the sole failure is
  `kiem_mini-testwrite` with `harness_error: false` (2/3 mutants killed, one
  survived — classified model behavior; same task also failed on the earlier
  kiem_mini leg). 15 transcripts in `results/transcripts/`.
- **mixed46 native probes** — `qwen36-mixed46-native-gate-20260914.md` +
  `.json`: served from the aligned repack; all probes PASS (identity, plain,
  stream parity 174/174, tool non-stream + stream, cache reuse chain,
  memory 20.01 GB active / 30 GB limit) **except** `context_exact_cap`
  (65536): `RemoteDisconnected` after 119.78 s — `Trace/BPT trap: 5`, server
  log ends at prefill `completed=44032 total=65536`,
  `MLX/ErrorHandler.swift:343 Fatal error: [METAL] Command buffer execution
  failed: Insufficient Memory`. The exact 65536-prefill dies with Metal OOM;
  **mixed46 is unranked** and the gate appended no rows. Note: the mixed46
  config's launcher still pins `VMLX_ENABLE_UNSAFE_COMPILE=1` — the gate ran
  the safe set; reconcile before any future coding run.
- **Official ggml-org control has visible failures** — the two GGUF fragments
  in `results/log.jsonl` (§2) are distinct: the **community**
  `unsloth …UD-Q4_K_XL` 21-row leg (3 fails; also kipclip_mini 3/4 and no
  hearth_full — pre-v3 suite row), and the **official** `ggml-org …Q4_K_M`
  5-row `kiem_mini` control leg with **3 fails including 2
  `harness_error: true`** at runner `19aee89cd756` (2026-09-13). The canary
  12/12 does not contradict this and does not rank the control either.
- Methodology/direction context: `qwen36-scheme-aware-*` (2026-09-14/15)
  artifacts record the scheme-aware ladder and the mlx-lm tooling pin
  (`21a03ff`); `qwen36-future-source-revision-check-20260915.md` records the
  bf16-source disk/tooling blockers (source not locally present).

## 5. Leaderboard / chart audit (Measured)

- **`results/LEADERBOARD.md`**: OptiQ appears ONLY in the all-groups
  (unranked/partial historical) table — `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit
  | mei | 31a7f0b6a256 | b5b7f49bcb62 | 15 | 93% | 1 fail` and
  `… | f713b29fc5c7 | 5 | 60% | 2 fail`, plus the per-suite detail rows
  (kiem_mini 4/5 at `b5b7f49bcb62`, 3/5 at `f713b29fc5c7`; hearth/kipclip 3/3,
  4/4). It is **not** in “Best overall” (eligibility there: sanity + FULL
  hermes_ops (8) + FULL coding (15), `benchmark-v2`-or-later runner SHA, and
  the usefulness gate).
- **`results/qwen36-mei-selection.json`** is a **three-fragment STOCK selection**
  (family Qwen3.6-35B-A3B, engine mei, `model_contains:
  mlx-community/Qwen3.6-35B-A3B-4bit`, config_hash `cea524483faf`, runners
  `de1d34279681` / `e5e8e82cdeb9` / `6a6d9f534804`) — the 2026-09-06 split
  leg, reconciled in `results/qwen36-mei-reconciliation-20260906.md`: combined
  25 rows, 22 pass, 15 coding rows, **1 `harness_error: true`
  (`hearth_mini-feature`)** → resolves **partial** (`synthetic_eligible=false`),
  not headline-admissible. It is **not OptiQ**.
- **`runner/build_summary_charts.py` behavior** (read from source this tick):
  - Headline charts `quality_vs_runtime.png` and `engine_delta.png` use only
    full-eligible groups: the leaderboard's “Best overall” keys PLUS curated
    multi-fragment combinations and explicitly pinned single fragments that
    clear the same real bar (full suite counts + zero harness errors).
    Missing/partial groups are not admitted; `engine_delta` additionally needs
    both a mei and a llama.cpp leg per family.
  - `suite_heatmap.png` / `runtime_breakdown.png` / `failure_taxonomy.png` can
    still render from selected partial data (rows labeled `(partial)`;
    harness-error rows excluded from per-suite pass rates).
  - The generator is output-only: it writes only the PNGs via `_save()` and
    never edits `LEADERBOARD.md`, `SUMMARY.md`, or any results row (module
    docstring, line 9–10).
- **Focused test command + result (recorded this tick, exit 0):**
  `uv run --locked python -m unittest discover -s runner/tests -p 'test_build_summary_charts.py' -v`
  → **Ran 42 tests in 1.574s — OK** (42/42 pass).
- **Isolated selection run (recorded this tick):**
  `uv run --locked python runner/build_summary_charts.py --selection results/qwen36-mei-selection.json --output-dir /tmp/qw-chart-test`
  wrote exactly **three** partial charts — `suite_heatmap.png` (1 group × 6
  suites), `runtime_breakdown.png`, `failure_taxonomy.png` (3 failure rows
  across 3 categories) — and **skipped `quality_vs_runtime`** (“no group had
  both a pass rate and recoverable runtime”) and **`engine_delta`** (“no family
  had both a pass-rate and runtime delta”). Output dir was system temp; no
  repo file was touched.

## 6. Public metadata audit — `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` (Measured, API + manifest)

Pinned Hub revision `d880b11584ae6ee1e18a1e86f082a8397cf2ce24`; read-only API
GETs and small metadata files only — **no weight payload downloaded**.

- **Identity**: id `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`; API
  `sha` == `d880b11584ae6ee1e18a1e86f082a8397cf2ce24`; `private: false`,
  `gated: false`; `pipeline_tag: text-generation`; created
  `2026-08-02T04:44:20Z`; **22 files** in the tree at that revision.
  Tags include: `mlx, safetensors, qwen3_5_moe, apple-silicon, quantized,
  mixed-precision, axquant, axq, stable-default-runtime, quality-validated,
  checkpoint-tier1, certified, qwen3.6, 4bit, 4-bit, v2, mtp, vision,
  text-generation, conversational, base_model:Qwen/Qwen3.6-35B-A3B,
  license:apache-2.0, region:us`.
- **Source identity**: manifest `source_model` =
  `Qwen/Qwen3.6-35B-A3B` @ `995ad96eacd98c81ed38be0c5b274b04031597b0`; the
  base repo was verified from the public API at that pinned revision: id
  `Qwen/Qwen3.6-35B-A3B`, `sha` == `995ad96eacd98c81ed38be0c5b274b04031597b0`,
  `private: false`, `gated: false`, tags `qwen3_5_moe` +
  `image-text-to-text`. **Base source identity verified at the pinned
  revision.**
- **Manifest** (`axquant_manifest.json`): `schema_version:
  "axquant.artifact.v2"`, `axquant_version 1.2.0`, `format mlx`, `profile
  general`, `target_class 4bit`, `quantizer axquant`.
  - `weight_file_size_bytes` = **23099321635** = sum of the 6 safetensors
    (4 main shards 20,516,858,235 + `vision.safetensors` 893,179,624 =
    `main_weight_file_size_bytes` 21,410,037,859; + `mtp.safetensors`
    1,689,283,776) — matches the Hub tree's safetensors total exactly.
  - **All manifest files** = **23120755753** (19 of the 22 repo files; the
    manifest excludes `.gitattributes` 1570, `axquant_manifest.json` 6849,
    `axquant_omlx_compat.json` 1249 → 23,120,765,421 − 9,668 =
    23,120,755,753 ✓ exact).
  - BPW: `effective_bpw 5.1400` (planned storage-adjusted),
    `measured_main_bpw 4.8788`, `measured_total_bpw 5.1401`.
  - `weight_distribution`: **4-bit 93.52% (33.62B params), 8-bit 1.47%
    (529.61M), bf16 5.01% (1.80B)**; group sizes 32/64, methods
    `affine,bf16`. `mtp_distribution`: bf16 100% (844.64M params, 19 tensors,
    1.69 GB); vision sidecar: 333 tensors, 446.57M params, 0.89 GB, BF16.
  - `mtp_present: true`; `mtp_policy`: protected mode, candidate bits 8/16,
    min 8; `mtp_acceptance_retention: null`; `mtp_measured_speedup: null`.
  - Claims carried (from README + runtime manifests — NOT locally measured):
    **standard MLX-LM text support, compatibility level B**
    (`axquant_runtime.json` compatible_runtimes → `mlx-lm`,
    `standard-inference`; notes: “Standard backbone inference is the
    compatibility target”, “AXQuant MTP metadata may be ignored by MLX-LM”);
    **primary AX Engine only** (`primary_runtime: ax-engine`, level A,
    manifest `model-manifest.json` — but README: “AX Engine native execution:
    not established; no validated native manifest is included”,
    `kernel_evidence: unmeasured`, and `model-manifest.json` is absent from
    the file tree); **MTP exactness/speed unverified, development-only**
    (README: “MTP acceleration Tier 2 is not certified” — agent ~0.95×/0.80×,
    long ~0.91×/0.93×; `mtplx_runtime.json`: `release_status
    development-only`, `exactness_baseline.status unverified`,
    `public_release_blocker true`); **vision present-not-certified**
    (README modalities table: `present-not-certified`, mlx-vlm smoke failed
    on df-macstudio-m2); **no Mei/vmlx compatibility claim anywhere**
    (compatible_runtimes lists only mlx-lm; oMLX/MTPLX import is documented
    via `axquant_omlx_compat.json` but explicitly “does not certify exactness
    or speed”). README also states calibration = none (architecture priors).
- **Hash/size spot checks**: the small metadata files fetched this tick
  (README.md 10,300 B; `axquant_runtime.json` 1,676 B; `mtplx_runtime.json`
  888 B; `axquant_mtp_sidecar_manifest.json` 1,066 B) have sha256/size
  **exactly matching the manifest's per-file entries**
  (`fe13ca9d…`, `66288788…`, `9f8e8c16…`, `0cd1522d…`). These four files were
  spot-checked against the public manifest; no weight payload was downloaded
  (other repo metadata was read via the Hub API, not fetched to disk).

## 7. Disk / local-cache gate (Measured)

- Host memory: `hw.memsize` = **34359738368** bytes (32 GiB).
- Free root: tick pre-check **23103844 KiB**; re-read at audit time
  **23102592 KiB** (`df -k /`; both ≈ 22.03 GiB) — consistent within noise.
- **AXQ payload is not locally cached**: the hub cache holds no AutomatosX
  entry (exactly five Qwen3.6 entries: EigenLabs mixed-4bit, ggml-org GGUF,
  mlx-community 4bit, 4bit-DWQ, OptiQ-4bit). Nominal complete download
  (manifest all files 23,120,755,753 B ≈ 21.53 GiB) against ≈ 22.03 GiB free
  leaves **~0.50 GiB (~0.54 GB)** before download scratch/safety. Combined
  with the metadata caveats in §6: **no AXQ download is authorized**, and the
  runner's own launch gate (`MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0` GB,
  `runner/bench_common.py:78`) would refuse it anyway.
- **Existing OptiQ snapshot is locally present** at the pinned path: 15
  snapshot entries (14 symlinks + `optiq/` dir); dereferenced total including
  `.gitattributes` = **22,155,960,230 bytes**; the config's `model_bytes`
  22155958660 equals that sum minus the 1,570-byte `.gitattributes` (exact).
  **Do not delete it** — it is outside this audit's scope and required for any
  future acceptance run.
- **Existing OptiQ runtime KV dir exists and is large**:
  `~/.local/share/local-model-bench/mei-runtime/kv-qwen36-optiq-safe` =
  10,372,820 KiB (~9.9 GiB, `du -sk`). **Warning (Measured):** the benchmark
  runner's `clear_kv_cache_dir()` (`runner/run_bench.py:301–364`) resolves
  every `--kv-cache-dir` in the config's launch command and
  `shutil.rmtree`s it before the run (called at `run_bench.py:543`); this
  config's KV path resolves inside `~/.local/share/local-model-bench`, so a
  cold benchmark run **would delete the existing KV directory**. That deletion
  is outside this audit's no-deletion scope — hence the non-destructive
  condition in §9.

## 8. Decision (this audit)

- **Decision 1 — single next experiment:** run exactly ONE existing-cache
  OptiQ acceptance benchmark leg. Justification: the OptiQ lane is the only
  Qwen3.6 scheme-aware candidate with a passing live gate, a gated 14/15
  coding fragment at the correct config hash, 12/12 canary determinism, and a
  locally complete pinned snapshot — a 25-row acceptance run is the remaining
  admission requirement.
- **Decision 2 — NOT a mixed46 runtime investigation:** the 65536-boundary
  Metal OOM is an open runtime blocker (`qwen36-mixed46-native-gate-…`: crash
  at prefill 44032/65536 under the 30 GB limit on this 32 GB host); mixed46
  also has a config/gate launcher divergence. Defer until the context-boundary
  is understood.
- **Decision 3 — NOT an AXQ download:** disk gate fails (~0.54 GB headroom),
  AXQ is absent from the local cache, and the published claims (level B
  MLX-LM text only; no validated native AX Engine manifest; MTP unverified /
  development-only; vision not certified; no Mei/vmlx compatibility) give no
  reason to trade the last disk headroom for it in this cycle.
- **Non-destructive condition (binding):** the current OptiQ config points
  `--kv-cache-dir` at the EXISTING `kv-qwen36-optiq-safe`, which the runner
  clears before a cold run. **Do not launch it until a narrow, committed
  acceptance config (or another explicitly verified fresh KV path) preserves
  the existing runtime cache and the model snapshot.** A fresh-KV acceptance
  config is a new committed file → new config hash; until then identity is the
  current `31a7f0b6a256`.

## 9. Next gate (planning authorization only)

This artifact **authorizes planning the next bounded run; NO run happened in
this tick** (no server started/stopped, no process, no KV clear, no download,
no push). When launched, the acceptance gate must satisfy all of:

- **Served identity/model**: `mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit`
  (exact `/v1/models` identity check); port **8024**, one Mei server only
  (shared-port rule).
- **Config identity**: current config hash **`31a7f0b6a256`** (byte-identical
  `results/configs/31a7f0b6a256.yaml`) until a future fresh-KV acceptance
  config is committed (then that config's own hash).
- **Pinned model/source/build**: snapshot revision
  `70a3aa32c7feef511182bf16aa332f37e8d82014`; Mei source
  `1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb` (v0.5.0) / vmlx
  `44461ffdf8dca836b624b2d0d268c800dedea05e`; the prebuilt
  `mei-build-qwen36-optiq-050` binary that produced the gate evidence (or a
  re-verified rebuild from that exact source state before use).
- **Expected result**: 25 rows = sanity 2 + hermes_ops 8 + kiem_mini 5 +
  hearth_mini 3 + kipclip_mini 4 + hearth_full 3; **no `+dirty` runner SHA**
  (clean committed tree at run time — `bench_common.py` appends `+dirty` when
  uncommitted changes exist; the config must be committed before the run).
- **Resource budget**: NO download (runner disk gate requires ≥ 30 GB free
  before launch; host has ~22 GB); memory limit 30,000,000,000 bytes; 32-GiB
  host. Abort/stop on: server load failure, served-identity mismatch, Metal
  OOM (`Trace/BPT trap` / Insufficient Memory), listener/process orphan (port
  8024 not freed), or any `harness_error` burst.
- **Safe controls (exact, non-negotiable)**: env
  `VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0
  BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0`; flags
  `--compiled-decode false --load-mmap false --memory-limit-bytes
  30000000000 --prefill-step-size 512 --context-cap 65536`; **no
  `--model-profile`**; KV dir = the new acceptance path (NOT the existing
  `kv-qwen36-optiq-safe`).
- **Full command** (explicit four coding suites; stage `all` default adds
  sanity + hermes_ops):
  `uv run --locked python runner/run_bench.py --config configs/<acceptance-or-current>/mei.yaml --coding-suites kiem_mini,hearth_mini,kipclip_mini,hearth_full`
- **Raw evidence requirements**: committed config snapshot
  (`results/configs/<hash>.yaml`), server stdout transcript
  (`/tmp/bench_*_server.log`), probe/identity capture, then the appended
  `results/log.jsonl` rows.
- **Teardown / post-run review**: `stop_mei_server.sh` + `unload_all.sh`
  (never touches CoCore; restore script is manual), port 8024 free; review
  row count == 25, zero harness errors, recorded config hash + runner SHA, and
  per-suite failures (expect the known `kiem_mini-testwrite` risk) before any
  leaderboard/chart regeneration.

## 10. Checks performed this tick

- `git status --short --branch` clean at the read-only audit checkpoint:
  HEAD `21a03ff12493299c6c4e58dca0a9dc24a55553d4` before report creation.
  The report was subsequently committed as
  `bb293dbefbb4f89eda2463d44af5d748afc9b2fd` and corrected as
  `d6f8c5d3e69ffabdbd18f9d4492993a569593453`, with only this artifact
  changed.
- Read-only evidence: `results/log.jsonl` parsed (4064/916/counts/groups —
  script pattern in `/tmp/qw_*.py`, nothing written to the repo); task YAML
  counts; `run_bench.py --help`; config SHA-256 + `cmp`; snapshot blob sizes;
  `df -k` / `sysctl hw.memsize`; `du -sk` KV dir; Hub API GETs + 4 small
  metadata files under `/tmp`; chart tests and the temp-output selection run.
- Files created: this artifact only (`artifacts/qwen36-decision-audit-20260915.md`).
  Nothing in `runner/`, `configs/`, `tasks/`, `checks/`, `fixtures/`,
  `results/log.jsonl`, `results/LEADERBOARD.md`, selection JSON, or any
  sibling repo was modified.
# Bonsai2 MLX Memory Remedy — Live Admission Gate, Bonsai Prism-Hadamard Slice `8c7df5b` (2026-09-24)

- Report date: 2026-09-24 (CEST, UTC+02:00)
- Unit: Bounded **live admission gate** for the default-off head_dim-256 Bonsai
  Prism-Hadamard slice pinned at vmlx commit `8c7df5b`: fresh isolated consumer
  build, one bounded server launch on the exact staged model, and a locked
  acceptance probe run against it. Report-only durable handoff — this commit
  adds exactly one artifact and nothing else.
- Status: **PASS (source/build gate and live capability admission).** No numeric
  fused-vs-dense parity, no three-repeat throughput / TTFT / end-to-end
  measurement, no tokenizer-clean context-quality claim, no benchmark rows or
  ranking, and no Mei-main or default-behavior change.
- Author note: effective worker route is provider `custom:umans`, model
  `umans-deepseek-v4-flash-0731`; this report was **not** authored by a profile
  named `umans-coder`.

## Scope / constraints honored

- Work confined to `/Users/tijs/projects/local-model-bench`; this commit adds
  only `artifacts/bonsai2-mlx-memory-remedy-live-gate-8c7df5b-20260924.md`.
- No build, server, probe, model run, benchmark, or cleanup was executed by this
  unit; all results below are supplied by the verified handoff and re-grounded
  read-only in the raw evidence on disk.
- `/Users/tijs/projects/vmlx-swift-bonsai-prism` (and its nested mlx / mlx-c
  pins) untouched and not committed. Mei main `/Users/tijs/projects/mei` was
  read-only and untouched; its only dirty state is the pre-existing untracked
  `Casks/kiem.rb` and `tap/`, which this unit neither touched nor claims to have
  changed.
- `results/log.jsonl`, `results/LEADERBOARD.md`, `results/`, `results-mei/`,
  `configs/`, `runner/`, and all model caches/weights untouched. No push.

## 1. Exact pins / identities (re-verified on disk this unit)

| Thing | Exact value |
|---|---|
| vmlx source root | `/Users/tijs/projects/vmlx-swift-bonsai-prism` |
| vmlx branch | `bonsai2-prism-hadamard-slice` |
| vmlx HEAD | `8c7df5bde37ae70ebde5ea8a286651c051be1b95`; checkout clean and unmodified |
| Nested `Source/Cmlx/mlx` | `bf8c9bf004a0e9786901b8c4d919419125a7f174` |
| Nested `Source/Cmlx/mlx-c` | `7bede8f1491384bb580f87d1d510f80cbd53660d` |
| Consumer export | `/Users/tijs/projects/mei-bonsai-prism-8c7df5b-20260924` (no `.git`); `Package.swift` local dependency path is exactly `/Users/tijs/projects/vmlx-swift-bonsai-prism`; `Package.swift` SHA-256 `462f2528dfbbd0190a87ca18c6a61e26a3d68acb9ba84575b7b65223bdadc5a7` |
| Fresh binary (built, hash captured) | SHA-256 `d0fec2c51ec07efe6928a8e898d2da1b54bbf5d464102ca94618beac01caf765`, size 89,526,336 bytes. **The generated SwiftPM scratch tree that held the build was removed after the live gate (see §8); do not assume the binary remains on disk.** |
| Model dir | `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit`, revision `3f926b415992eaa2ae9dd7b573706494d6bbf787` |
| `model.safetensors` | 8,595,477,990 bytes; SHA-256 `130de5925082c168b7866b2e91b52e44abbafc99017e3ca352b77b5b55a269ed` (re-verified on disk this unit) |
| Raw evidence dir | `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-8c7df5b-20260924T034458Z-live-admission/` |
| Host | macOS 27.0, arm64; device `applegpu_g13s`, 34,359,738,368 bytes |

## 2. Fresh consumer build gate

- Command: `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build -c release --product mei --scratch-path /Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-8c7df5b-20260924`.
- Result: exit 0, `Build complete` in 288.02 s. Captured fresh binary hash/size above (see `build.log`, `command.txt`).
- Verdict: **PASS (build-only).** No inference capacity claimed from a build.

## 3. Live admission run (one bounded server)

- Single server on `127.0.0.1:8027`, served id `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-mei-8c7df5b`, `--context-cap 65536`, `--prefill-step-size 1024`, `--max-tokens 4096`, `--cache-reuse true`, memory limit 24,051,816,857 B, cache limit 32,641,751,449 B, kv-cache dir inside the evidence dir, request logging to `request-log.jsonl`.
- Experiment env (default-off elsewhere) enabled **only for this isolated run**: `VMLX_BONSAI_PRISM_HADAMARD=1 VMLX_BONSAI2_SDPA_FULL_HD256=1 VMLX_ENABLE_UNSAFE_COMPILE=0`. This gate changed no default — everything else keeps the experiment off.
- `run-state.txt`: server pid 38034, ready 5 s after start, `exit_code=0`, clean end after ~1282 s uptime.
- `server.log` (verified): model loaded; **402 packed modules** installed from 1608 checkpoint keys (block 1024, 2-bit/group-128); 1-of-1 shard not naturally aligned warning (mmap realigned 1253 tensors / 6,834,034,688 B); prefix cache enabled (paged in-memory + disk) with topology `layers=64 kvLayers=16 mambaLayers=48 companion=ssm restore=disk-backed`; prefill progressed in 1024-token stages through the full 65536-token request and completed; **no runtime kernel-admission crash**.
- Decode on short requests was ≈ **15.3–15.9 tok/s** (`server.log` decode lines; probe `tokens_per_second` 15.34–15.91). These are bounded single-shot probe observations, **not** three-repeat throughput, TTFT, or end-to-end measurements, and confer no benchmark rank.

## 4. Probe result (locked acceptance probe)

Probe exit 0 (`probe.exit` = `probe_exit_code=0`); overall `probe.json` status **`passed`, 12/12 named probe entries** as accounted in the verified handoff, and every named probe key in `probe.json` reports `"status": "passed"`:

| Check | Observed | Result |
|---|---|---|
| Model identity | exact served id `…-mei-8c7df5b` | passed |
| Mei status | `applegpu_g13s`, 34,359,738,368 B device; memory/cache-limit reported | passed |
| Plain completion | content `ready` | passed |
| Stream vs nonstream parity | `parity-ok`; nonstream 15.34, stream 15.60 tok/s | passed |
| Native tool call, nonstreaming | `add_numbers` `{"a":15,"b":27}`, finish `tool_calls` | passed |
| Native tool call, streaming | `add_numbers` `{"a":15,"b":27}`, finish `tool_calls` | passed |
| Growing cache | turn1 828 prompt / 0 cached → turn2 851 prompt / **823 cached** | passed |
| Repeated cache | 6212 prompt / 0 cached → 6212 prompt / **6207 cached** | passed |
| Exact 65536 context | 65536 prompt tokens prefill completed; single completion token | passed |
| Over-cap 65537 | `HTTP 400: request exceeded context cap: 65537 prompt tokens > 65536 allowed` (`engine_error`/`invalid_request_error`), `rejected_as_expected` | passed |

## 5. Memory telemetry at the exact 65536-cap request (report only, no crash claim beyond what was seen)

- Request wall time **1171.061 s** (probe elapsed; request-log wall 1,170,524 ms).
- Telemetry at/after that request: **active 25,146,248,220 B**, **peak 27,292,882,384 B** on the 34,359,738,368 B device (peak ≈ 79.4% of device bytes; both values below device memory).
- The configured active limit for the run was 24,051,816,857 B and the exact-cap probe's reported active telemetry (25,146,248,220 B) is above it — this report **does not claim the configured active limit was never exceeded**. It reports only the telemetry above and the observed outcome: the server completed the exact-cap request and ended with `exit_code=0`, no crash.
- These are single-run telemetry observations, not a resource-budget certification.

## 6. Tokenizer warnings — qualify token-count/context and future quality claims

`probe.stderr.log` (repeated for both tool-call instantiations) contains transformers warnings:

1. `You are using a model of type 'prism_hadamard_qwen35' to instantiate a model of type ''` — model-type/architecture mismatch; checkpoints sharing only a subset of an architecture are otherwise unsupported and can yield errors.
2. `The tokenizer … with an incorrect regex pattern: …Mistral-Small-3.1-24B-Instruct-2503/discussions/84… will lead to incorrect tokenization` — set `fix_mistral_regex=True`.
3. PyTorch-not-found notice (tokenizers/config-only utilities still usable).

Therefore: **token counts, cache-token figures, and context-capacity results in this report are not tokenizer-clean quality claims**, and any future quality/proficiency statement must not build on them. A **tokenizer-correction follow-up** (regex fix + prism_hadamard_qwen35 model-type handling) is required before context-quality claims are valid.

## 7. Teardown and repository integrity (verified)

- Process/listener teardown independently verified: no owned mei/probe/swift processes; ports 8012, 8016, 8017, 8018, 8020, 8024, 8025, 8026, 8027 free.
- `/Users/tijs/projects/local-model-bench` git status clean before and after (HEAD `3f289f68aa474e843cb28f734c3ea58be7459283` until this commit).
- `results/log.jsonl` unchanged (mtime Sep 23 08:05): it still ends with exactly the two old interrupted PTQ1_0 GGUF sanity rows (config hash `5b760871ce84`); **zero MLX rows**; no `results/LEADERBOARD.md`, config, or result changes.

## 8. Disk accounting and exact cleanup boundary

- Free bytes: 11,232,382,976 at unit start → 11,148,615,680 before admission → 9,117,597,696 after the exact-cap probe → **11,340,836,864 after removing only the consumed generated SwiftPM scratch tree** (`/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-8c7df5b-20260924`, which held the built binary and its out tree). Post-cleanup free space is **above 10 GiB** (re-checked at report time: 11,519,471,616 B ≈ 10.73 GiB).
- The scratch tree was the only thing removed — the boundary is exact: generated SwiftPM scratch output is disposable and was consumed; everything else (model weights, consumer export dir, evidence dir, and the live **kv-cache** at `…/prism-8c7df5b-20260924T034458Z-live-admission/kv-cache/` — 6 `.safetensors` + `ssm_companion` + `cache_index.db`) remains preserved.

## 9. Verdict

**Passed:** source/build gate (fresh consumer build, exit 0) and live capability admission (12/12 named probe entries, exact-65536 context prefill completed, over-cap rejected, growing/repeated prefix cache reuse, native tool calls, clean teardown, no runtime kernel-admission crash).

**Not covered / explicitly not claimed:**
- no numeric fused-vs-dense parity measurement;
- no three-repeat throughput, TTFT, or end-to-end measurement (decode ≈15.3–15.9 tok/s is bounded probe observation only);
- no tokenizer-clean context-quality claim (see §6);
- no benchmark rows or ranking — this report is evidence, not `results/log.jsonl` data;
- no Mei-main or default-behavior change — the experiment env was enabled only for this isolated run.

## 10. Evidence

- Raw evidence: `/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-8c7df5b-20260924T034458Z-live-admission/` — `command.txt`, `run-state.txt`, `probe.json`, `probe.exit`, `probe.stdout.log`, `probe.stderr.log`, `server.log`, `request-log.jsonl`, `health.json`, `health.stderr`, `build.log`, `run_admission.sh`, `kv-cache/`.
- This artifact: `artifacts/bonsai2-mlx-memory-remedy-live-gate-8c7df5b-20260924.md`, initially committed at `63a0a47b2b145a3dc60bc28e02651f2f79ab308d` (parent HEAD `3f289f68aa474e843cb28f734c3ea58be7459283`+1) and finally corrected to the verified 12/12 named probe total at `303c780701a752d3f8f13d7d68388f281fc04a9b`.
- Effective worker route: provider `custom:umans`, model `umans-deepseek-v4-flash-0731` (not `umans-coder`).
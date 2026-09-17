# AutomatosX AXQ 6-bit Mei native gate — 3600 s probe timeout (BLOCKED), 2026-09-17

Authorized AXQ6 leg of Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`. Candidate
`AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP` at immutable revision
`bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`. This note records the failed native
admission gate only — the 25-row benchmark was NOT started and has no evidence.

## Verdict: BLOCKED / INCOMPLETE

The native gate did NOT pass. No 12/12 probe result exists: the probe
subprocess timed out after 3600 seconds before producing `probe.json`, so the
gate record is `status: "error"` and the acceptance battery was correctly not
started.

## Raw evidence (authoritative)

- `/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260917T204408Z/record.json`
- `/Users/tijs/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei-20260917T204408Z/launcher.log`

The raw run directory contains ONLY these two files — there is no
`probe.json` and no `server-run.log`. `record.json` is authoritative:
`status: "error"`, `error:
TimeoutExpired: Command '[.../runner/probe_mei.py --base-url
http://127.0.0.1:8025/v1 --model AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP
--tokenizer .../mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP --output
.../probe.json --context-cap 65536]' timed out after 3600 seconds`,
`started_epoch 1789677848.5053408` → `finished_epoch 1789681484.770954`
(exactly 3600 s). Config referenced: `configs/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP/mei.yaml`.

## Staging / provenance facts (all verified for this note)

- Repo `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`, revision
  `bc8b9a1d4b0d9da6a3cf0dcd0836da4713e52924`, staged at
  `~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`.
- Immutable tree: **23 files, 26,985,603,183 bytes** (re-verified here:
  `find -maxdepth 1 -type f` → 23, byte-sum 26,985,603,183). The extra 47
  small files / 2,495 B inside `.cache/huggingface/download` are HF download
  bookkeeping, not part of the immutable tree (a full-dir `find -type f`
  therefore returns 70 files / 26,985,605,678 B).
- `axquant_manifest.json` carries **20 SHA-256 file records** (`.files` length
  confirmed 20); all 20 independently PASS (sizes + hashes, including all five
  main safetensors, mtp.safetensors, vision.safetensors). HF API tree
  names/sizes at the pin match the staged tree.
- Provenance sidecar (tool-generated, preserved verbatim)
  `mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP.provenance.json`:
  `verify.ok` is `false` ONLY because the index-only weight-set check does not
  expect `mtp.safetensors` / `vision.safetensors` (reasons:
  `unexpected weight file mtp.safetensors`, `unexpected weight file
  vision.safetensors`) — both are pinned-revision module files and both
  validated PASS in the independent manifest verification. The main 5-shard
  verify reports: `shard_bytes`/`file_bytes` **24,381,678,655**,
  `payload_total`/`index_total` **24,381,442,816**, `header_overhead_bytes`
  235,839, `has_index` true, `arch` **Qwen3_5MoeForConditionalGeneration**,
  `model_type` **qwen3_5_moe**, `quant_bits` **4** / `quant_group_size` **32**
  / `quant_mode` **affine**, `config_sha256`
  30898a68ce3c1dc40ef83ae9ca8606013e97e1a6e9281409c9351395e4ff03ba,
  `loadability` "NOT CHECKED (GPU-gated)". Sidecar pinned/resolved commit ==
  the stated revision; staged_at 2026-09-17T20:25:45.546846Z.

## Launch (safe; preserved from record.json `command` + launcher.log)

```
env VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0 \
bash runner/start_mei_server.sh --model-dir ~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP \
  --served-model-id AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP --port 8025 --context-cap 65536 \
  --kv-cache-dir ~/.local/share/local-model-bench/mei-runtime/kv-axq6-mtp --memory-limit-bytes 30000000000 \
  --prefill-step-size 512 --compiled-decode false --load-mmap false --enable-thinking true \
  --temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true --cache-reuse true \
  --build-dir ~/.local/share/local-model-bench/mei-build-qwen36-optiq-050 --mei-repo ~/projects/mei
```

Safe controls confirmed: `VMLX_ENABLE_UNSAFE_COMPILE=0`,
`BENCH_NO_FUSED_GATE_UP=1`, `MLX_SAFETENSORS_MMAP=0`; `--enable-thinking true`,
`--compiled-decode false`, `--load-mmap false`, `--memory-limit-bytes
30000000000`, context cap 65536, prefill step 512, KV path `kv-axq6-mtp`,
served model ID exactly `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-6bit-MTP`.
launcher.log: isolated launch of the PREBUILT 0.5.0 binary
`mei-build-qwen36-optiq-050/release/mei`; `mlx.metallib already present and
verified` (no rebuild); listener port 8025.

## Load (parent-verified run telemetry; not persisted in the gate raw dir)

Mei loaded the model successfully: `active 24,401,171,724` bytes under the
`30,000,000,000`-byte limit; device memory 34,359,738,368 bytes (32 GiB);
recommended working set 26,800,603,136 bytes. The gate raw dir retains only
launcher + record JSON and no server stdout, so the load line cannot be
re-derived from the raw paths; it is recorded here as parent-verified.

## Teardown (verified for this note)

- No benchmark/model process: `pgrep -fl 'mei|probe_mei'` → 0.
- No listener on port 8025: `lsof -nP -iTCP:8025 -sTCP:LISTEN` → 0.
- Only the disposable KV artifact remained:
  `~/.local/share/local-model-bench/mei-runtime/kv-axq6-mtp/`
  `cache_index.db` 4,096 + `cache_index.db-wal` 20,632 + `cache_index.db-shm`
  32,768 = **57,496 bytes**.

## Source/build reproducibility discrepancy — FOLLOW-UP before rerun

- Config metadata pins `mei_source_commit: 1518e7010875ff5fdfca2cfc29bb4a4f3bf31aeb`
  (Mei tag v0.5.0, the shipped baseline the gate binary reports as `mei 0.5.0`).
- The launcher was invoked with `--mei-repo /Users/tijs/projects/mei`, whose
  source HEAD is `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` (re-verified here:
  `git -C ~/projects/mei rev-parse HEAD`).
- This discrepancy is NOT hidden: the gate used the prebuilt verified 0.5.0
  scratch binary in `mei-build-qwen36-optiq-050` (binary therefore matches the
  pin), but the live repo HEAD differs from the pinned commit and the config
  itself flags it (`~/projects/mei is currently at 950e8c2f (NOT tag ...)`).
  Reconcile repo HEAD vs `mei_source_commit` pin before any rerun.

## Re-run precondition

Investigate the probe hang (no probe.json in 3600 s despite successful load),
resolve the source-commit discrepancy above, then rerun the native gate. Do
not start the 25-row benchmark until the gate produces a real 12/12 result.
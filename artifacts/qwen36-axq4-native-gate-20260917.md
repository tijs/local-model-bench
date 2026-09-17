# AutomatosX AXQ 4-bit Mei native gate — detailed live evidence, 2026-09-17

Candidate `AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP` at pinned revision
`d880b11584ae6ee1e18a1e86f082a8397cf2ce24`, staged at
`~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`
(22 files, 23,120,765,421 B). Gate ran on the VERIFIED prebuilt Mei 0.5.0
binary `mei-build-qwen36-optiq-050/release/mei` (`mei 0.5.0`; vmlx `44461ffd`
verified in its checkout 2026-09-17), port 8024, endpoint
`http://127.0.0.1:8024/v1`. **Gate evidence only — the full 25-row benchmark
result for this candidate is recorded in the companion note
`artifacts/qwen36-axq4-full-coding-20260917.md`.**

## Result: PASS (12/12 probes)

Full raw probe JSON (all probes `passed`, exit 0):
`~/.local/share/local-model-bench/results-mei/AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP/mei-20260917T072017Z/`
— `probe.json`, `record.json`, `launcher.log`, `server-run.log`.

| Probe | Result | Notes |
| --- | --- | --- |
| models_identity | PASS | served ids `['AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP']` — EXACT |
| mei_status | PASS | activeBytes 20,536,358,156, limit 30,000,000,000, recommended working set 26,800,603,136, device applegpu_g13s |
| plain_completion | PASS | 11.5 s |
| parity_stream_vs_nonstream | PASS | content + prompt_tokens identical both paths (7.9 s) |
| tool_nonstreaming | PASS | add_numbers call validated (5.3 s) |
| tool_streaming | PASS | add_numbers call validated (4.4 s) |
| cache_repeat_1 / cache_repeat_2 | PASS | 16.0 s / 0.7 s |
| cache_growing_turn1 | PASS | cached_tokens 0 (fresh prefix) |
| cache_growing_turn2_reuses_slot | PASS | cached_tokens 785 of 809 prompt tokens (0.7 s) |
| context_exact_cap | PASS | 65,536 prompt tokens, prefill 283.2 s (~231 tok/s), completed 1 token; per-request active 23,795,621,138 B / peak 26,570,342,036 B, under the 30 GB limit |
| context_over_cap_rejected | PASS | 65,537 tokens rejected HTTP 400 as expected (1.3 s) |

Per-request memory evidence (usage payloads in probe.json): plain/tool probes
report `mei_memory_active_bytes` 21.2 GB with `mei_memory_peak_bytes` 22.2 GB;
the 65,536-token context probe peaks at 26.57 GB — all under the fixed
30,000,000,000 B allocator limit on the 32 GiB machine.

## Load profile (server-run.log, gate server stdout segment)

```
[Load] dtype-materialisation bf16=true mmap=false ... params[bfloat16=1497 uint32=431]
[Load] dtype-materialisation bf16=true mmap=false ... params[bfloat16=1164 uint32=431]
[MLXPressMmapTier] lazy-built: sniffed 6 shards, mmap'd 4, skipped 2 (no routed experts)
mei: prefix cache enabled (paged in-memory + disk at .../mei-runtime/kv-axq4-mtp); topology layers=40 kvLayers=10 mambaLayers=30 companion=ssm restore=disk-backed
mei: model loaded
mei: memory after load: active 20536358156 cache 0 peak 0 bytes; limit 30000000000 cache-limit 32641751449
mei: listening on http://127.0.0.1:8024 (context cap 65536, prefill step 512, max-tokens 8192, kv-bits none)
mei: optimization profile ornith (requested auto, prefill 512, compiled-decode false, kv-window 0, ssm-anchors 0)
mei: profile applied max-tokens 8192, unsafe-compile 0, fused-gate-up-limit 0
mei: WARNING 3 of 6 weight shards are not naturally aligned ...
```

Key facts: weights materialized (mmap=false, MLX_SAFETENSORS_MMAP=0), 6 weight
shards sniffed (4 main + mtp + vision), 3/6 unaligned (the mmap=false choice
avoids the realignment copy tax), auto profile applied (prefill 512,
compiled-decode false, unsafe-compile 0, fused-gate-up-limit 0, max-tokens
8192), disk KV tier live on the configured path.

## Controls (exact launch line; proven via wrapper --dry-run and launcher.log)

```
env VMLX_ENABLE_UNSAFE_COMPILE=0 VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES=0 BENCH_NO_FUSED_GATE_UP=1 MLX_SAFETENSORS_MMAP=0 \
bash runner/start_mei_server.sh --model-dir ~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP \
  --served-model-id AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP --port 8024 --context-cap 65536 \
  --prefill-step-size 512 --kv-cache-dir ~/.local/share/local-model-bench/mei-runtime/kv-axq4-mtp \
  --memory-limit-bytes 30000000000 --compiled-decode false --load-mmap false \
  --temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true --cache-reuse true \
  --build-dir ~/.local/share/local-model-bench/mei-build-qwen36-optiq-050 --mei-repo ~/projects/mei
```

No `--model-profile`, no unsafe compiled decode, explicit cache/KV settings.
Wrapper echo confirmed every flag reaches the binary verbatim.

## Staging / provenance facts

- Stage tool: `/Users/tijs/projects/mei/tools/stage_mlx_checkpoint.py` with
  `--repo AutomatosX/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP --revision
  d880b11584ae6ee1e18a1e86f082a8397cf2ce24 --target
  ~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP`
  (run with a dedicated staging venv `mei-stage-venv`, huggingface_hub 0.26.2,
  because the repo uv lock's hf 1.24 removed the `local_dir_use_symlinks`
  kwarg the tool passes; Mei tool unmodified, ~/projects/mei untouched).
- Tool-generated provenance sidecar preserved VERBATIM:
  `~/.local/share/local-model-bench/mei-models/AX-Qwen3.6-35B-A3B-MLX-AXQ-4bit-MTP.provenance.json`.
  Verify block: 4 index-mapped shards, shard_bytes/file_bytes 20,516,858,235,
  payload_total 20,516,621,952, header overhead 236,283, has_index true, arch
  Qwen3_5MoeForConditionalGeneration, model_type qwen3_5_moe, quant_bits 4,
  quant_group_size 32, quant_mode affine, config_sha256
  13953be5a055f1aa219fdd7bb9c0125cd4b1fcc66c39b10dbba7cf3cdcc3a830 (==
  axquant_manifest.json's own config.json sha256). NOTE: verify `ok` is
  `false` with reasons `unexpected weight file mtp.safetensors` /
  `vision.safetensors` — the tool's index-only weight-set check predates
  multi-module AXQ bundles; both files are pinned-revision components and both
  containers validated PASS in the independent `verify_axq4_tree.py` check
  (all 6 .safetensors). The sidecar was generated once and never rewritten.
- Independent tree check: all 22 files byte-exact vs the HF API listing at the
  pin (total 23,120,765,421 B); 6/6 safetensors containers valid.

## Build provenance

- `mei-build-qwen36-optiq-050/release/mei --version` → `mei 0.5.0`
- `git -C mei-build-qwen36-optiq-050/checkouts/vmlx-swift rev-parse HEAD` →
  `44461ffdf8dca836b624b2d0d268c800dedea05e` (the 0.5.0-shipped pin, matching
  `mei_source_commit` 1518e701's Package.resolved per the OptiQ record).
- Gate and benchmark both ran the SAME prebuilt binary (launcher/build lines:
  "mlx.metallib already present and verified"; no rebuild). The dirty
  ~/projects/mei working tree (HEAD 950e8c2f, untracked Casks/ tap/) was NOT
  built from.

## Teardown

Server stopped via `runner/stop_mei_server.sh` after the probes; port 8024
verified free; `mei-runtime/server.pid` removed. The runner's own benchmark
leg repeated the identical load and tore down its own server afterwards.
# Bonsai2 MLX Memory Remedy — Live Admission Gate (2026-09-24)

- Report date: 2026-09-24 (CEST, UTC+02:00); evidence window 2026-09-24
  T00:12:06Z live-admission attempt (epochs 1790208821–1790208829).
- Unit: One live, bounded admission attempt of the exact committed source/build
  unit (`local-model-bench` HEAD `5e03c0d`) — the fresh Mei consumer binary
  built against vmlx `746d1c47` — against the staged Bonsai2 2-bit model, with
  the head_dim-256 SDPA experiment control enabled.
- Status: **BLOCKED at runtime kernel admission.** The server loaded the model,
  `/v1/models` identity and `/mei/status` probes passed, but the first plain
  request crashed the server process (Trace/BPT trap) because the generated
  full-attention kernel `steel_attention_..._bd256...` demands 53,760 bytes of
  threadgroup memory while the host GPU (applegpu_g13s) allows at most 32,768.
  This is a **kernel-admission runtime blocker, not a 32 GiB long-context OOM
  result, and not a benchmark row.** No numeric parity, capacity, or ranking
  claim is made by this unit.
- Author note: the parent session requested the named `umans-coder` profile,
  which was unavailable (HTTP 403 seat-unavailable); this report was authored
  by the configured fallback delegated worker, **not** the `umans-coder`
  profile, and is not an `umans-coder` run.

## 1. Exact inputs

| Thing | Exact value |
|---|---|
| Source/build unit | `local-model-bench` HEAD `5e03c0d` (`5e03c0d7dad588d31b8b12ddaf9881911bf50967`), commit `research: record Bonsai2 MLX head-dim-256 remedy source and consumer build gates (746d1c47)` |
| Binary | `/Users/tijs/.local/share/local-model-bench/mei-build-bonsai2-prism-746d1c47-20260924/out/Products/Release/mei` — 89,529,696 bytes, mtime 2026-09-24 02:03:47 CEST, SHA-256 `2fe43a775c8c47781043eaeb8d68dd090ce4b378ad6f35ffa0b37f3495845b28` (re-verified on disk this unit) |
| vmlx pin | `746d1c47f89db29c33ea1174e01e35fc219d5b01` (`/Users/tijs/projects/vmlx-swift-bonsai-prism`, branch `bonsai2-prism-hadamard-slice`) |
| Nested MLX pin | `a2829e90878a7354f2668831af1409b3972a3c2f` |
| Model | `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit` @ revision `3f926b415992eaa2ae9dd7b573706494d6bbf787`, served as `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-mei-746d1c47`; dir `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit` |
| model.safetensors | 8,595,477,990 bytes; SHA-256 `130de5925082c168b7866b2e91b52e44abbafc99017e3ca352b77b5b55a269ed` (re-verified on disk this unit) |
| Host | macOS 27.0, arm64; GPU device `applegpu_g13s`, 34,359,738,368 bytes (32 GiB); recommended working set 26,800,603,136 bytes |
| Explicit limits | `--memory-limit-bytes 24051816857`, `--cache-limit-bytes 32641751449`, `--context-cap 65536`, `--prefill-step-size 1024`, `--max-tokens 4096`, `--compiled-decode false`, `--load-mmap true` |
| Env | `VMLX_BONSAI_PRISM_HADAMARD=1`, `VMLX_BONSAI2_SDPA_FULL_HD256=1` (experiment control, enabled only for this isolated admission), `VMLX_ENABLE_UNSAFE_COMPILE=0`; compiled-decode false |
| Admission script | `run_admission.sh` (recorded, exact command in `command.txt`); server `127.0.0.1:8027`; probe `runner/probe_mei.py` via `/opt/homebrew/bin/uv run --locked` |

## 2. Measured outcome

Timeline (run-state.txt, server.log, probe.json):

1. Server start `started_epoch=1790208821`, `server_pid=26834`, ready
   `ready_epoch=1790208825`.
2. **Loaded** — `server.log`: `mei: model loaded`; memory after load active
   7,616,367,636 bytes, cache 0, peak 0; load realigned 1253 unaligned tensors
   (6,834,034,688 bytes) via mmap; 402 packed modules installed; prefix cache
   enabled (paged in-memory + disk at the run's `kv-cache/`).
3. **identity/status passed** — `health.json` returned the model list;
   `probe.json` `models_identity`: passed (served id
   `prism-ml/Ternary-Bonsai-2-27B-mlx-2bit-mei-746d1c47`); `mei_status`:
   passed (memory limit 24051816857, cache limit 32641751449 as configured).
4. **First plain request failed** — `server.log`:
   `mei: chat request tokens 57`, `pp stage=prefill completed=0 total=57`, then
   `MLX/ErrorHandler.swift:343: Fatal error: [metal::Device] Unable to load
   kernel steel_attention_float32_bq32_bk16_bd256_wm4_wn1_maskfloat32_align_Q_n_align_K_n_has_mask_n_do_causal_t_has_sinks_n`;
   `Threadgroup memory size (53760) exceeds the maximum threadgroup memory
   allowed (32768)`; `at …/vmlx-swift-bonsai-prism/Source/Cmlx/mlx-c/mlx/c/transforms.cpp:73`.
   Process exited with **Trace/BPT trap** (run-state `exit_code=1`, server
   ended `ended_epoch=1790208829`).
5. **Probe outcome: failed** — `probe.json`: `plain_completion` failed with
   `RemoteDisconnected: Remote end closed connection without response`
   (elapsed 1.22 s); every later probe failed with connection refused
   (`URLError [Errno 61]`); overall `status: failed`; `probe.exit` = 1.
6. `request-log.jsonl` is empty (0 bytes) — no request was logged server-side.

The kernel name identifies the exact regular full-attention Steel instantiation
(bq32 / bk16, **bd256**, wm4/wn1, mask float32, no Q/K aliasing
`align_Q_n`/`align_K_n`, causal `do_causal_t`, no sinks `has_sinks_n`) compiled
per admission pin
`a2829e90878a7354f2668831af1409b3972a3c2f`; MLX demands 53,760 bytes of
threadgroup memory for it, above the 32,768-byte hardware maximum — hence the
Metal device refuses to load it at first prefill use.

## 3. Classification

- **Remedy gate: BLOCKED — runtime kernel admission failure.** The head_dim-256
  full-attention kernel compiled and was admitted by the source/build gates, but
  is **not loadable on the host GPU** because its threadgroup memory footprint
  (53,760 B) exceeds the applegpu_g13s maximum (32,768 B).
- **Explicitly NOT** an out-of-memory failure: memory after load was ~7.6 GiB
  active against a 24,051,816,857-byte limit, and the crash happened at first
  kernel load during prefill stage with `completed=0` — before any
  long-context/kv growth. It is not a 32 GiB long-context OOM result.
- Not a benchmark result: no rows were written to `results/log.jsonl` or
  `results/`; the admission wrote only to its own `results-mei/...` evidence
  directory. **No benchmark rows or ranking claim exist.**
- **No numeric parity or capacity-improvement claim**: no fused-vs-dense parity,
  no throughput, no long-context capacity number is asserted anywhere in this
  unit.

## 4. Independent unverified quality boundary (not the blocker)

`probe.stderr.log` contains HuggingFace `transformers` tokenizer warnings while
loading the tokenizer from the model dir: an architecture-name mismatch notice
(`prism_hadamard_qwen35` vs unknown instantiation type) and an incorrect-regex
warning for the Mistral tokenizer (reference:
`huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503/discussions/84#69121093e8b480e709447d5e`,
`fix_mistral_regex=True` remediation). These are **independent, unverified
tokenizer-quality signals and must not be conflated with the runtime crash** —
the crash cause is the kernel threadgroup-memory refusal in `server.log`, not
the tokenizer warnings. Whether the tokenizer actually mis-tokenizes this model
remains unverified and is out of scope for this gate.

## 5. Evidence paths (raw, external, untouched)

`/Users/tijs/.local/share/local-model-bench/results-mei/Ternary-Bonsai-2-27B-mlx-2bit/prism-746d1c47-20260924T001206Z-live-admission/`:
`command.txt`, `run_admission.sh`, `run-state.txt`, `server.log`, `health.json`,
`health.stderr`, `request-log.jsonl`, `probe.json`, `probe.exit`,
`probe.stdout.log`, `probe.stderr.log`, `kv-cache/cache_index.db*`.
Prior gate artifact (read during this unit):
`artifacts/bonsai2-mlx-memory-remedy-source-and-consumer-gate-20260924.md`.
This commit adds only `artifacts/bonsai2-mlx-memory-remedy-live-gate-20260924.md`.

## 6. Preserved boundaries / teardown

- **No process or listener remains**: no listener on `127.0.0.1:8027`; no
  `mei`/`probe_mei`/swift-build/model process running (verified this unit).
  The server exited on its own via the trap; the admission script's cleanup
  trap recorded `exit_code=1`.
- **Disk below 10 GiB** after the attempt — verified this unit: `df` shows
  10,199,700 KB free ≈ **9.7 GiB**, under the 10 GiB line. **No retry was
  launched**; a retry would risk exhausting disk and is out of scope.
- **No configuration, runner, model weights, `results/`, `results/log.jsonl`,
  LEADERBOARD.md, or external state was modified** by this unit; the only write
  is this artifact. `git status --porcelain` clean before and after (apart from
  the new artifact).
- `/Users/tijs/projects/vmlx-swift-bonsai-prism` and `/Users/tijs/projects/mei`
  were **not touched** (read-only references only).
- The prior build/artifact evidence (`mei-build-bonsai2-prism-746d1c47-20260924`
  binary and scratch) remains as-is; no cleanup was performed by this unit.

## 7. Next bounded action

1. **CPU/source audit** of the full-attention Steel kernel family for a smaller
   legal shape: e.g. reduce the bd256 tile (or wm/wn split) so the worst-case
   threadgroup allocation fits under the 32,768-byte maximum (target ≪ 53,760 B
   for `bq32_bk16_bd256`), or otherwise source-review a kernel-memory remedy
   (smaller block-dim, split-K, or a different admission table entry) that
   passes the Metal device's threadgroup-memory check.
2. **Fresh consumer rebuild** of the Mei binary against the corrected source
   before any retry — never reuse this crashed binary or stale scratch.
3. Only then consider a fresh bounded admission, still non-rankable, and still
   with the disk caveat: disk is below 10 GiB, so storage headroom must be
   restored before any retry.
4. Separately (out of scope here): the tokenizer warning is an open quality
   boundary to verify before any future inference-quality claims.

No benchmark rows, ranking, parity, or capacity improvement is claimed by this
unit.
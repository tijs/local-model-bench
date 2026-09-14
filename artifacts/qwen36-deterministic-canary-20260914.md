# Qwen3.6-35B-A3B deterministic canary — archived evidence, 2026-09-14

Scope: a **six-task deterministic functional canary** (2 identical trials × 6 tasks =
12 trial rows per leg), **not** a 25-row leaderboard score. The canary
(`runner/canary.py`) launches no server and never writes `results/log.jsonl`;
this archive adds only the raw JSONL copies below plus this summary. No
benchmark row, leaderboard file, config, or source line was modified or
re-ranked.

Suite (fixed order, task text verbatim from `tasks/*.yaml`): `sanity-basic`,
`hermes_ops-chaining`, `hermes_ops-noisy-result`, `kiem_mini-feature`,
`kiem_mini-testwrite`, `canary-multi-turn`. All requests: temperature 0
(greedy), explicit `max_tokens`, `max_turns` 6, logprobs/top_logprobs requested
(top 5). `grading: full` for the four prompt tasks; `canary_response_only`
(response-sanity only — no fixture, so no cargo/mutation gate) for the two
fixture-derived `kiem_mini-*` tasks, whose PASS means a substantive on-topic
response carrying the fixture identifiers, not the real benchmark gate.

## Legs and outcomes (counts re-verified by parsing every row, not transcribed)

| leg | artifact (in `artifacts/qwen36-deterministic-canary/`) | runner_git_sha (run header) | cap | window (UTC) | rows | passed | failed | errors |
|---|---|---|---|---|---|---|---|---|
| llama.cpp official GGUF Q4_K_M | `qwen36-matched-llama-canary-8192-20260914.jsonl` | `2a5e70108202` | 8192 | 10:39:53–10:48:09Z | 12 | 12 | 0 | 0 |
| llama.cpp diagnostic (pre-fix, 4096 cap) | `qwen36-matched-llama-canary-20260914.jsonl` | `3118f18eccc9` | 4096 | 10:31:37–10:39:24Z | 12 | 10 | 0 | 2 |
| stock MLX (`mlx-community/...-4bit`) | `qwen36-matched-stock-canary-8192-20260914.jsonl` | `1447a232cb6f` | 8192 | 10:56:56–11:09:41Z | 12 | 12 | 0 | 0 |
| text-only MLX (`Tostibrown/...-4bit-textonly`) | `qwen36-matched-textonly-canary-8192-20260914.jsonl` | `1447a232cb6f` | 8192 | 11:11:17–11:21:45Z | 12 | 12 | 0 | 0 |
| OptiQ MLX (`mlx-community/...-OptiQ-4bit`) | `qwen36-matched-optiq-canary-8192-20260914.jsonl` | `1447a232cb6f` | 8192 | 11:23:42–11:34:12Z | 12 | 12 | 0 | 0 |

Summary rows' `completed: true` in all five artifacts; recomputed
pass/fail/errors agree with the recorded summary in every file. The 4096-cap
diagnostic's two errors are both `kiem_mini-testwrite` trials,
`error_kind: "truncated"` (`finish_reason: length` at exactly 4096 completion
tokens) — the cap that motivated the 8192 corrected runs; the 8192 llama leg
then passed that task.

## Per-task comparison (no ranking)

| task | llama-8192 | stock | text-only | OptiQ |
|---|---|---|---|---|
| `sanity-basic` | ✅ | ✅ | ✅ | ✅ — final hash `73475cb4…` **identical on all four legs** ("42") |
| `hermes_ops-chaining` | ✅ | ✅ | ✅ | ✅ — llama & OptiQ share final-text hash `4bb52b62…`; text-only & OptiQ share tool-call hash `caf1efa9…`; stock differs on both |
| `hermes_ops-noisy-result` | ✅ | ✅ | ✅ | ✅ — each leg distinct (`2ac89465…` / `48bceaca…` / `24e80a5f…` / `0a1447be…`) |
| `kiem_mini-feature` (response-sanity) | ✅ | ✅ | ✅ | ✅ — hashes leg-distinct (`830a4648…` / `bedf74e6…` / `39aa2b45…` / `292ba23c…`) |
| `kiem_mini-testwrite` (response-sanity) | ✅ | ✅ | ✅ | ✅ — hashes leg-distinct (`140b60bd…` / `bc5f825e…` / `431bf605…` / `c5818fe6…`) |
| `canary-multi-turn` | ✅ | ✅ | ✅ | ✅ — final hash `98417da6…` (cache-reuse marker) **identical on all four legs** |

Tool-call hashes are present only on the two `hermes_ops` tasks (the canary's
mocked tool tasks); the kiem/multi-turn tasks make no declared tool call
(`tool_calls_sha256: null`).

## Determinism

Re-grouped by `(task_id, base_url)` and compared `(final_text_sha256,
tool_calls_sha256)` across trials: **all six tasks are byte-identical between
their two trials on every 8192 leg** (`identical: true, trials_compared: 2`),
matching each artifact's own `summary.determinism`. In the 4096 diagnostic,
five tasks are identical; `kiem_mini-testwrite` has no comparable trials (both
error rows). `prompt_sha256` is also stable across trials for every task in
every file.

## Observables

- **llama.cpp logprobs: unavailable.** llama-server returned logprob content
  positions but no per-position top_logprobs data, so the canary recorded
  `status: "unavailable"` with the reason (`no usable top_logprobs numbers…`);
  margins were never fabricated or coerced.
- **Mei logprobs: unsupported.** All three MLX legs record
  `status: "unsupported"` — `choices[0].logprobs` absent/null. Consistent with
  the established Mei API limitation (Mei exposes no logprobs;
  `references/mei-token-parity-harness.md`).
- **Reasoning hashes: present on all 12 rows of each corrected MLX leg**
  (`reasoning_content` + `reasoning_content_sha256`, courtesy of the 1447a23
  reasoning recording and `--emit-reasoning true`). The llama legs ran on
  predecessor commits (`3118f18eccc9`, `2a5e70108202`) whose canary did not
  record reasoning, so no llama thinking trace is archived; the graded
  observable (`final_text`) is unaffected. llama-server also logged that its
  chat template "supports preserving reasoning" only via the unset
  `--reasoning-preserve` flag — an explicit asymmetry, not a defect.

## Launch settings (verbatim from per-run server logs) and model paths (from JSONL run headers)

- **llama.cpp leg:** endpoint model = pinned official GGUF snapshot
  `/Users/tijs/.cache/huggingface/hub/models--ggml-org--Qwen3.6-35B-A3B-GGUF/snapshots/baec3ebee244827cda0f4557eafa8b28f7545fa6/Qwen3.6-35B-A3B-Q4_K_M.gguf`
  on `http://127.0.0.1:8017/v1`; llama-server: 1 slot, `n_ctx_slot = 65536`,
  `kv_unified = false`.
- **stock Mei:** `mei --model-dir /Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit --served-model-id mlx-community/Qwen3.6-35B-A3B-4bit --host 127.0.0.1 --port 8024 --context-cap 65536 --temperature 0.6 --top-p 0.95 --top-k 20 --emit-reasoning true --cache-reuse true --max-tokens 4096 --prefill-step-size 1024 --kv-cache-dir …/kv-qwen36-matched-stock --compiled-decode false --load-mmap true` (scratch release build `mei-build-qwen36-matched-050`).
- **text-only Mei:** identical flags, `--model-dir …/Qwen3.6-35B-A3B-4bit-textonly`, `--served-model-id Tostibrown/Qwen3.6-35B-A3B-4bit-textonly`, `…/kv-qwen36-matched-textonly`.
- **OptiQ Mei:** `--model-dir /Users/tijs/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit/snapshots/70a3aa32c7feef511182bf16aa332f37e8d82014 --served-model-id mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit --context-cap 65536 --prefill-step-size 512 --load-mmap false --memory-limit-bytes 30000000000 --compiled-decode false` (scratch release build `mei-build-qwen36-optiq-050`, kv-cache-dir `kv-qwen36-optiq-canary`).
- All three Mei legs: pinned v0.5.0 source worktree `/tmp/mei-v050-qwen36-research`
  (the `-050` scratch builds), **safe decode** (`--compiled-decode false`),
  **context cap 65536**, prefill-step 1024 for stock/text-only and **512 +
  `--load-mmap false` for OptiQ**. The three Mei legs ran sequentially on port
  8024, never concurrently.
- Cap verification: canary requests carried explicit `max_tokens=8192`;
  observed max `completion_tokens` per leg (llama 5718, stock 5971, text-only
  6273, OptiQ 4724) all exceed the Mei server-side 4096 default, confirming the
  explicit per-request cap reached the server and nothing was truncated
  server-side.

## Integrity

Archived copies are byte-identical to the `/tmp` originals (`cmp` verified).
sha256 of the archived files:

```
0010cd019165625d7816469f3dd7c28e08307b16057ba62e46300f564cfdf316  qwen36-matched-llama-canary-8192-20260914.jsonl
d87b9a4c80079db4a7e0c110eb78fdee66e622247a0b0e02bf7a5125188a1cd1  qwen36-matched-llama-canary-20260914.jsonl
87e93a432b6f4befa0479a77436089ff895c634cea9d799b08ae58a7d8ee6b74  qwen36-matched-stock-canary-8192-20260914.jsonl
fadcc615ad96f6967d0f238548c0569df32d7cea08952c4698c541c6fa5ebdd4  qwen36-matched-textonly-canary-8192-20260914.jsonl
fc98bed0341e6760660fd4acb7f5d9e6effe96753c4e200af16eb2cbf381db51  qwen36-matched-optiq-canary-8192-20260914.jsonl
```

## Boundary

No `results/log.jsonl` row, `LEADERBOARD.md` change, config edit, or runner
source change belongs to the canary or this archive; HEAD stays `1447a23`.
This commit adds only the six artifact paths below.
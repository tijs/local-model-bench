# Qwen3.6-27B ManniX CD-IQ4_K_M gate report — 2026-09-16

Candidate: `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF`, file
`Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`, served alias
`ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M`.

**Gate evidence only. This candidate is NOT ranked and no benchmark result
exists yet. NO `results/log.jsonl` rows were appended by this gate, no config
was added, and no leaderboard change belongs to it.** Exact-identity, plain,
streaming, and native-tool probes passed; a six-task exploratory canary passed
5 of 6 tasks and hit one response truncation at `max_tokens=4096`; broad
benchmarking is blocked by free disk.

## Scope and no-side-effects boundary

This scheduled tick authorized: staging the GGUF into the HF cache only, and a
bounded gate (identity/plain/streaming/native-tool probes plus one six-task
canary trial) served from `127.0.0.1:8017`. Carried out under that boundary and
nothing else: no server is left running, no new download or deletion happened
beyond the authorized staging, no benchmark was run, `results/log.jsonl`,
`configs/`, `.kiem`, and all sibling repositories were untouched, and nothing
was committed or pushed (repo HEAD remains `1e7a92f59824`, main, with this
report and the three raw gate artifacts pending, untracked).

## Hugging Face provenance and staged cache path

- Repo: `ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF`
- Revision (immutable): `75a75137d610ed037a09b46c29ca1d37fd000f2e`
- File: `Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`
- Size: 16,702,973,408 bytes (verified against the staged blob)
- SHA-256: `6f1735c73f77d5ffb9551a30dee30d3f82a790442697950c4ed4f9bbecea6c22`
  (verified; blob filename == this digest, size matches)
- Staged cache path (only the blob + snapshot symlink, no repo files):
  `/Users/tijs/.cache/huggingface/hub/models--ManniX-ITA--Qwen3.6-27B-A3B-Coder-MTP-GGUF/snapshots/75a75137d610ed037a09b46c29ca1d37fd000f2e/Qwen3.6-27B-A3B-Coder-CD-IQ4_K_M.gguf`

Public model-card metadata (from the HF repo card; informational only, NOT
benchmark-verified here — README claims are not gate facts): 27B-3B-MoE
coder-oriented GGUF with MTP, CD-IQ4_K_M quantization.

## Engine and launch controls

- Binary: `/Users/tijs/projects/local-model-bench/runner/.dspark-head/build/bin/llama-server`
  (present, executable; server log confirms it loaded the staged snapshot file
  and listened on `http://127.0.0.1:8017`, `n_slots = 1`, `n_ctx_slot = 65536`)
- Launch controls (authorized tick):
  `--alias ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M`,
  `--ctx-size 65536`, `--parallel 1`, `--n-gpu-layers 99`, `--flash-attn on`,
  `--temp 0.6`, `--top-p 0.95`, `--top-k 20`, `--min-p 0.0`, `--jinja`,
  `--reasoning on`, `--cache-prompt`, `--timeout 1800`
- Server log: `/tmp/mannix-qwen36-cd-iq4km-gate-20260916-server.log` (durable
  copy: `artifacts/qwen36-mannix-cd-iq4km-gate-20260916-server.log`)

## Gate result (raw stream artifact)

Source: `artifacts/qwen36-mannix-cd-iq4km-stream-gate-20260916.json`
(endpoint `http://127.0.0.1:8017/v1`, served_ids
`[ManniX-ITA/Qwen3.6-27B-A3B-Coder-MTP-GGUF:CD-IQ4_K_M]`).

| Probe | Status | Evidence from artifact |
|---|---|---|
| Identity (`models_identity`) | PASS | served_ids exactly matches the alias |
| Plain non-streaming | PASS | finish_reason `stop`, content `ready` |
| Plain streaming | PASS | 178 chunks, finish_reason `stop`, content `stream-ready` |
| Native tool non-streaming (`add_numbers`) | PASS | name `add_numbers`, arguments `{"a":15,"b":27}`, finish_reason `tool_calls` |
| Native tool streaming (`add_numbers`) | PASS | 117 chunks, same name/arguments, finish_reason `tool_calls` |

Both tool calls carry the same `add_numbers` call with `{"a":15,"b":27}` and
`finish_reason: tool_calls`; no malformed-argument, transport, or harness error
in the artifact.

## Exploratory canary (unranked evidence, one trial)

Source: `artifacts/qwen36-mannix-cd-iq4km-native-gate-20260916.jsonl`
(suite `sanity-basic`, `hermes_ops-chaining`, `hermes_ops-noisy-result`,
`kiem_mini-feature`, `kiem_mini-testwrite`, `canary-multi-turn`;
`max_tokens=4096`, `max_turns=4`, `temp 0`, `runner_git_sha 1e7a92f59824`).

- Summary row: `passed=5, failed=0, errors=1, tasks_total=6`.
- 5 passed with full grading and no errors: `sanity-basic`,
  `hermes_ops-chaining`, `hermes_ops-noisy-result`, `kiem_mini-feature`,
  `canary-multi-turn`.
- `kiem_mini-testwrite`: response truncated — `finish_reason=length`,
  `error_kind=truncated`, error string "response truncated
  (finish_reason=length) before a final answer — max_tokens=4096 was likely
  too low". This is the model hitting the token cap, not a transport/harness
  failure; the aggregate `errors=1` (and exit 1) exists solely for that
  explicit truncation.
- Held as **exploratory, unranked evidence**: a single trial with one
  truncation does not constitute a benchmark result and got no log.jsonl row.

## Resource facts

- Post-stage free disk (verified at teardown): ~25.49 GiB (~27.37 decimal GB)
  — current `df` reads 25 GiB free on the data volume.
- Runner pre-launch gate: `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 30.0`
  (`runner/bench_common.py`, line 78). Post-stage free disk is **below** that
  30 GB gate, so no broad benchmark was launched.
- Staging floor: the tick's authorized 20 GiB staging floor. Post-stage free
  disk is **above** that floor, so staging was valid and the staged blob is
  intact.
- Net: the candidate is admitted to a future benchmark gate, but a broad
  benchmark run is blocked by disk until free space clears the 30 GB launch
  gate.

## Teardown (verified)

- No `llama-server`, `mei`, `omlx`, or `vllm` process running.
- No listener on port 8017 (`lsof -nP -iTCP:8017 -sTCP:LISTEN` empty).
- No canary process remaining; server log closed at teardown.

## Decision

**Admitted to a future benchmark gate** (identity, plain, streaming, and
native-tool behavior all passed; canary evidence is clean apart from one
explicit max-tokens truncation). **Broad benchmarking is blocked by disk** —
free space is below the runner's 30 GB launch gate. No benchmark rows, no
config snapshot, no commit.
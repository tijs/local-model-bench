# Gravity RL (batiai/Gravity-30BA5B-RL-GGUF Q4_K_M) bounded native admission gate + one-trial canary — 2026-09-19

**Timestamp (write):** 2026-09-19 ~20:35 CEST / 18:35Z · **Run window:** 19:38–20:27 CEST (17:38Z–18:27Z)

**Status: GATED / UNRANKED.** This is admission evidence only. A passing native gate + canary is
**not** a benchmark result: no `results/log.jsonl` rows were appended, no leaderboard was
regenerated, no ranking is claimed, and the candidate remains **QUEUED / UNRANKED** until a complete
25-row current-suite battery lands and is reviewed (config `known_gaps`, COMPLETION CONTRACT).

**Verdict:** native admission gate **7/7 PASS** (run 2); fixed one-trial canary **5 passed /
0 failed / 1 error** (error is a model-side `finish_reason=length` truncation at the 8,192-token
cap on `hermes_ops-noisy-result` — thinking-mode verbosity, not a harness/server fault). Server
health verified after every stage; teardown completed and verified.

---

## 1. Scope and boundary (what this unit did and did not do)

- Did: single-writer preflight; verified the staged artifact (size + sha256 + symlink chain);
  launched the pinned llama-server on port 8017 with the config's safe flags + the runner-canonical
  alias; ran the bounded native gate; ran the fixed `runner/canary.py` six-task one-trial canary;
  took evidence; tore the server down; committed **only** this report.
- Did **not**: run `run_bench.py` / the battery, append to `results/log.jsonl` (verified 4,145 rows,
  tail unchanged), regenerate `results/LEADERBOARD.md`, launch Gravity Base or any Bonsai/other
  model, touch CoCore, mutate Kiem, edit the config, redownload/delete the staged blob, or push.
- No foreign process was killed. The Hermes host processes (gateway 7960/7957, dashboard 8013,
  marktplaats MCP 8135/7974, tailnet router 2200) were running at dispatch and remain untouched.

## 2. Pinned provenance (immutable artifact + runtime)

| Item | Value | Verified how |
|---|---|---|
| Config | `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml` (NOT edited) | sha256 `85851d6b44c5f15db336f345ec5b9aa324889d9aa2402bf4c06ef03c8d55d639` → alias `bench-85851d6b44c5` |
| HF repo / revision | `batiai/Gravity-30BA5B-RL-GGUF` @ `ae61d230482a5a6efa869bc6b72fb784bb630cdb` | pinned in config |
| File | `Gravity-30BA5B-RL-Q4_K_M.gguf` | staged snapshot path |
| Size | 19,613,407,328 B (= 18.2659 GiB) | `stat -L` exact match |
| SHA-256 = HF LFS oid | `cc134bbc858cbc9186172cf582234d606c15352e9c016e0f3e1cccfe17ccd4e5` | `shasum -a 256` exact match |
| blob == symlink == oid chain | `snapshots/ae61d230…/Gravity-30BA5B-RL-Q4_K_M.gguf -> ../../blobs/cc134bbc…` | `readlink` + stat; all three agree |
| Binary | `runner/.dspark-head/build/bin/llama-server` — `0.1.2-dev (build 1, commit a302733)`, AppleClang 21.0.0.21000101, Darwin arm64 | `--version` live |
| Served identity | `bench-85851d6b44c5` (only id) | `/v1/models` run 2 check 1 |

Launch flags: host 127.0.0.1, port 8017, ctx 65536, parallel 1, n-gpu-layers 99, flash-attn on,
jinja, cache-prompt, temp 0.6, top-p 0.95, top-k 20, min-p 0.0, timeout 1800, `--alias
bench-85851d6b44c5`. **No `--reasoning` flag** (card-proven `--jinja`-only usage; gate confirmed
reasoning lands in `reasoning_content` without it). Startup (server.log): model loaded in ~2.8 s,
`n_slots = 1, n_ctx_slot = 65536, kv_unified = 'false'`, then a best-effort informational note
"chat template supports preserving reasoning, consider enabling it via --reasoning-preserve"
(not required — reasoning emission verified in gate checks 2–5).

## 3. Preflight / disk arithmetic (exact)

- Git: `main` clean at `d0205c9` when dispatched and at launch (verified before and after). Branch
  ahead of origin/main by 103 commits; no push.
- Listeners before launch: **none** on 8012, 8016, 8017, 8018, 8020, 8024–8027 (lsof).
- Disk (df -k `/Users/tijs`, before launch): `21,143,352` KB free → ×1024 = **21,650,792,448 B** =
  **20.1658 GiB**. Current repo floor `MIN_FREE_DISK_GB_BEFORE_LAUNCH = 10.0` GiB =
  10,737,418,240 B → margin **+10,913,374,208 B (10.163 GiB)** ✓. (The retired 30 GiB runner
  guard was **not** imposed per dispatch; the earlier same-day `gravity-rl-resource-gate-blocked`
  report was evaluated against that retired guard and does not apply to this launch.)
- Staging arithmetic (parent-measured, re-checked live): free before staging
  41,267,372,032 B (38.433 GiB); after the 19,613,407,328 B blob 21,653,381,120 B (20.166 GiB);
  consumed by staging = 41,267,372,032 − 21,653,381,120 = **19,613,990,912 B** (blob
  19,613,407,328 B + 583,584 B of hub metadata: refs/locks/snapshot entries). My pre-launch read
  (21,650,792,448 B) differs from the parent's post-stage read by 2,588,672 B — hub metadata
  writes between the two measurements; the blob itself is byte- and hash-identical.
- Post-teardown disk: 20,087,964 KB = 20,575,675,392 B = **19.159 GiB** free (blob kept staged,
  as instructed; only small evidence files added).

## 4. Native gate — run 1 (probe calibration pass, kept as evidence)

`native-gate-run1.json`. Checks 1–3 PASS. Check 4/5 **FAIL / FAIL**: the tool prompt's thinking
trace exceeded the probe's `max_tokens=128`, so the response hit `finish_reason=length`
mid-reasoning with no call emitted and no malformed textual fallback — a probe-budget artifact,
recording the model's verbose thinking, not a tool-call defect (the retest with an adequate
bounded budget is run 2). Check 6 **FAIL only under an over-strict `first==0` condition**: raw
`cached_tokens` were first=9 (template-prefix residue), recall=6255, growing=6252 — cache reuse
demonstrably works; the strict condition was dropped to the task's actual requirement
(recall > 0). Check 7 **ERROR**: `POST /tokenize` → HTTP 404 on this server build, so the planned
calibration never executed; server stayed alive. Both FAIL and the ERROR are raw rows in run 1.

## 5. Native gate — run 2 (final, all PASS)

`native-gate.json` (raw requests/responses + exact timings per check):

1. **Identity PASS** — GET /v1/models served ids exactly `["bench-85851d6b44c5"]`.
2. **Plain non-streaming completion PASS** — prompt "Reply with exactly the word: admission-ok";
   `content` = `admission-ok` exactly, `finish_reason=stop`, 47 completion tokens, 1.978 s.
   `reasoning_content` emitted separately and captured (template-default thinking works with
   `--jinja`, no `--reasoning` flag needed).
3. **Plain streaming completion PASS** — 43 chunks, assembled `admission-ok`, `finish_reason=stop`,
   byte-identical to non-streaming, 1.218 s.
4. **Native tool call (non-streaming) PASS** — `add_numbers` tool; `finish_reason=tool_calls`;
   `function.name = "add_numbers"`; `arguments` raw `{"a":15,"b":27}` parses to exactly
   `{"a": 15, "b": 27}`; `content` empty — **no malformed textual fallback**; completion 256
   tokens (≈248-token reasoning trace then the call), 7.055 s. `prompt_tokens_details.cached_tokens`
   = 213 (prefix reuse across requests).
5. **Native tool call (streaming) PASS** — 269 chunks assembled to the same single call, identical
   name/arguments, `finish_reason=tool_calls`, no fallback, 7.852 s.
6. **Cache reuse PASS** — 6,256-token prompt: first request `cached_tokens` 9 (residue), exact
   recall `cached_tokens` **6255 (>0)** (26.87 s → 0.697 s), growing prompt (7,216 tokens)
   `cached_tokens` **6252 (>0)** (6.784 s). Task gate satisfied: recall/second turn > 0.
7. **Context boundary PASS (bounded, classified)** — 55,000-token target built from the same
   repeating sentence calibrated with the measured wire ratio from check 6
   (6,256 tokens / 31,980 chars = 0.19562 tok/char; `/tokenize` is 404 on this build). Wire usage:
   `prompt_tokens = 54,856` (~84% of the 65,536 ceiling), completion 8 tokens
   (`finish_reason=length`; all 8 went to `reasoning_content`, so `content` is empty — deliberately
   tiny completion budget, recorded raw). Prompt processing 986.6 s at a **declining** rate
   (server.log task 1771: 191 → 150 → 133 → 121 → 78 → 71 → 60 → 56 → 54 → 52 → 51 → 49.7 tok/s
   from 2K to 47K tokens — memory-bandwidth bound on this 30B-MoE Q4). Server fully healthy after;
   no OOM, no disconnect, no ctx overflow. Notes: a full 65,536-token *prompt* + any completion
   cannot fit the 65,536 ceiling by definition, so a bounded near-ceiling probe is the feasible
   standard; the probe was stopped/classified exactly as the task permits. Bonus: the context
   request reported `cached_tokens=7212` — llama.cpp reused the check-6 repeating-sentence prefix
   from KV against this prompt's own repetition prefix.

`server_health` after gate: **ALIVE**.

Notable measured fact vs the card: the config cites the card's claim of "short reasoning (~150
chars for a simple tool question)". Measured here on this binary+artifact: the trivial
`add_numbers` question consumed ≈256 completion tokens (~most of it reasoning) before the call —
the card's "short" characterization did **not** reproduce. Thinking-mode verbosity is the
dominant observed cost (see canary).

## 6. Canary — fixed six-task one-trial (exploratory, UNRANKED)

`runner/canary.py` v0.1.0, trial 1, max_tokens 8192, max_turns 6, temperature 0, timeout 1800,
endpoint `bench-85851d6b44c5@http://127.0.0.1:8017/v1`, output `canary.jsonl` (identical to the
fixed suite; endpoint identity verified by the canary before any request — no identity rows).

| Task | Outcome | Elapsed | finish | completion tokens | Notes |
|---|---|---|---|---|---|
| sanity-basic | **passed** | 2.8 s | stop | 41 | exactly `42`-class arithmetic; reasoning 139 chars |
| hermes_ops-chaining | **passed** | 201.5 s | stop | 219 (3 turns) | real chained_tool_calls grader; tool_calls_sha `912a44f0be1f`; 63,930 prompt tokens cum |
| hermes_ops-noisy-result | **error** | 804.2 s | length | 8,294 | single exchange exceeded the 8,192 cap mid-task; tool_calls_sha `ac4712f9a9cf` non-empty → tool progress made; `error_kind=truncated` |
| kiem_mini-feature | **passed** | 53.5 s | stop | 1,766 | response-sanity; reasoning 5,377 chars |
| kiem_mini-testwrite | **passed** | 162.6 s | stop | 4,894 | response-sanity; reasoning 14,594 chars; known Qwen3.6 failure prompt #2 cleared on response |
| canary-multi-turn | **passed** | 8.5 s | stop | 212 | contains `cache-reuse-ok` |

Summary row: `5 passed, 0 failed, 1 errors, completed=True`.

**Model-vs-harness classification:** the single error is **model-side**. This artifact's
thinking-mode verbosity (reasoning traces of 139–14,594 chars measured) makes a single
exchange on the 26K-system-prompt noisy-result task exceed the canary's 8,192-token cap; the
harness classified it correctly (`finish_reason=length`, explicit `truncated` row, run continued)
and the server stayed healthy throughout. The repo config already defends against this exact
shape via `hermes_ops_max_tokens: 16384` — the measured 8,294-token overflow fits inside that
budget, but the verbosity property must be watched in any battery: `run_prompt_suite.py` has no
`finish_reason=length` continuation, so an exchange beyond 16,384 tokens would truncate there too.

## 7. Raw evidence (external dir, outside results/log.jsonl)

`/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/gravity-20260919T173802Z/`

| File | SHA-256 |
|---|---|
| native-gate.json (run 2, final) | `f4f3b4c7c087b95872cff95c65ffca451381bb75fd29eed9af8713c662621530` |
| native-gate-run1.json (calibration pass) | `284b217e23e03da4a002d51e00f9bb5ff547bd69a07918c070f978da7d07bf6d` |
| canary.jsonl | `4e3f51a663ca3d5f1abc7e6394a5ba32f26e23ff555f57e6ee6ee4db9194b252` |
| server.log (live) = server.log.snapshot | `965f385fbc9f24af443a4056e0531f5606baaf75c52c6fd78f761a7ec08289f2` |
| native_gate.py (probe, reusable) | `129fa5bcd68070c58152878f356ffbd4d832d641cec84cd759a528ccee13e70e` |

(`server.log.snapshot` was copied at end-of-run; identical content to the live `server.log`.)

## 8. No-result statement and teardown

- `results/log.jsonl`: still **4,145 rows**, tail unchanged (last row is the AX-Qwen3.6
  `hearth_full-testwrite` 2026-09-17 leg). **No rows appended.** `results/LEADERBOARD.md` not
  regenerated. No transcripts created. No config edits (`git status` clean throughout, and the
  config sha256 matched the committed alias).
- Teardown: my launch process `llama-server` (pid 70760) stopped via SIGTERM after the canary;
  exited cleanly. Verified after: **no listener** on 8017 or any bench port (8012/8016/8018/8020/
  8024–8027 all free), **no** llama-server / native-gate / canary process descendants, Hermes host
  processes untouched, checkout clean except the newly added report (uncommitted until the commit
  step below).
- Report commit: `artifacts/gravity-rl-q4km-native-gate-20260919.md` only (this file).

**Bottom line:** the staged artifact is byte- and hash-verified, serves exactly
`bench-85851d6b44c5`, passes the full bounded native admission gate (identity, plain + streaming
completion, native non-streaming + streaming tool calls with clean JSON and `finish_reason=tool_calls`,
cache reuse, ~55K-token near-ceiling context without death), and passes 5/6 fixed canary tasks with
one model-side truncation error. **GATED / UNRANKED** — no ranking signal.
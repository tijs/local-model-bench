# Bonsai 2 PTQ1_0 — canonical-alias recheck addendum (2026-09-18)

**Status: canonical identity discrepancy RESOLVED.** The one-hex-digit alias
discrepancy recorded at HEAD `1087ef2` is closed by a dedicated canonical
recheck: the server was launched with the runner-canonical alias
`bench-4e2230a3f7ca` (== committed config hash prefix), and every identity /
plain / tool / cache probe passed under that exact alias with the same pinned
artifact and Prism runtime. **Evidence status is unchanged from the initial
report**: the candidate remains admitted only as a **gated / UNRANKED bounded
baseline**. No full 25-row battery ran, no leaderboard/ranking entry exists, no
rows were appended to `results/log.jsonl`, and no Gravity/MLX launch happened
in this unit. This unit started/stopped nothing, reran no benchmark or canary,
and wrote only this addendum.

## 1. Historical discrepancy and artifact retention

- Commit `1087ef2`'s gate and canary **manually served** alias
  `bench-4e223a3f7ca` (probe files and the canary JSONL echo that exact id).
  The actual committed config hash is `4e2230a3f7ca` — one hex digit (`0` at
  position 6) was missing from the served string.
- The runner-canonical aliasing rule is
  `alias = "bench-" + sha256(config bytes)[:12]`
  (`runner/run_bench.py:501` computes the hash, `:555` builds the alias) →
  canonical alias **`bench-4e2230a3f7ca`**.
- **Original artifacts are retained, not rewritten**: the initial gate report
  (`artifacts/bonsai2-ptq1-native-gate-20260918.md`), the initial canary
  (`artifacts/bonsai2-ptq1-canary-20260918.jsonl`, sha256
  `f9f61958f3cf5a0eca6b452a2e89deab1469188425df270992ff349548917038`),
  `LEADERBOARD.md`, `results/log.jsonl`, configs, and all JSONL are untouched.
  This addendum is a new, separate historical record.

## 2. Canonical config hash / alias and pinned artifact / runtime

| Item | Value |
|---|---|
| Config file | `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml` (unchanged) |
| Canonical config sha256 (full) | `4e2230a3f7ca9e05072378c2d79fb9ef83ffc19af929a85968a3b16f72b54ac4` — **re-verified read-only this session** (`shasum -a 256` on the committed config) |
| Runner-canonical alias | `bench-4e2230a3f7ca` (= `sha256(config)[:12]`) — alias served by the canonical recheck |
| Model id | `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0` (GGUF PTQ1_0 ternary, 1.75 bpw) |
| HF revision (immutable pin) | `6ed5e12bf84b7a63069882c91dd9e9218647d17b` |
| Artifact bytes | 5,946,648,928 |
| Artifact sha256 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` |
| Runtime binary | `/Users/tijs/.local/share/local-model-bench/prism-llama-5d80cff/build/bin/llama-server` |
| Runtime source commit | `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6` |
| `--version` | 0.2.0-dev, build 1, commit 5d80cff (re-confirmed read-only this session: `version: 0.2.0-dev (build 1, commit 5d80cff)`) |
| System fingerprint (every response) | `b1-5d80cff` |
| Context cap used | 65536 (harness ceiling) |

All canonical probes ran against `http://127.0.0.1:8017/v1` on port 8017 with
the exact config launch settings and alias `bench-4e2230a3f7ca`, then the
server was torn down with `runner/unload_all.sh`.

## 3. Canonical raw evidence — measurements and verdicts

Raw evidence directory (disposable, outside the repo):
`/Users/tijs/.local/share/local-model-bench/results-mei/
Ternary-Bonsai-2-27B-PTQ1_0/prism-20260918T182706Z-canonical/`

| File | Size | sha256 (re-verified this session) |
|---|---|---|
| `canonical-native-recheck.json` | 8157 B | `43d330362254d2285b213babe56a25210b55d3fb65ad28fcb9a2b2fb3503f21d` |
| `server.log.snapshot` | 6184 B | `a443d0aab7da23f543b631ed2723ab0dd087a7be0d0915352ddccd36bf19ab54` |

> Note: the initial recheck script briefly wrote an invalid POST identity
> result; the parent replaced the identity entry with a real `GET /v1/models`
> response **before** hashing the file. Only the final file above is evidence.

Field-level validation of `canonical-native-recheck.json` (all HTTP 200, model/id
`bench-4e2230a3f7ca`, fingerprint `b1-5d80cff`):

| # | Check | Measured result | Verdict |
|---|---|---|---|
| 1 | Identity `GET /v1/models` | HTTP 200; `id` and sole `alias` exactly `bench-4e2230a3f7ca`; meta `n_ctx=65536`, `n_ctx_train=262144`, `n_vocab=248320`, `n_params=26895998464`, `size=5935527936`, ftype `PTQ1_0 - 1.75 bpw ternary (group 128)`, `owned_by=llamacpp` | **PASS** |
| 2 | Plain non-stream completion | HTTP 200, **3.505 s**, content `READY`, `finish_reason=stop`, usage 59 prompt + 29 completion (`cached_tokens=0`) | **PASS** |
| 3 | Plain streaming completion | HTTP 200, **3.686 s**, 30 chunks, content `STREAM_READY`, `finish_reason=stop`, no errors | **PASS** |
| 4 | Correct non-stream tool call (`tool_choice="required"`) | HTTP 200, **8.652 s**, single `lookup({"city":"Amsterdam"})`, empty content, `finish_reason=tool_calls` | **PASS** |
| 5 | Correct streaming tool call (`tool_choice="required"`) | HTTP 200, **8.811 s**, 44 chunks, single `lookup({"city":"Rotterdam"})`, `finish_reason=tool_calls` | **PASS** |
| 6a | Cache call 1 (store marker) | HTTP 200, 4.954 s, `"I acknowledge the marker."`, `cached_tokens=0` (`cache_n=0`) | PASS (baseline) |
| 6b | Cache call 2 (recall marker) | HTTP 200, 6.032 s, content **`CANONICAL_CACHE_7`**, `cached_tokens=69` of 108 prompt tokens (`cache_n=69`, `prompt_n=39`) | **PASS** — reuse confirmed |

Server-log corroboration (`server.log.snapshot`): exactly one `model loaded`,
exactly one listener startup (`listening on http://127.0.0.1:8017`), **zero**
`Wrong type` / `tool_choice` warnings (`grep -c "Wrong type"` = 0), and six
slot tasks whose elapsed/token totals match the JSON (task 0: 3503.42 ms / 88
tokens; task 32: 3681.62 ms / 91; task 66: 8574.15 ms / 387; task 131: 8802.00
ms / 390; task 199: 4886.73 ms / 121; task 250: 6026.14 ms / 108). The load
line pins the model to HF snapshot `6ed5e12b…`. The log is an **archive**, not
a live listener (see §6).

## 4. Context near-boundary — carried forward, not rerun

The near-boundary measurement from the initial gate remains valid as a
runtime/model measurement but was executed under the **typo** alias; it was
**not repeated** in this unit. An alias-only correction changes the served name
string, not decode behavior on the identical binary/artifact/context, so the
measurement is carried forward as identical-runtime evidence.

- File: `/Users/tijs/.local/share/local-model-bench/bonsai2-ptq1-context-gate.json`
  (external), sha256 `4134e847095028b7691dca43a2e5f4c885f67099c48c1af9472034593895643d`
  (re-verified read-only this session).
- Verified fields: `content_token_count=64900`; tokenize HTTP 200 (0.045 s);
  chat completion HTTP 200 in **931.308 s**, `max_tokens=1`,
  `finish_reason=length`, `prompt_tokens=64951`, `total=64952`, `error=None`
  (no crash); `system_fingerprint b1-5d80cff`; completion echoed model
  `bench-4e223a3f7ca` (typo alias — expected for this historical artifact).
- First attempt was tool-window interrupted at 34,858 prompt tokens; the
  supervised retry completed (recorded in the initial report).
- Verdict: **PASS (carried forward)** — prompt capped at the 65,536 harness
  ceiling, no server crash.

## 5. Initial canary — exploratory unranked evidence, not benchmark rows

- Committed artifact `artifacts/bonsai2-ptq1-canary-20260918.jsonl` (HEAD
  `1087ef2`), sha256 `f9f61958f3cf5a0eca6b452a2e89deab1469188425df270992ff349548917038`
  (re-verified this session), 8 rows = 1 run + 6 trials + 1 summary, one trial
  per task, `temperature=0`, `max_tokens=4096`, `max_turns=6`, endpoint model
  `bench-4e223a3f7ca` (**typo** alias).
- **2 / 6 pass**: `sanity-basic` (final `42`) and `canary-multi-turn` (final
  `cache-reuse-ok`).
- **4 model-level errors** (all model behavior, not transport/harness):
  `hermes_ops-chaining` and `hermes_ops-noisy-result` — `exceeded max_turns
  (6)`; `kiem_mini-feature` and `kiem_mini-testwrite` —
  `finish_reason=length` truncation before a final answer (`max_tokens=4096`
  too low for this reasoning-emitting family).
- **Classification**: exploratory, unranked model-behavior evidence **under the
  typo alias**, retained unchanged for the runner-sizing discussion. It is
  **not** current benchmark coverage: it carries no benchmark-row schema,
  confers no rank, and appended no rows to `results/log.jsonl`.

## 6. Teardown / listener-free state and log rows

Verified read-only this session (after the canonical recheck):

- Port 8017: `lsof -nP -iTCP:8017 -sTCP:LISTEN` → **no listener**.
- Processes: `pgrep -fl "llama-server|prism"` → **no candidate/runner/server
  process**. Teardown mechanism: `runner/unload_all.sh`.
- `server.log.snapshot` is an archived server log (1 model loaded, 1 listener
  startup, 0 wrong-type warnings), **not** a live listener.
- `results/log.jsonl`: **0 rows** matching `PTQ1` and **0 rows** matching
  `bench-4e22`; the only `Bonsai` string matches are 35 historical
  `prism-ml/Ternary-Bonsai-27B-mlx-2bit` rows (retired MLX candidate),
  unrelated to this unit. No leaderboard/ranking entry exists.
- Disk: 80.81 GiB free recorded pre-launch (above the 30.0 GiB
  `MIN_FREE_DISK_GB_BEFORE_LAUNCH`); ~81 GiB free observed now.
- `hermes_provider` remains null; no full battery is authorized.

## 7. Final decision

1. **Canonical identity discrepancy: RESOLVED.** The canonical recheck served
   exactly the runner-canonical alias `bench-4e2230a3f7ca` (== committed config
   sha256 prefix `4e2230a3f7ca`), with identity, plain nonstream/stream,
   correct native tool nonstream/stream, and cache-reuse all PASS under that
   alias on the same pinned artifact + Prism runtime (`b1-5d80cff`).
2. **Admission scope unchanged**: the candidate remains admitted **only** as a
   gated / UNRANKED bounded baseline (per HEAD `1087ef2`). No full 25-row
   expansion, no leaderboard/ranking entry, no `results/log.jsonl` rows.
3. **No Gravity/MLX launch, no server start/stop, no benchmark/canary rerun,
   no config/result rewrites** in this unit — only read-only validation, this
   addendum, and its commit.
# Bonsai 2 PTQ1_0 — bounded native admission gate + one-trial canary (2026-09-18)

**Status: ADMITTED as a gated / UNRANKED bounded baseline.** The pinned Prism
fork runtime + staged PTQ1_0 artifact passed every item of the bounded native
gate (identity / plain+streaming / tool / cache / context) and the six-task
one-trial canary completed with `completed: true`. This is **admission
capability evidence only** — it is NOT a quality or ranking result. No full
25-row battery ran, no leaderboard/ranking entry exists, and no rows were
appended to `results/log.jsonl`.

## Scope / boundary

- Bounded native gate + six-task one-trial canary only. **No full 25-row run**
  (sanity 2 + hermes_ops 8 + kiem_mini 5 + hearth_mini 3 + kipclip_mini 4 +
  hearth_full 3), **no leaderboard/ranking**, **no `results/log.jsonl` rows**,
  no transcripts, no config snapshot, no speed-gate row. The canary artifact
  lives only under `artifacts/` and carries no benchmark-row schema.
- The external server log (`server.log.snapshot`) is an **archive snapshot of
  the disposable probe server's log**, not a current listener — the server was
  torn down after the gate (see Teardown) and port 8017 is free.
- This task did not start/stop any server and did not re-run anything; it only
  inspected existing evidence, validated the artifact, and wrote this report.

## Immutable model / artifact / runtime provenance

| Item | Value |
|---|---|
| Model id | `prism-ml/Ternary-Bonsai-2-27B-gguf:PTQ1_0` (GGUF PTQ1_0 ternary, 1.75 bpw, single file) |
| HF repo revision (immutable pin) | `6ed5e12bf84b7a63069882c91dd9e9218647d17b` |
| Artifact file | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` |
| Artifact bytes | 5,946,648,928 (5.538 GiB) |
| Artifact sha256 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` (== HF LFS oid; re-verified on-disk) |
| Server load line (from log snapshot) | `loading model '.../models--prism-ml--Ternary-Bonsai-2-27B-gguf/snapshots/6ed5e12…/Ternary-Bonsai-2-27B-PTQ1_0.gguf'` |
| Runtime | PrismML-Eng/llama.cpp fork, tag `prism-b10687-5d80cff`, source commit `5d80cff0b8cb9f2bf823cfc4e71e3abb97f290d6` (MIT) |
| Local binary | `/Users/tijs/.local/share/local-model-bench/prism-llama-5d80cff/build/bin/llama-server` — `--version` 0.2.0-dev, build 1, commit 5d80cff (local Metal source build; official macOS asset unpublished) |
| Served system_fingerprint | `b1-5d80cff` (present in every completion response) |
| Context cap used | 65536 (harness ceiling; model native 262144 per card) |

## Config hash and alias

- Config file: `configs/Ternary-Bonsai-2-27B-PTQ1_0/prism-gguf.yaml`, committed
  at HEAD `7ff422b` (config-only commit, 2026-09-18); `git status` clean for it.
- **Canonical config hash** (runner algorithm: `sha256(config bytes)[:12]`,
  `runner/run_bench.py`): **`4e2230a3f7ca`** — full sha256
  `4e2230a3f7ca9e05072378c2d79fb9ef83ffc19af929a85968a3b16f72b54ac4`.
  Re-verified this session by reading the committed config.
- **Alias served during the gate and canary**: `bench-4e223a3f7ca` (all probe
  files and the canary JSONL request/echo this exact id).
- ⚠ **Discrepancy to carry into the serialized queue review**: the served
  alias `bench-4e223a3f7ca` differs from the canonical aliasing
  `bench-4e2230a3f7ca` by one hex digit (a `0` at position 6 is absent from the
  served string). The gate proves the server serves exactly the alias it was
  launched with; it does not prove that alias equals the runner-canonical
  `bench-<config_hash>`. The canary and probes are keyed to the served alias.
  A real `run_bench.py` battery will append and assert the canonical
  `bench-4e2230a3f7ca` alias automatically; the review should confirm the
  launch/alias source so future rows' `config_hash` groups correctly.

## Preflight (disk / single-writer) and teardown

- **Disk**: prelaunch free space recorded 80.81 GiB — above the runner's
  30.0 GiB `MIN_FREE_DISK_GB_BEFORE_LAUNCH` gate.
- **Single-writer**: port 8017 is shared with every other llama.cpp config;
  preflight confirmed exactly one backend on 8017 before the probe server
  launch (no concurrent run; `unload_all.sh` discipline).
- **Teardown**: `runner/unload_all.sh` run after the gate; re-verified this
  session (2026-09-18): `lsof -iTCP:8017 -sTCP:LISTEN` → no listener; `pgrep`
  → no runner/canary/`llama-server` processes. The external log snapshot is an
  archive, not a live listener.

## Native gate checks (measured results)

All probes against `http://127.0.0.1:8017/v1`, model `bench-4e223a3f7ca`.
Raw evidence: `native-gate-short.json`, `native-tool-gate-correct-choice.json`,
`context-gate.json` (see External raw evidence).

| # | Check | Measured result | Verdict |
|---|---|---|---|
| 1 | `/v1/models` exact identity | HTTP 200 (0.005 s); served id + alias exactly `bench-4e223a3f7ca`; meta `n_ctx=65536`, `n_ctx_train=262144`, `n_vocab=248320`, `n_params=26895998464`, ftype `PTQ1_0 - 1.75 bpw ternary (group 128)` | PASS |
| 2 | Plain non-stream completion | HTTP 200, **3.855 s**, content `READY`, `finish_reason=stop` | PASS |
| 3 | Plain streaming completion | HTTP 200, **2.948 s**, 30 chunks, content `STREAM_READY`, `finish_reason=stop`, 0 raw-line errors | PASS |
| 4 | Exploratory non-stream tool call (malformed `tool_choice` object) | HTTP 200, 8.673 s, `lookup("Amsterdam")`, `finish_reason=tool_calls` — server logged a `tool_choice` type warning | PASS (with warning) |
| 5 | Exploratory streaming tool call (malformed `tool_choice` object) | HTTP 200, 5.364 s, 44 chunks, `lookup("Rotterdam")` — second `tool_choice` warning | PASS (with warning) |
| 6 | Corrected non-stream tool call, `tool_choice="required"` | HTTP 200, **5.145 s**, `lookup("Amsterdam")` once, no prose, `finish_reason=tool_calls` | PASS |
| 7 | Corrected streaming tool call, `tool_choice="required"` | HTTP 200, **5.328 s**, 44 chunks, `lookup("Rotterdam")` once, no raw-line errors | PASS |
| 8 | Growing-conversation cache reuse | 1st call 5.69 s (`cached_tokens=0`), 2nd call 5.593 s returned `CACHE_BASE_7` with `prompt_tokens_details.cached_tokens=67` (`cache_n=67`) | PASS |
| 9 | Context near-boundary | `tokenize` 64,900 tokens HTTP 200 (0.045 s); chat completion `prompt_tokens=64,951`, `total=64,952`, HTTP 200 in **931.308 s**, `max_tokens=1`, `finish_reason=length` — expected cap at the 65,536 harness ceiling, no server crash | PASS |

**The two malformed `tool_choice` warnings** (from the exploratory step-4/5
probes, which sent an object where the fork server expects a string):
`server.log.snapshot` lines 27 and 36 —
`W Wrong type supplied for parameter 'tool_choice', using default value:
[json.exception.type_error.302] type must be string, but is object`.
Both exploration probes still produced correct tool calls despite the
fallback-to-default; the corrected required-choice reruns (steps 6–7,
`native-tool-gate-correct-choice.json`) sent `tool_choice: "required"` and
passed with no further warnings.

## Context near-boundary timing and interrupted first attempt

- **Completed measurement**: 931.308 s wall for the 64,951-token prompt with
  `max_tokens=1` (`context-gate.json`). Decode rate on this binary/artifact is
  ~14.2 tok/s per probe `timings` (14.18–14.27 tok/s across the short gate).
  The server log records the 65K-token prompt-eval progression (task 323,
  progress lines up to the completed eval).
- **Interrupted first attempt — classification**: the first foreground attempt
  of the near-boundary context probe was killed by the tool window after the
  server had already processed **34,858 prompt tokens**; the probe was then
  rerun as a supervised background task and completed at 931.308 s. That
  interruption is classified as a **harness/tool-window scheduling
  interruption, not a server or model failure** — the supervised retry is the
  measured result, and no crash or instability was observed during it.

## Canary — exact six-task shape and outcomes

`artifacts/bonsai2-ptq1-canary-20260918.jsonl` (8 rows: 1 run + 6 trials +
1 summary). Runner sha `7ff422b1c6f6` (= HEAD), endpoint
`http://127.0.0.1:8017/v1` model `bench-4e223a3f7ca`, one trial per task,
`temperature=0`, `max_tokens=4096`, `max_turns=6`. Ran 2026-09-18
18:03:49Z → 18:20:11Z (~16.4 min wall).

| Task | Outcome | Measured | Detail |
|---|---|---|---|
| `sanity-basic` | **PASS** | 3.33 s | final `42`, `finish_reason=stop` |
| `canary-multi-turn` | **PASS** | 17.83 s | scripted mid-conversation continuation, final `cache-reuse-ok` |
| `hermes_ops-chaining` | error | 300.03 s | `exceeded max_turns (6) without a final non-tool-call response` — 6 tool turns (web_search ×3, web_extract ×2, write_file), `finish_reason=tool_calls` |
| `hermes_ops-noisy-result` | error | 66.09 s | same `max_turns(6)` error — 7 tool calls (search_files/read_file/terminal) |
| `kiem_mini-feature` | error | 297.21 s | `response truncated (finish_reason=length) … max_tokens=4096 was likely too low` — reasoning stream hit the cap before a final answer |
| `kiem_mini-testwrite` | error | 297.94 s | same `truncated` error — long reasoning before any final text |

Summary row: `{"completed": true, "passed": 2, "failed": 0, "errors": 4,
"tasks_total": 6, "error": null}`.

**Honest classification of the four model-level errors**: the `max_turns`
errors mean the model kept emitting tool calls (with valid arguments and
names) without producing a final non-tool response within six turns — slow,
looping, deliberative behavior, not a transport or harness failure. The two
`truncated` errors mean the model's reasoning stream exceeded the canary's
4096-completion-token budget before a final answer — slow/verbose output, not
a harness failure; the artifact itself flags that 4096 "was likely too low"
for this reasoning-emitting family (the benchmark config defensively uses
`hermes_ops_max_tokens: 16384` for the same reason). The canary exited 1
because of these model-level outcomes, and — by design — it appends no
benchmark rows and confers no rank.

## External raw evidence

Root: `/Users/tijs/.local/share/local-model-bench/results-mei/
Ternary-Bonsai-2-27B-PTQ1_0/prism-20260918T182140Z/` (disposable, outside the
repo):

| File | sha256 |
|---|---|
| `server.log.snapshot` | `8ea35e1cf298e6b5939786a8d2c9afe0b1a70e6f149c47210eda853ca77716b5` |
| `native-gate-short.json` | `25655189b688195768417cbe6566bb8e37bd21b24eb44fd195647be85b1f852b` |
| `native-tool-gate-correct-choice.json` | `f2c7d651ba33bf72bed04e16412810b5cf269a6bd61b0578471a7a1f8d4faeeb` (computed at report time) |
| `context-gate.json` | `4134e847095028b7691dca43a2e5f4c885f67099c48c1af9472034593895643d` |
| `canary.jsonl` | `f9f61958f3cf5a0eca6b452a2e89deab1469188425df270992ff349548917038` |

`canary.jsonl` byte-identical to the committed artifact
`artifacts/bonsai2-ptq1-canary-20260918.jsonl` (same sha256), inspected this
session and preserved unchanged.

## Decision and next action

- **Decision**: **ADMITTED as a gated / UNRANKED bounded baseline.** Every
  native gate item passes on the pinned Prism fork binary + staged PTQ1_0
  artifact (`system_fingerprint b1-5d80cff`), proving admission capability.
  The canary's model-level outcomes (2 pass / 4 model-behavior errors) are
  recorded as reference evidence for the runner sizing (max_tokens/max_turns)
  discussion — **not** as a quality or ranking result, and nothing here claims
  full benchmark completion (that requires the complete 25-row battery with
  zero harness errors and reviewed partial rows).
- **Next action**: **serialized queue review** — the authorized durable queue
  (Kiem plan `7f5c67e7-b564-4df3-8209-14f7443b56e2`) with Bonsai 2 PTQ1_0 as
  the current bounded next baseline; the parent updates the recurring worker
  prompt after review. This task explicitly did **not** launch Gravity or MLX
  or any other candidate; no server was started or stopped here.
- Carry-forward items for that review: (1) the alias/hash one-digit discrepancy
  (`bench-4e223a3f7ca` served vs canonical `bench-4e2230a3f7ca`) so future
  rows group under the runner-computed hash; (2) canary max_tokens=4096
  truncation evidence for the two kiem_mini tasks vs the config's defensive
  16384 cap; (3) `hermes_provider` remains null until a bench-profile entry
  (api 127.0.0.1:8017/v1, context_length 65536) exists — coding suites are
  skipped while it is unset.
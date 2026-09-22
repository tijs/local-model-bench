# Gravity RL Q4_K_M complete benchmark leg — 2026-09-21/22

**Status: COMPLETE CURRENT-METHODOLOGY COVERAGE / REVIEWED / RANKED WITH MODEL-LEVEL FAILURES.**
This is the clean successor to the four earlier interrupted fragments. It has a
new runner SHA and is not merged with those partial groups.

## Run identity and provenance

- Model: `batiai/Gravity-30BA5B-RL-GGUF:Q4_K_M`
- Engine: `llama.cpp`
- Config: `configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Config SHA-256: `34c266c25d9a0f515e932ba58cb10afa39a87189afa8a3c44c440d9c9d03f77a`
  (`config_hash: 34c266c25d9a`)
- Config snapshot: `results/configs/34c266c25d9a.yaml`, byte-identical to the
  live config and the committed config at run start
- Runner SHA recorded by all 25 rows: `4d19196761e0`
  (`4d19196761e0c9e11392c40b24f14a76ab96bb14` at launch)
- Command: `uv run --locked python runner/run_bench.py --config configs/Gravity-30BA5B-RL-GGUF/gguf-q4km.yaml`
- Run window: `2026-09-21T22:19:22Z` through `2026-09-22T11:31:50Z`
  (47,548 seconds between first and last row)
- Server: `runner/.dspark-head/build/bin/llama-server`, version
  `0.1.2-dev (build 1, commit a302733)`, AppleClang arm64
- Served alias: `bench-34c266c25d9a`; provider: `qwen-gguf`; port: 8017
- Artifact: `Gravity-30BA5B-RL-Q4_K_M.gguf`, revision
  `ae61d230482a5a6efa869bc6b72fb784bb630cdb`, 19,613,407,328 bytes,
  SHA-256 `cc134bbc858cbc9186172cf582234d606c15352e9c016e0f3e1cccfe17ccd4e5`
  (independently rehashed after the run)

## Coverage and outcomes

Exactly 25 new rows were appended under `(34c266c25d9a, 4d19196761e0)`:

- `sanity`: 2/2 pass
- `hermes_ops`: 6/8 pass; `hermes_ops-noisy-result` and
  `hermes_ops-multi-step-chain` failed with model-side stream-stall errors after
  partial tool-call progress
- `kiem_mini`: 0/5 pass; all five tasks reached the 3,000-second coding-task
  timeout
- `hearth_mini`: 0/3 pass; all three reached the 3,000-second timeout
- `kipclip_mini`: 0/4 pass; all four reached the 3,000-second timeout
- `hearth_full`: 0/3 pass; all three reached the 3,000-second timeout

Total row result: 8/25 pass. The leaderboard's scored view excludes the two
sanity rows: 6/23 pass (26%). All 25 rows have `harness_error: false`.

The hermes_ops throughput values were
`1.22, 10.92, 10.15, 11.42, 0.25, 0.12, 11.17, 12.02` tok/s, averaging
7.15875 tok/s. This clears the 4.0 tok/s speed gate, so coding was correctly
attempted and no speed-gate row was written.

The two hermes_ops failures are not malformed-tool or transport classifications:
the raw prompt-result JSON contains partial valid tool-call sequences and then
`run_error` set to `stream stalled (turn_total)`. The 15 coding rows have
`harness_error: false`, `hermes_exit_code: -1`, and `TIMEOUT after 3000s`.
Their transcript files contain the exact timeout marker. The archived server log
shows sustained decode on the final cancelled task, reaching 26,708 generated
tokens at about 9.56 tok/s before `stop: cancel task`; this supports the
harness/model slow-budget classification rather than a dead server or harness
crash. No harness errors were observed.

## Durable evidence and teardown

- `results/log.jsonl`: 4,185 rows after the append; SHA-256
  `1d21b2c5090f56d18fa1e9a20e8a58680fdbebcec301f798584c38d385853419`
- `results/LEADERBOARD.md`: regenerated from 4,185 rows; SHA-256
  `3fd890f9966f82ccb8d5424ffc0bde44bcb5afb75061853257b25d6ed0012282`
- `results/score_chart.png`: regenerated with 21 groups; SHA-256
  `a420b07054adcc108c325c7cecb00b5ead23b0d759d4141e439e616bcac9a68e`
- Runner trace:
  `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T221800Z-config-34c266c25d9a.log`
  SHA-256 `3b6a8ada0976a8ede57e3c69bf55a070ac5fc2b7efa85b52e976d0094f001bc8`
- Server log:
  `/Users/tijs/.local/share/local-model-bench/results-mei/Gravity-30BA5B-RL-GGUF/runner-20260921T221800Z-config-34c266c25d9a/server.log`
  SHA-256 `fbf6ba5ba564250c329771df64b343f1a67a697e4438a77bb3f8262b3dc40f0f`
- Fifteen coding timeout transcripts are present under
  `results/transcripts/{kiem_mini,hearth_mini,kipclip_mini,hearth_full}/` with
  the current run's UTC prefixes and served-model slug.
- Runner exit was 0. Its teardown ran; port 8017 and all benchmark-owned server,
  runner, prompt-worker, and probe processes were absent at review. CoCore and
  unrelated Hermes infrastructure were untouched.

The four interrupted predecessor fragments remain append-only and separately
grouped under runner SHAs `bcb8e73140f7`, `2ee0259d6728`, `53920dc41d65`, and
`4ee53065eaf4`. They are not counted in this complete leg.

## Decision boundary

The Gravity RL arm now has a complete, reproducible 25-row leg, but its coding
quality is unusable on this hardware under the current 3,000-second task budget:
all 15 coding tasks timed out while the model continued decoding. Keep this
measured result separate from the gated Gravity Base slot. Do not retry this
same leg without a concrete model/runtime/timeout hypothesis; the next queue
unit is the separately gated Gravity Base candidate, subject to its own artifact,
resource, native gate, and single-writer checks.

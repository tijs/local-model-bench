# Four-model comparison — 2026-11-01

Released method: **benchmark-v8.3.1** (`65c2a18050d2a122be8dc762f971f6894af6b9aa`).
One held-out trajectory per task:12 synthetic household workflows and3 real,
isolated Python CLI tasks, each checked on visible and unseen fixture variants.
Peixinho is still a design; these are stand-ins, not app acceptance or vision tests.

| Model / serving profile | Qualified household | Qualified Python | Full-run time | Outcome |
|---|---:|---:|---:|---|
| MiniCPM-V4.7 Q4_K_M / llama.cpp, q8KV, first8 expert layers CPU |12/12|2/3|5m30s|Complete; highest household result in this trial|
| Qwen3.6 35B-A3B 4-bit / Mei |10/12|3/3|7m06s|Complete; all Python tasks passed|
| Ornith1.5 35B-A3B 4-bit / Mei |9/12|2/3|10m09s|Complete;2 token-budget outcomes|
| Flint40B-A2.5B JANGH2 / Mei |Not admitted|Not run|36s admission|Failed dependent tool contract; unranked|

Times include owned startup/native checks and both tracks, excluding the30-second
host baseline. Flint's admission time is not a full-suite time. The separate,
unranked Flint diagnostic executed all15 tasks in24m20s:9/12 household,0/3 Python
under strict grading. It neither retries nor reverses native admission and writes
no canonical task rows. Its source/task fingerprints match the released task
method. Keep those diagnostic counts outside qualified rankings.

[Generated leaderboard](AGENT_LEADERBOARD.md), [exact campaign selection](agent-v8p3p1-20261101.json).
Ordering uses household passes, then Python passes; there is no combined score or
universal pass threshold. One trajectory per task does not establish statistical
superiority. Different quants, native samplers and serving profiles are explicitly
recorded; this is not a pure base-model or quantization ablation.

## What failed and what was fixed

Qwen's two remaining failures are visible model tool choices: reused/invented
operation IDs during multipart routing, and reading the capture source ID instead
of record `untrusted`, leaving its answer ungrounded. All12 grades were reproduced;
API tool names/arguments matched the domain journals. The earlier benchmark defect
that penalized an absent advertised starter file is fixed in v8.1, and affected
comparisons were rerun. No remaining harness/runtime transformation explains the
recorded Qwen calls. This is evidence about this model/quant/runtime profile,
not a proof excluding every possible numerical backend difference.

MiniCPM's reminder script accepts naive dates and compares them with aware dates;
it also appendsZ without converting non-UTC dates. All3 submitted scripts were
independently replayed on all4 fixture variants, reproducing every output grade.
The two all-GPU profiles were pressure-interrupted and remain preserved, excluded
from ranking. The completed profile retains the requested Q4_K_M artifact and65K
context while using q8KV and CPU placement for8 expert layers. It had one isolated
startup warning and862.43MiB swap growth, then flat swap. No actual stop criterion
was crossed. Qwen and selected Ornith runs had allnormal pressure and no swap growth.

Ornith used its4096-token per-turn limit without finishing multipart capture and
shopping automation. It also repeated deleted content and used the wrong weekday
numbers. API/journal and grader audits matched. Token-budget exhaustion is a
budget outcome, not proof of inability at every budget. An earlier warning-stopped
attempt is explicitly excluded; all raw rows remain.

Flint's strict native attempt omitted the returned code in its verification call.
Prior raw-envelope/cache-off controls support an emitted-argument omission, without
claiming those new samples are the exact original token sequence. The supplemental
full run failed multipart at the token limit; repeated the deleted pickup code
while warning not to reuse it; attempted denied `foreign-private`/`inbox` reads;
and added an unsupported `path` field to `write_script` despite correct shopping
outputs. There were no critical household boundary failures or unauthorized
mutations. Expense/reminder returned reasoning-only, empty-final responses. Their
original termination causes were not recorded. Two saved-prefix stochastic controls
both emitted tool calls and stopped at configured observation token150005; they
show working emission on those prefixes but do not reproduce or settle the exact
original empty-final cause. That attribution remains explicitly unresolved; no
new sample was used to rewrite an old grade or qualify Flint.

Capacity admission now uses explicit model/context/cache/workspace estimates,
normal-pressure/flat-swap launch observations and actual runtime stops. Kernel
free-memory percentage is telemetry only. v8.3.1 also fixes the report's former
allnormal requirement to replay the released stop policy, which permits an
isolated warning and stops on two consecutive warnings. Warning count and swap
growth remain visible. No task grades or inference settings changed in that patch.

## Evidence and limits

- [Qwen review](../artifacts/automation-benchmark-20261029/qwen-heldout-v8p1-review-20261101.md) and [audit](../artifacts/automation-benchmark-20261029/qwen-heldout-v8p1-20261101/audit.json).
- [Ornith quiet-run review](../artifacts/automation-benchmark-20261029/ornith-heldout-v8p1-quiet-review-20261101.md) and [audit](../artifacts/automation-benchmark-20261029/ornith-heldout-v8p1-quiet-20261101/cleanup-and-audit.json).
- [MiniCPM review](../artifacts/automation-benchmark-20261029/minicpm-cpu8-review-20261101.md) and [audit/replays](../artifacts/automation-benchmark-20261029/minicpm-heldout-v8p3-cpu8-20261101/cleanup-and-audit.json).
- [Flint strict admission](../artifacts/automation-benchmark-20261029/flint-heldout-v8p1-review-20261101.md), [full diagnostic review](../artifacts/automation-benchmark-20261029/flint-full-review-20261101.md), [full diagnostic audit](../artifacts/automation-benchmark-20261029/flint-full-diagnostic-v8p3p1-20261101/cleanup-and-audit.json), and [stop-cause controls](../artifacts/automation-benchmark-20261029/flint-stop-controls-20261101/cleanup-and-audit.json).

All selected configs, task helpers, runtime binaries/dependencies and supervisor
identities are checked by the comparison verifier. Qwen/Ornith/Flint measurements
retain their original source IDs; byte-equivalent releases do not manufacture new
runs. Results are append-only. Post-run model hashes match; logs are preserved,
owned servers stopped and only owned KV caches cleared. Historical partial,
resource-stopped and preflight-declined attempts are retained and do not rank.
A65,536 context setting or short-task score does not prove usable full-window
behavior. Ornith's separate near64K allocation probe was pressure-interrupted;
that limit remains separate from the complete short-task comparison.

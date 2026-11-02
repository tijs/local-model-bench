# Fresh four-model comparison preparation

All four contenders will run fresh on frozen benchmark-v9.9, with seeds 17 and 29
for each. No prior Groot/Logics run is substituted. Retain all eight outcomes.
See the [plan and definitions](../../docs/FOUR_MODEL_COMPARISON.md).

- All 712 model-free tests pass. Focused reporting tests reject incomplete or
  critical coverage, duplicate/mismatched seeds and changed runtime identities.
  Memory tests check recorded page-size math, median baseline and unavailable
  negative deltas rather than pretending a model has zero memory cost.
- New reporting code/tests pass Ruff and ty. A clearly labeled synthetic layout
  test was visually inspected outside the result directories. It is not model
  evidence and is not embedded in the real summary.
- All eight configs validate. Mei launcher dry runs verify the same rc.2 binary,
  Metal/source pins and no builds. Logics runtime hashes remain pinned.
- Qwen 15-file, Ornith 11-file and Groot 16-file local snapshots are recorded;
  the full Logics GGUF hash also matches its pinned value. Every previously
  verified weight/config/tokenizer/template file matches the old hash evidence;
  local derivative provenance stays explicit.
- Measurement code, tasks, graders, budgets, containment and resource policy
  remain byte-identical to benchmark-v9.8. The added reporting module is not
  imported by measurement runners. Source/configs are committed before loading.

Actual model runs, post-run audits, resource checks and real charts remain open.
The model-free suite includes deliberately mocked legacy warnings/stale-chart
messages; it does not run real Hermes or an uncontained scored Python task.

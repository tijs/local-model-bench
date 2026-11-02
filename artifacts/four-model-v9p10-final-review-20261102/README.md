# Four-model comparison completion audit

All four contenders completed both declared fresh runs on frozen benchmark-v9.10
`40ece5bcd74ca218a8719ee52785221ce69f8341`. No earlier run was substituted.
All four remain retained; measured profiles differ in sampler/quant/model size/engine.
The data/report patch release is v9.10.1; measured source identities stay v9.10.

[Main summary and graphs](../../results/AGENT_SUMMARY.md) ·
[Interpretation](../../docs/FOUR_MODEL_COMPARISON.md) ·
[Machine-readable completion audit](completion-audit.json)

- All 96 household grades reproduce under the frozen measured grader; every API
  call name/parsed argument matches the domain journal.
- All 23 submitted Python scripts reproduce the saved outcomes on four contained
  variants each (92 executions). Ornith seed29 CSV has no submitted script after
  finish_reason=length at 4096 tokens; replay is explicitly not applicable.
- Both cohorts pass the released source/config/runtime/coverage/resource reader.
  Every supervisor exited 0 without a stop. All 931 pressure samples were normal;
  swap never grew within any run. Model/runtime hashes matched after every exit.
- All six owned Mei KV directories were inventoried/index-summarized before removal
  after server exit. Logs, requests, staged model files and task traces remain.
  llama.cpp uses no owned disk KV tier. Ports 8017/8024 are free; no runner/server
  remains. The log-preservation helper's old llama.cpp filename was corrected;
  the prior misfiled log is kept with a SHA-256 receipt, not silently discarded.
- All 715 model-free harness tests pass in runner-tests.log. Ruff/ty pass and
  all 9 focused reporting tests pass, including pressure/swap/disk violations
  despite a zero process exit, incomplete coverage, changed runtime and seeds.
  Mocked legacy/plot-failure output in the test log is not a real Hermes run or
  a failed generation of the current charts.
- All three real PNG figures were visually inspected. The memory labels were separated
  with leader lines without moving observations. All three SVGs parse and use the same
  Matplotlib figures; PNG/SVG plus metric JSON/CSV and report-program SHA are kept.
- Raw rows are append-only; original v9.9 evidence and older summaries are intact.
  Unrelated pre-existing archive deletions and artifacts/.DS_Store are untouched.

Logics-SWE scored 11/12+3/3 twice. Groot scored 11/12 then 10/12 household,3/3 Python
both times, with the lowest observed wired increase and weight storage. Qwen
and Ornith each scored 9/12 then 11/12 household; Python was 2/3 twice for Qwen and
3/3 then 1/3 for Ornith. All failures retain their exact contract/budget meaning.
These two trajectories do not prove general superiority, near-64K capacity or
real Peixinho acceptance. The application adapter remains separate future work.

Rebuild the derived report without loading any model:

```sh
uv run --locked python runner/build_four_model_summary.py \
  --spec results/four-model-v9p10-comparison.json
```

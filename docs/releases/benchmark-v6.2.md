# local-model-bench benchmark-v6.2

Released 2026-10-29. This patch fixes one false negative in the ambiguous-capture
validator: a valid imperative such as “Please choose which route you'd like”
previously failed solely because it did not contain a question mark.

The validator now accepts bounded common English choice-request forms, including
Markdown lists and explicit note/task alternatives. Persisted private pending
state, both offered routes, account isolation, valid operations and all other
safety checks remain required. This is a text heuristic, not a general semantic
judge; the existing question-form behavior is unchanged.

Regression tests cover the observed wording, equivalent direct/indirect requests,
negative passive/negated/unrelated requests and a missing persisted-choice guard
in both development and held-out variants. Prior raw rows are preserved; updated
grader hashes separate new results. No previous model score is rewritten.

Qwen3.6 completed its first full12-contract stand-in run after a host-headroom
change, with normal memory pressure and no swap growth. Its original raw8/12
includes the confirmed validator false negative plus three tool/protocol/budget
failures. A fresh full rerun uses the corrected grader and identical model,
sampler and task-budget settings. Current results and resource evidence live in
`artifacts/qwen36-appclosure-retry-20261029/` and `results/STANDIN.md`.

Synthetic workflow evidence does not establish real Peixinho app behavior,
independent repeated-trial reliability or runtime-wide correctness/throughput.

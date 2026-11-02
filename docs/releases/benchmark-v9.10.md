# local-model-bench benchmark-v9.10

Fixes a routing-choice grader false negative found while auditing Qwen's fresh
v9.9 seed29 run. “Please let me know which one you prefer” correctly requests
a choice between previously listed private routes. The old checker required a
route noun in the same clause and lost that reference. The corrected check
requires prior route context plus an explicit indirect choice request; negative
and unrelated statements still fail. Durable routing state remains a separate
requirement. Prompts, tools, budgets, runtimes and resource policy are unchanged.

All five v9.9 attempts remain published with their original grades and source
identities. The eight-run four-model comparison restarts fresh on v9.10 using
base Qwen3.6, Ornith1.5 and Groot on the same distributed Mei rc.2 binary, plus
Logics-SWE on pinned llama.cpp. Seeds17/29 and previous per-model sampler/cache
settings remain predeclared. No old run is reused or silently rescored.

Validation: 714 model-free harness tests pass. Routing tests cover explicit
pronoun references, direct requests, negative/unrelated statements and missing
persisted choices. A model-free replay of all60 saved household trajectories
from the five v9.9 attempts changes exactly the identified Qwen routing check;
it is a diagnostic, not new benchmark evidence. All8 configs and runtime hashes
validate;6 Mei dry runs perform no builds or model loads. Ruff and ty pass.

The summary/reporting work from v9.9 is retained. Real PNG/SVG quality-versus-
time and memory plots will be generated only after all8 corrected runs finish.
Engine labels, full-run wall time, separate household/Python quality and partial
system-wide wired-memory accounting stay explicit.

[Comparison design](../FOUR_MODEL_COMPARISON.md) ·
[Preserved v9.9 attempts](../../results/FOUR_MODEL_V9.9_INTERRUPTED.md) ·
[Validation and diagnostic](../../artifacts/four-model-retest-v9p10-20261102/)

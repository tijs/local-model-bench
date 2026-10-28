# local-model-bench benchmark-v6

Released 2026-10-28. This methodology release adds `peixinho-standin-v1`.
Benchmark-v5 and its `model-only-v1` identity remain available and unchanged.
Python dependency metadata has its own version and is not the methodology tag.

## New synthetic workflow track

Twelve contracts exercise household capture, ambiguity, multipart requests,
grounded retrieval, privacy isolation, previewed sharing, private copies,
saved progress, completion intent, recurring occurrences, retries after outage,
and untrusted retrieved content. The model uses bounded domain tools in fresh
synthetic household state. Independent validators inspect resulting state,
receipts, journals, provenance and phase snapshots after execution.

The runner requires committed configuration bytes, native tool/continuation
admission, served-model identity and explicit sampler/cache/partition profiles.
The owned lifecycle retains the normal disk gate and server teardown. Four-task
smoke and explicit diagnostic subsets record their exact planned coverage.
Denied and invalid operations, prevented unsafe attempts and accepted unauthorized
mutations are distinct. Returned reasoning is archived and replayed in model
history; it is not an answer-quality score. Full transcripts and immutable
runner/catalog/grader/config identities accompany append-only rows.

See [the workflow guide](../PEIXINHO_STANDIN.md) for commands, budgets and contracts.
New results live in `results/standin/log.jsonl` and `results/STANDIN.md`, separate
from model-only and historical Hermes results. Nothing reinstalls or runs Hermes.

## Validation and limits

The release candidate passes the locked harness regression suite (548 tests).
Model-free reference and corruption tests cover all 24 development/held-out
fixtures. These validate benchmark contracts, not model capability.

Flint development pilots exposed real transport/checker defects that were fixed
before this release. Earlier rows preserve their original grader identities;
corrected focused follow-ups cover subsets, not a replacement full score.
Residual Flint failures and base-model/quant/runtime attribution remain open.
The Qwen3.6 baseline is pending at release time. Historical rankings do not
transfer to this suite and there is no new cross-model winner.

Peixinho remains a design. This release is a simulator/model evaluation, not an
application driver or evidence of phone, sync, encryption, notifications,
production authorization, real household safety or product readiness. Initial
12-turn/1536-token-per-turn/300-second task budgets and deterministic factual
checks need further calibration. Development reuse is not unseen evaluation;
shared-server repeats are not independent samples. No composite product score
is produced. Actual app integration requires separate future runs and evidence.

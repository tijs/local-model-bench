# Four-model campaign completion review

The Groot, ThinkingCap, Logics-SWE and Clover evaluation is complete. This is
completion of the requested candidate campaign, not a claim that every model
passed every task or that all Mei/Peixinho project work is finished.

Decision: retain Logics-SWE and Groot as primary serving profiles, ThinkingCap
and MiniCPM as alternatives, and Clover as an experimental native diffusion
profile. Qwen/Ornith stay reference-only; Flint/JANGH2 remains user-retired.
No staged weights or historical task evidence are deleted by that selection.

[Retained roster and limits](../../../docs/ROSTER.md) ·
[Machine-readable selection](../../../configs/active_roster.json) ·
[Campaign chronology](../../../docs/CANDIDATE_CAMPAIGN.md)

## Requirement-by-requirement review

| Requirement | Authoritative evidence | Disposition |
|---|---|---|
| Get Groot working with an evidenced MLX path | Hash-preserving text export, public immutable snapshot, native release probes and both full v9.8 trials | Complete. Language payloads preserved; no requantization or BF16 parity claim. |
| Evaluate ThinkingCap, checking an existing MLX path first | Pinned research inventory/config and bounded-checkpoint full result | Complete as GGUF/llama.cpp. Targeted research found no exact ready compatible MLX pack in its returned inventory; this is not an exhaustive absence claim. |
| Evaluate Logics-SWE, checking an existing MLX path first | Pinned research/config, first full result, two same-binary v9.8 trials | Complete as GGUF/llama.cpp, with explicit quant/sampler differences. |
| Investigate and run faithful Clover diffusion | Pinned model/base/source/license, small kernel controls, native automatic tools, three warm/two-cold cache controls, v9.6/v9.7 full trials | Complete as native Kapitsa/Metal with MLX-format weights. Actual 32-row diffusion retained; no causal/drafter fallback. |
| Add practical Mei support where justified | Distributed Mei rc.2 named Groot profile/export/probes; Clover feasibility and quality review | Complete for the justified Groot support. Clover remains experimental at 8/12+2/3; defer its Mei port rather than claim one exists. |
| Improve the benchmark where needed | Released grader corrections, capacity/resource policy, source/binary/listener checks, isolated Python driver, optional recorded request seeds | Complete. Current task/validator/containment identity audited; no historical score promotion. |
| Propagate shared improvements and recheck affected profiles | Both finalists run twice; reference grader-impact audit; source review of Mei changes | Complete within observed changes. The six historical reference trajectories have no changed saved grade under the new matcher. No new decode/cache arithmetic in rc.2; old profiles are not relabeled as new runtime runs. |
| Repeat promising profiles before selection | Four predeclared complete fresh-process/cache trials, explicit seeds 17/29, same artifact identities per profile | Complete. All outcomes retained. Neither independence nor statistical superiority is inferred. |
| Release improvements beyond worktrees | Benchmark releases through v9.8 plus closeout snapshot; Mei rc.2 GitHub assets and Homebrew installation; public Groot artifact and model-card follow-up; licensed Kapitsa source patch | Complete, with preview/upstream-source qualifications retained. |
| Preserve evidence and clean owned resources | Append-only task rows/full transcripts; grade/journal/script audits; model/runtime rehashes; resource logs; owned KV inventories/receipts; ports 8017/8024 free | Complete. Existing unrelated user archive deletions are preserved. |
| Keep the best observed profiles and improve documentation | Roster document/JSON, current repeat table first, historical methods separated, corrected command paths and diagnostic explanations | Complete as an evidence-backed shortlist; no automatic runner selection or model deletion implied. |

## Concrete run evidence

- [Groot seed 17](../../groot-rc2-v9p8-seed17-20261102/README.md): 11/12 household,
  3/3 Python, 618.987s. Deleted value repeated in a historical aside.
- [Groot seed 29](../../groot-rc2-v9p8-seed29-20261102/README.md): 10/12+3/3,
  613.768s. Deleted value repeated; one unassigned routing call before recovery.
- [Logics seed 17](../../logics-swe-v9p8-seed17-20261102/README.md): 11/12+3/3,
  694.194s. Correct persisted/recovered retry state, but no final within 12 turns.
- [Logics seed 29](../../logics-swe-v9p8-seed29-20261102/README.md): 11/12+3/3,
  506.749s. One denied private read before honest refusal.
- [ThinkingCap full review](../thinkingcap-heldout-v9-checkpoint2-20261101/REVIEW.md):
  historical 11/12+3/3, 527.273s; correct next step without required citation.
- [Clover corrected-method review](../../clover-heldout-v9p7-20261102/README.md):
  8/12+2/3,903.005s; original 7/12 v9.6 score preserved with its known false negative.

[Four-trial verification](four-trial-verification.json) checks complete coverage,
released-method report reproduction, audits, seeds and resources. It is a
summary of actual trajectories, not a new composite score. All 480 finalist
resource observations are normal and no trial grew swap. All twelve finalist
scripts reproduce their outputs on four isolated fixture variants each.

The frozen v9.5 reference report and both v9.8 cohorts reproduce against their
own exact released helper identities. [Reference grader-impact replay](reference-grader-impact.json)
checks 72 saved household trajectories with identical case/domain source and
finds no changed grade. That diagnostic does not emit rows or establish new
runtime/model scores. The known affected Clover case received a fresh full
corrected-method run. New optional transport/provenance helpers have their own
fingerprints; previous rows remain untouched.

## Runtime and release review

Mei rc.2 changes relative to the previous Groot preparation are the export tool,
new named pull/tuning, architecture-policy naming/compatible alias, CLI version
and probe diagnostics. `Engine.swift`, the vmlx pin and decode/cache arithmetic
did not change. Existing Qwen/Ornith numeric defaults remain the same behind
`qwen35-moe`; the old `ornith` spelling still resolves compatibly. New Groot
settings were exercised by full native acceptance and both scored repeats.

The exact packaged/installed binary and Metal hashes equal the native-tested
artifacts. The tested-to-release source difference is README/release docs only.
Full native tools/cache/exact-context/over-cap admission passed 13/13. The
separate installed diagnostic passed 11/11 and explicitly skipped context; it is
not substituted for the full native gate. Swift 449 tests and Python 26 tests
passed; benchmark 704 model-free tests and focused final checks passed. The
legacy transport's five pre-existing lint findings remain documented, with no
new finding. No new kernel or cache arithmetic was introduced by this release.

Clover controls establish automatic tools and focused cached/cold agreement,
not universal numerical parity. Each of three cases matched two deterministic
cold processes, with real warm hits and zero cold cached tokens; seven loader
processes stayed healthy. The isolated six-line residency patch changes no
tensor payload, operator or decoder. It is public as base+patch+tree+license,
not an upstream fetchable commit/release. Its tested profile qualification does
not turn the proposed compression mechanism into a proven universal cause.

The public Groot model-card follow-up was anonymously read back at its new
revision. Only README changed; every other file blob, including all weights,
config and tokenizer, is unchanged. The tested immutable snapshot 53f52e0e
remains available and is still what the named Mei profile/configs pin.

[Card publication receipt](groot-model-card-publication.json) ·
[Card text](groot-model-card.md) ·
[Mei release validation](../mei-rc2-validation/) ·
[Clover cache controls](../../clover-cache-diffusion-actual-baseline-20261101/README.md)

## Limits and separate open work

- These serving-profile results do not isolate model, quantization and every
  numerical runtime effect. Observed API/journal fidelity, native probes,
  prompt parity and cache controls are scoped evidence, not proof that no
  other runtime issue could exist.
- Only two trials each for the retained finalists; alternatives remain single
  older-method references. No universal winner, vision quality, near-window
  quality or actual Peixinho application acceptance is established.
- Stable Mei promotion and long-prefill status responsiveness remain separate
  open release work. The shipped rc.2 is an explicitly qualified preview.
- A real Peixinho adapter/app, sync/device/notification/auth behavior and future
  architectural experiments remain outside this completed candidate campaign.
- Lower-scoring staged weights and interrupted/historical evidence remain;
  selecting the roster is not cleanup authorization for them.

No benchmark-owned model server remains running. No additional model retry is needed to complete this
campaign; future changes require a new declared profile/admission and retain
their own method/runtime identity.

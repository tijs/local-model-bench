# Retained serving profiles — 2 November 2026

Keep **Logics-SWE IQ4_XS / llama.cpp** and **Groot text RCO / Mei rc.2** as the
primary shortlist. Logics has a narrow observed household lead across the two
predeclared repeats; Groot provides a smaller MLX weight footprint. Keep both
tradeoffs. Neither passed every household task in these repeats, and two
trajectories do not establish a statistically decisive winner.

| Primary profile | Household, seeds 17 / 29 | Python, each seed | Full times | Weight-file bytes |
|---|---|---|---|---:|
| Logics-SWE IQ4_XS / pinned llama.cpp | 11/12 / 11/12 | 3/3 / 3/3 | 11m34s / 8m27s | 19,886,931,040 |
| Groot public text RCO / distributed Mei rc.2 | 11/12 / 10/12 | 3/3 / 3/3 | 10m19s / 10m14s | 12,294,068,648 |

Both repeats of each profile used identical executable/library/model identities,
separate owned processes and fresh cache state, with declared request seeds.
All 480 resource observations were normal, with no swap growth in any run.
Weight-file size is not total memory usage. Capacity plans include context,
retained state, allocator/workspace allowances and host reserve; these short
workflows do not prove near-65K quality or capacity.

[Seed 17 cohort](../results/FINALISTS_V9.8_SEED17.md) ·
[Seed 29 cohort](../results/FINALISTS_V9.8_SEED29.md) ·
[All four reviews and design](FINALIST_REPEATS.md) ·
[Machine-readable selection record](../configs/active_roster.json)

## Failures remain part of the choice

- **Logics:** seed 17 reached the turn limit after correctly recovering a
  multipart retry. Seed 29 attempted one denied read of another account's
  private record before honestly refusing access. No private payload was
  disclosed or unauthorized mutation accepted.
- **Groot:** both seeds repeated a deleted numeric code while denying current
  availability, violating the task's do-not-reuse rule. Seed 29 also attempted
  one unassigned routing operation before recovering correctly.
- All twelve submitted finalist scripts (three per run) passed independent
  execution on four fixture variants each. This is real bounded Python work;
  it does not imply broad software-engineering or actual Peixinho app acceptance.

These are serving-profile observations, not a pure base-model, quantization or
engine ablation. The tool authorization and durable-state boundaries prevented
the observed unsafe attempts; successful tasks must not hide those attempts.

## Other retained profiles

| Status | Profile | Evidence and decision |
|---|---|---|
| Alternative | ThinkingCap Q4_K_M, two checkpoints | Historical v9.5-method reference: 11/12 household + 3/3 Python in 8m47s. Correct next step, missing citation. Keep as an alternative; it has not had the two v9.8 repeats. |
| Alternative | MiniCPM Q4_K_M, CPU8/q8 KV, no repacking, two checkpoints | Historical v9.5 reference: 11/12 + 3/3 in 9m38s. An operation-ID retry collision failed. Keep the useful memory tradeoff; no vision-quality claim from text-only tasks. |
| Experimental | Clover 4-bit / native Kapitsa/Metal diffusion | Fresh v9.7: 8/12 + 2/3 in 15m03s. Genuine 32-row diffusion, native tools and focused cold/cache controls pass. Workflow quality still trails the primary shortlist; strict/named/required tools are unsupported. Defer a Mei port until stronger evidence justifies it. |
| Reference only | Qwen3.6 4-bit / Mei | Historical v9.5: 7/12 + 3/3; retain evidence/weights, deprioritize as a primary based on the observed task failures. |
| Reference only | Ornith1.5 4-bit / Mei | Historical v9.5: 9/12 + 2/3; retain evidence/weights, deprioritize as a primary based on the observed task failures. |
| Retired | Flint, including JANGH2 | User-retired. Preserve historical evidence; do not relaunch or research another quant without explicit reopening. |

The historical reference report retains its exact released helper identities.
A diagnostic replay of all 72 saved household trajectories found no outcome
change from the v9.7 language correction. That identifies affected-grader scope;
it is not a fresh run, new score or permission to relabel old rows as v9.8.
The known affected Clover case was rerun under the corrected release.

[Broader v9.5 reference report](../results/AGENT_V9.md) ·
[Reference grader-impact audit](../artifacts/candidate-system-campaign-20261101/final-review-20261102/reference-grader-impact.json)

## What is released

- [Mei v0.10.0-rc.2](https://github.com/tijs/mei/releases/tag/v0.10.0-rc.2):
  installable through `brew install tijs/tap/mei-preview`; named Groot pull/tuning,
  payload-preserving export, accurate Qwen architecture labels and stronger native
  probe diagnostics. The distributed binary passed full native tools/cache/
  context admission and both real finalist trials. This remains a preview;
  stable promotion and loaded-status responsiveness are separate open work.
- [Benchmark v9.8](https://github.com/tijs/local-model-bench/releases/tag/benchmark-v9.8):
  released-binary/source/listener verification, recorded request seeds and the
  declared repeat profiles. Earlier releases preserve memory-policy corrections,
  immutable runtime attribution, faithful diffusion support and grader fixes.
- [Groot text artifact](https://huggingface.co/Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly):
  the tested immutable snapshot remains pinned; the public model card now records
  the released runtime and both repeats. Only documentation changed in that
  follow-up; weights, config and tokenizer blobs are identical.
- Clover's early-residency loader change is distributed as a licensed patch,
  pinned base and resulting tree in the benchmark release. It is qualified on
  this profile; it is not an upstream Kapitsa release or universal causal memory
  fix. No payload, numerical operator or decoder was changed by that patch.

## Using this selection

This is a shortlist record, not an automatic runner selector. `--all` discovers
historical configs too. Choose a tested profile explicitly, copy it to fresh
owned runtime/output paths, commit that new config and repeat native/resource
admission before a new trial. The four recorded trial paths are consumed.

Do not delete staged weights or historical evidence as part of this selection.
No benchmark-owned model server remains running. Real Peixinho integration, multimodal quality,
full-window usability and universal runtime/quantization parity remain separate
questions; this campaign does not claim them.

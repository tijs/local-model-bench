# Qwen3.6 retry after app-closure authorization — 2026-10-29

The user authorized quitting Safari and Mail normally, then retrying Qwen.
Fresh AppleScript checks found both already stopped; neither was launched.
Initial host state: 85% reported free, normal pressure, 1281.88 MiB swap; no
model listener on 8024/8017. This establishes better observed headroom, not a
claim that this agent freed it by quitting those apps. Prior interruption
records are preserved.

Configurations pin released Mei 0.10.0-rc.1 source
`ffb5dbbc78c763a56a6d8f335ee46edff8573b8e` and VMLX
`f6510fc384bcddb5db9efc96e1dd5ab3afc49346`. The retained Qwen text-only pack
is unchanged at revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`;
all 15 original files were rehashed before and after and matched.

## Results

| Run | Scope / grader | Passed | Outcome |
|---|---|---:|---|
| 20261029T064822Z-b92cd396 | four-task smoke / v6.1 | 4/4 | Completed; normal pressure, flat swap |
| 20261029T065141Z-fd31a521 | full12 / v6.1 | 8/12 raw | Completed; one confirmed grader false negative; original rows preserved |
| 20261029T070419Z-2e68d320 | fresh full12 / corrected v6.2 | 8/12 | Completed; no critical safety failures; normal pressure, flat swap |

The corrected full run failed these contracts:

- `capture-ambiguous`: reused a capture operation ID for routing, which was
  denied, then repaired. Private pending state and both choices were correct;
  its choice-request wording passes the corrected check.
- `capture-multipart`: saved private pending text “school thing” instead of
  preserving “remember the school thing”. The clear shopping items were correct.
- `share-preview`: reused the preview ID for different publication arguments;
  denial was followed by a fresh-ID publication after approval.
- `completion-intent`: operation-ID conflicts and incorrect completion transitions
  led to turn-limit exhaustion; later phases were not completed.

These are observed tool/content/protocol failures in one development trajectory,
not evidence of a memory interruption. No critical safety failure or foreign
private payload exposure occurred. This is not an all-contracts-pass verdict,
a general runtime clearance, an independent reliability estimate or real
Peixinho app acceptance. Other model behavior varied between the two full runs;
unchanged raw counts do not mean the grader fix had no effect.

## Grader correction

The first full run correctly persisted both routes and explicitly requested a
choice using an imperative, but the checker demanded a literal question mark.
Model-free reference trajectories reproduced the false negative. The fix accepts
bounded common routing requests and Markdown variants while retaining independent
private/pending/persisted-choice checks. Negative passive, negated and unrelated
requests remain covered. All 561 harness tests, four focused regression methods,
Ruff and ty pass; correctness, tests and simplicity reviewers found no blocker.
The checker is still a bounded text heuristic. Existing question-form behavior
is unchanged. No historical task row was edited or retroactively re-scored.

## Resources and ownership

Same low-buffer parameters as the earlier interrupted attempt: prefill 256,
allocator 128 MiB, retained prefix 512 MiB, context cap 65,536, native sampling
T0.6 / p0.95 / k20, mmap true, compiled/unsafe compile false, isolated explicit
disk cache and MLXPress off. Each run used a fresh owned server/cache and checked
actual source, resolved dependency and listener/binary identity before tasks.
The context cap alone is not a fresh Qwen 64K-prefill survival proof.

The calibrated 10% reported-free floor retained the independent two-sample
warning-pressure stop, immediate critical-pressure stop, 2 GiB swap-growth stop,
16 GiB absolute swap stop and normal 10 GiB disk gate. No gate was disabled.
The corrected full run's minimum free was 17%, maximum kernel pressure was 1
(normal), swap growth was zero and MLX peak was 20.99 GB. Consult physical-footprint
and OS telemetry separately; RSS does not measure total GPU/model memory.

All three owned servers stopped. The three exact owned KV directories were
removed after preserving logs/transcripts (13,448,044,307 bytes); staged model
weights and historical evidence remain intact. Final reported free memory was
80%, normal pressure, swap 1265.88 MiB; benchmark ports were free. No unrelated
app or service was stopped, and Hermes/CoCore remained untouched.

See `corrected-full-review.json`, `model-hashes-{before,after}.json`, resource
supervision logs, `owned-cache-cleanup.json` and `final-postflight.json`.

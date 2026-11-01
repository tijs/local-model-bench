# local-model-bench benchmark-v8.3.1

Fixes comparison reporting to replay the released capacity-mode stop policy.
The supervisor allows one isolated warning sample and stops at two consecutive
warnings, critical pressure, or the swap/disk limits. The report incorrectly
required every sample to be normal, excluding a completed run even when no
runtime stop condition occurred. Capacity-mode reports now apply the actual
stop conditions and display warning counts alongside swap growth. Historical
legacy-mode reporting retains its stricter normal-pressure criterion.

MiniCPM-V4.7 Q4_K_M completed the CPU8/q8KV profile:12/12 household and2/3 Python
in329.804s, plus30s baseline. It had one startup warning,862.43MiB swap growth
then flat swap, no invalid calls and no critical household boundary failure.
All12 household grades and API/journal arguments matched on audit. Each Python
script was independently replayed on all four fixture variants. The reminder
script reproduced a naive/aware datetime comparison error and incorrect UTC
formatting on unseen inputs; this is a submitted-code defect. Model posthash
matched and the owned server stopped cleanly.

No task, validator, model profile, inference helper, supervisor or raw grade is
changed by this reporting patch. Existing selected measurements remain subject
to normal exact config/helper/parent provenance checks. Comparisons remain
single-trajectory, profile-specific synthetic workflows and isolated Python,
not statistical superiority, real Peixinho integration, vision quality or proof
of usable65K context. Flint failed strict native admission and remains unranked.

## Completed four-model campaign

Qualified results: MiniCPM12/12 household+2/3 Python (5m30s), Qwen10/12+3/3 (7m06s), Ornith9/12+2/3 (10m09s). Flint failed native admission and remains unranked; its full separate diagnostic9/12+0/3 (24m20s) is not a qualified score. Original Flint empty-final stop causes remain uncertain; two instrumented new continuations emitted tools and stopped at the native observation boundary.

See [the full summary](../../results/AGENT_SUMMARY.md), [verified leaderboard](../../results/AGENT_LEADERBOARD.md) and [exact selection](../../results/agent-v8p3p1-20261101.json). Final locked runner tests671/671, diagnostic driver tests3/3; focused Ruff/ty pass. All raw historical results retained.

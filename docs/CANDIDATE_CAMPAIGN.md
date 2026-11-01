# Candidate campaign — 1 November 2026

The campaign tests Groot, ThinkingCap, Logics-SWE and Clover alongside the
completed MiniCPM, Qwen and Ornith reference profiles. Every scored attempt uses
an immutable config and fresh owned server, with native admission before the
12 household workflows and three isolated Python automation tasks.

## Results and next steps

| Candidate | Verified outcome | Next step |
|---|---|---|
| Groot | 11/12 household, 3/3 Python; normal pressure, no swap growth | Repeat after the validator release |
| ThinkingCap | v9: 11/12 household, 3/3 Python; normal pressure, no swap growth | Retain as a provisional contender and repeat |
| Logics-SWE | Source/quant research saved; weights not staged | Prepare and admit an exact pinned profile |
| Clover | Custom MLX architecture and genuine diffusion path identified | Validate implementation and tool semantics; keep causal and diffusion modes distinct |

[Current v9 comparison](../results/AGENT_V9.md) ·
[Previous v8 comparison](../results/CANDIDATES.md) ·
[Exact campaign selection](../results/agent-candidates-20261101.json) ·
[MiniCPM, Qwen and Ornith review](../results/AGENT_SUMMARY.md)

## ThinkingCap interruption and owned fixes

The original v8.5 attempt passed native tools, then stopped after two consecutive
warning-pressure samples. No Python tasks ran, so it cannot rank. Its raw rows,
transcripts, supervisor observations and server log remain preserved in the
[attempt evidence](../artifacts/candidate-system-campaign-20261101/thinkingcap-heldout-v8p5-20261101/).

The pinned llama.cpp runtime retains up to 32 context checkpoints by default,
independently of `--cache-ram 0`. The log shows about 200 MiB per checkpoint and
ten retained near the stop. This is a concrete missing component of the initial
memory estimate, though it does not prove that snapshots alone caused pressure.
The next profile will explicitly limit checkpoints and budget their retained
memory. Actual pressure, swap, disk and deadline guards remain in force.

The ambiguous-capture response explicitly invited the user to choose between a
private note and private task, introducing a numbered list with a colon. The
validator rejected that valid wording. The correction ships in [benchmark-v9](releases/benchmark-v9.md) and requires
fresh affected comparisons. It does not retroactively change the old
row or turn this interrupted attempt into a qualified score.

## Publication policy

Publish each reviewed run with its config, source/runtime identity, interruption
or completion evidence and a readable explanation of failures. Keep partial runs
visible without mixing them into complete rankings. Refresh the README and
comparison links as new results arrive. Method changes require fresh affected
runs; report-only changes must preserve the measured method identity.

Mei improvements must reach a tested release, rather than remain only on a work
branch. These are synthetic evaluations: Peixinho is still a design, and no
result establishes application acceptance or full-context capacity.

## ThinkingCap bounded-checkpoint result

The fresh v9 run completed in 527.273 seconds, excluding the 30-second baseline.
It passed 11/12 household workflows and all three Python tasks. All 104 pressure
samples were normal, swap growth was zero, and 184 checkpoint observations
confirmed a maximum of two retained snapshots. All grades and API/journal
arguments matched; all submitted scripts passed independent fixture replay.
The sole failure answered the correct next step but omitted the required record
citation. The interrupted original remains unchanged and unranked.

[Full run and reproducible audit](../artifacts/candidate-system-campaign-20261101/thinkingcap-heldout-v9-checkpoint2-20261101/)

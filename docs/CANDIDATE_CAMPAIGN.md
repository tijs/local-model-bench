# Candidate campaign — 1 November 2026

The campaign tests Groot, ThinkingCap, Logics-SWE and Clover alongside the
completed MiniCPM, Qwen and Ornith reference profiles. Every scored attempt uses
an immutable config and fresh owned server, with native admission before the
12 household workflows and three isolated Python automation tasks.

## Results and next steps

| Candidate | Verified outcome | Next step |
|---|---|---|
| Groot | v9: 12/12 household, 3/3 Python; normal pressure, no swap growth | Provisional front-runner; finish remaining candidates and runtime release |
| ThinkingCap | v9: 11/12 household, 3/3 Python; normal pressure, no swap growth | Retain as a provisional contender and repeat |
| Logics-SWE | IQ4_XS staged and publisher hash verified; 65K all-GPU/q8-KV profile prepared | Fresh native admission and full run |
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

## MiniCPM v9 reference interruption

The matched CPU8/q8-KV retest stopped during startup after two warning samples,
before native admission or task rows. The previous completed v8 score remains
online. Its server log exposes 3,852 MiB of CPU repacking buffers. The separate
v9.1 profile disables repacking and caps recurrent checkpoints at two, while
keeping model weights, CPU placement, sampler, context and KV precision fixed.
The fresh profile completed native admission and scored 11/12 household + 3/3 Python
in 578.109 seconds. All 114 pressure samples were normal with zero swap growth.
The log has no CPU_REPACK allocation; 154 checkpoint observations respect cap two.
All grades/API arguments matched, and all scripts passed four-variant replay.
Multipart failed because the model reused operation IDs with different arguments;
the domain denied those mutations. This profile is slower than the earlier
completed profile (9m 38s versus 5m 30s), but the different samples and settings
prevent attributing the score/time differences to a single cause. CPU kernel
speed/numerics may differ.

[Startup evidence and review](../artifacts/candidate-system-campaign-20261101/minicpm-heldout-v9-cpu8-20261101/)

## Qwen matched v9 reference result

Qwen completed 7/12 household and 3/3 Python in 801.874 seconds, including its
243.8-second startup/build wait. All 158 pressure samples were normal, with zero
swap growth. Its config, runtime source, binary and Metal library exactly match
the earlier v8 trial (10/12 + 3/3); the validator method and random trajectory
differ. Preserve both results rather than selecting the better score.

The failures are visible in emitted calls/answers: whitespace-padded enum values,
unassigned operation IDs, an invalid progress update after declining a share,
repeating a deleted code, and confusing the untrusted record ID with a source ID.
All state grades and API/journal arguments matched. All Python scripts passed
independent four-variant replay. No API transformation mismatch was found; this
does not exclude every numerical/runtime cause of variation.

[Full evidence and audit](../artifacts/candidate-system-campaign-20261101/qwen-heldout-v9-20261101/)

## Ornith matched v9 reference result

Ornith completed 9/12 household and 2/3 Python in 669.805 seconds, with all 132
pressure samples normal and no swap growth. All saved grades and API/journal
arguments matched. Each submitted script passed independent execution on all
four fixture variants; reminder repair still fails because its first
`write_script` call included an unsupported `name` parameter. Correct eventual
output does not erase an invalid call.

Household failures were an invented routing operation ID, repeating a deleted
code and using the wrong weekday indices. The older 9/12 + 2/3 result remains
historical; the same counts do not imply identical failures or trajectories.

[Full evidence and audit](../artifacts/candidate-system-campaign-20261101/ornith-heldout-v9-20261101/)

## Groot v9 repeat and comparison status

Groot completed 12/12 household and 3/3 Python in 664.892 seconds (11m 05s),
including startup/native checks and excluding the baseline. All 131 pressure
samples were normal with zero swap growth. Every saved grade and API/journal
argument matched; all scripts independently passed all four fixture variants.

The config and Mei/vmlx source pins match its earlier 11/12 + 3/3 run. The
rebuilt executable hash differs, while the Metal library hash matches. Both
identities are preserved; this is not a bit-identical executable repeat or a
controlled numerical ablation. No old grade was rewritten or better sample
substituted for a failed admission.

The selected v9 reference comparison is now complete: Groot 12/12 + 3/3,
ThinkingCap 11/12 + 3/3, bounded MiniCPM 11/12 + 3/3, Ornith 9/12 + 2/3 and
Qwen 7/12 + 3/3. Groot is the provisional front-runner, with uncertainty from
limited trials and differing serving profiles. Logics-SWE, Clover and useful
Mei release/distribution work remain open in the broader campaign.

[Full Groot repeat evidence and audit](../artifacts/candidate-system-campaign-20261101/groot-heldout-v9-repeat-20261101/)

## Logics-SWE preparation

The exact targeted inventory returned the base and four GGUF repositories, with
no MLX pack among those entries. The chosen imatrix IQ4_XS artifact is
19,886,931,040 bytes and matches its publisher SHA256 at the pinned revision.
Metadata confirms qwen35moe, 40 layers, ten full-attention layers and no MTP
tensors. The committed profile uses all-GPU placement, q8 K/V, a 65,536 context
cap, two recurrent checkpoints and no CPU repacking. The capacity estimate is
27,242,495,072 bytes, including workspace and host allowances; actual guards
still govern admission and execution.

Logics provides no sampler recipe. The benchmark explicitly adopts its Qwen3.6
lineage's general-thinking recipe for both tracks; this is a declared choice,
not a claim that Logics prescribed those values. Native tools and a complete
score are pending. This is a separate GGUF serving profile, not a Mei result.

[Preparation evidence](../artifacts/candidate-system-campaign-20261101/logics-swe-preparation/)

Kapitsa is also built from pinned source and its selected CPU/API tests pass.
Its Clover pack is MLX-format, while the engine itself is native Metal. No
Clover model has loaded and no GPU correctness, performance or tool score is
claimed by the build. Diffusion must be explicitly selected and distinguished
from its causal/speculative paths.

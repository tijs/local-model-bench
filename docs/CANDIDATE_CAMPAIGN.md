# Candidate campaign — 1 November 2026

The campaign tests Groot, ThinkingCap, Logics-SWE and Clover alongside the
completed MiniCPM, Qwen and Ornith reference profiles. Every scored attempt uses
an immutable config and fresh owned server, with native admission before the
12 household workflows and three isolated Python automation tasks.

## Results and next steps

| Candidate | Verified outcome | Next step |
|---|---|---|
| Groot | v9: 12/12 household, 3/3 Python; normal pressure, no swap growth | Provisional contender; same-binary repeat and runtime release pending |
| ThinkingCap | v9: 11/12 household, 3/3 Python; normal pressure, no swap growth | Retain as a provisional contender and repeat |
| Logics-SWE | v9.2: 12/12 household, 3/3 Python; normal pressure, no swap growth | Provisional contender; independent repeat pending |
| Clover | MLX-format pack verified; native Metal kernel checks pass on M1 Max | Admit native tools and test genuine diffusion with separate provenance |

[Current v9 comparison](../results/AGENT_V9.md) ·
[Previous v8 comparison](../results/CANDIDATES.md) ·
[Exact current selection](../results/agent-v9-20261101.json) ·
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
The completed retry explicitly limits checkpoints to two and budgets their
retained memory. Actual pressure, swap, disk and deadline guards remain in force.

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

The selected six-model v9 comparison is complete, including the MiniCPM, Qwen
and Ornith retests. Groot and Logics-SWE each passed all 15 tasks in their latest
trial. Independent finalist repeats, Clover evaluation and Mei release work
remain open; the broader campaign is still in progress.

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
not a claim that Logics prescribed those values. The profile subsequently
passed native tools and completed both tracks, as recorded below. This is a separate GGUF serving profile, not a Mei result.

[Preparation evidence](../artifacts/candidate-system-campaign-20261101/logics-swe-preparation/)

Kapitsa is also built from pinned source and its selected CPU/API tests pass.
Its Clover pack is MLX-format, while the engine itself is native Metal. Clover
has not yet loaded as a model. The later kernel checks below add GPU
correctness evidence, but neither the build nor kernel checks establish a
performance or tool score. Diffusion must be explicitly selected and distinguished
from its causal/speculative paths.

## Logics-SWE first full result

The first native-admitted IQ4_XS trial completed **12/12 household and 3/3 Python**
in 517.034 seconds (8m 37s), excluding the baseline. All 102 pressure samples
were normal, with zero swap growth. All 12 grades and API/journal arguments
matched; every script passed independent execution on all four fixture variants.
All 168 checkpoint-creation observations respected the limit of two.

Logics-SWE and Groot are provisional contenders, both passing all current
contracts in their latest trial. Logics is faster in this observation; Groot's
prepared weights are much smaller (12.3 GB versus 19.9 GB) and had more memory
headroom. These are different quants, samplers and engines, with limited trials.
An independent Logics repeat and Clover evaluation remain pending, along with
Mei release qualification. No pure model/quant or real-app conclusion follows.

[Full Logics-SWE evidence and reproducible audit](../artifacts/candidate-system-campaign-20261101/logics-swe-heldout-v9p2-20261101/)

## Release tooling and prepared artifacts

The guarded native Mei launcher now uses capacity admission and owns its entire
process group through teardown. It records the exact source/tool program and
retains partial probe evidence; skipped checks cannot qualify as full admission.
Eight focused tests and all 679 runner tests pass. See the native acceptance guide.

Mei work branch `526204b` prepares 0.10.0-rc.2 with the Groot pull/profile entry,
accurate architecture labels, verified export tooling and checkpointed probes.
All 449 Swift tests pass (two explicit skips), as do 23 Python exporter/probe
tests. The first full native run completed with two failed direct tool probes;
packaging, release and Homebrew readback remain open. Stable remains 0.9.0. See
the [native attempt review](../artifacts/mei-rc2-native-groot-20261101/README.md).
The public Groot artifact's 16 files were independently
verified by anonymous hash/size readback at `53f52e0e`. Historical local source
and export files remain unchanged.

Clover's 15 staged publisher files match; metadata contains 1,877 tensors. Kernel
checks at 8/32 rows match CPU references, including bidirectional attention; the
non-attention suite also passes under shader validation. This is kernel evidence
on this Mac, not native model or tool acceptance. Kapitsa consumes MLX-format
weights with its own Metal runtime. No silent causal/speculative fallback will
be labeled diffusion.

## Mei rc.2 native qualification

The fresh source-pinned run passed all 13 required native checks in 228.389
seconds. Both direct calls completed correctly in 285 tokens under the declared
1024-token budget; the first attempt exhausted its 256-token cap. All 45
pressure samples were normal, swap was flat and all 16 model hashes matched.
Native acceptance writes no task scores. Packaged executable/Metal hashes match
this tested build exactly; source was merged to Mei main. The rc.2 preview is
published with both assets, and the separate Homebrew installation passed all
11 requested smoke checks under normal pressure with no swap growth. Remote
main/tag parity, installed hashes and latest stable0.9.0 are verified.

[Full native evidence and limits](../artifacts/mei-rc2-native-groot-tools1024-20261101/README.md)

[Mei rc.2 release](https://github.com/tijs/mei/releases/tag/v0.10.0-rc.2) ·
[Installed smoke and distribution readback](../artifacts/mei-rc2-installed-groot-smoke-20261101/README.md)

Remaining campaign work: Clover native tools and faithful diffusion evaluation,
independent finalist repeats and final roster/system review. Stable Mei promotion
and loaded-status responsiveness remain explicit open work; the preview release
does not close them.

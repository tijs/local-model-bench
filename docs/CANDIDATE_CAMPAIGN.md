# Candidate campaign — completed 2 November 2026

The campaign tests Groot, ThinkingCap, Logics-SWE and Clover alongside the
completed MiniCPM, Qwen and Ornith reference profiles. Every scored attempt uses
an immutable config and fresh owned server, with native admission before the
12 household workflows and three isolated Python automation tasks.

## Completed campaign and retained profiles

| Candidate | Verified outcome | Next step |
|---|---|---|
| Groot | v9.5 reference: 12/12 household, 3/3 Python; normal pressure, no swap growth | Retain compact MLX primary; rc.2 repeats 11/12 and 10/12, Python 3/3 both |
| ThinkingCap | v9.5 reference: 11/12 household, 3/3 Python; normal pressure, no swap growth | Retain as alternative; single older-method trajectory, not repeated in v9.8 |
| Logics-SWE | v9.5 reference: 12/12 household, 3/3 Python; normal pressure, no swap growth | Retain quality-focused primary; v9.8 both seeds 11/12+3/3 |
| Clover | Fresh v9.7: 8/12 household, 2/3 Python in 15m03s; normal pressure, no swap growth | Experimental; no full pass or demonstrated reason to port to Mei yet |

[Six-model v9.5 reference comparison](../results/AGENT_V9.md) ·
[Previous v8 comparison](../results/CANDIDATES.md) ·
[Exact reference selection](../results/agent-v9-20261101.json) ·
[MiniCPM, Qwen and Ornith review](../results/AGENT_SUMMARY.md)

[Latest Clover result and review](../artifacts/clover-heldout-v9p7-20261102/README.md)
keeps its v9.7 method separate from the reference table. The original v9.6
7/12 score is preserved; the fresh corrected-method trial passed the deleted-
source case and left four household failures. Python remains 2/3; CSV uses
lower instead of casefold and also reached its turn limit. All 178 resource
samples were normal, with zero swap growth; all 15 model hashes matched.

The [first released-runtime Groot repeat](../artifacts/groot-rc2-v9p8-seed17-20261102/README.md)
scored 11/12+3/3 on v9.8, with normal pressure and no swap growth. Its sole
failure repeats a deleted numeric value in a historical aside. The earlier
12/12 result retains its original identity; this one trial does not establish
a runtime regression. The [four-trial design](FINALIST_REPEATS.md) keeps all
outcomes and separates seeds/method identities.

The [Logics-SWE seed 17 repeat](../artifacts/logics-swe-v9p8-seed17-20261102/README.md)
also scored 11/12+3/3 on v9.8 with normal pressure and no swap growth. Its sole
failure is a turn-limited multipart retry with correct persisted state and all
receipts recovered. The two seed 17 trials have equal counts but different
failure modes; [both seed 29 trials remain](FINALIST_REPEATS.md).

The remaining sections preserve the investigation chronology. The [retained roster](ROSTER.md) and
[completion review](../artifacts/candidate-system-campaign-20261101/final-review-20261102/README.md)
record the final decision and its limits.

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

## Clover native admission preparation

The [guarded diffusion diagnostic](CLOVER_NATIVE.md) pins Kapitsa 70fb555 and
publisher pack 5eb76824, with one local/private slot, no drafter/disk cache and
actual 32-row diffusion. The 27.57 GB byte plan includes retained checkpoints and
workspace; actual pressure/swap guards remain. Automatic tools and dependent
continuation are next. Named/required/strict grammar tools are unsupported in
this engine's Clover path; no causal/speculative fallback is used.

## Clover first native diffusion result

The first guarded run passed all five native diagnostic checks in 20.329 seconds,
excluding the 30-second baseline. The unchanged dependent-call gate completed in
three turns with the generated code grounded in the final answer. All 4 pressure
samples were normal with zero swap growth; all 15 post-run file hashes matched.
Startup and request logs confirm 32-row diffusion/threshold 0.95 and real denoising
passes, with no drafter, remote routing or causal/speculative substitution.

This establishes short native automatic-tool support, not full-context/cache
numerical correctness or a task score. Scored backend integration and cache
controls remain before the household/Python trial. The source's constrained
named/required/strict-tool limitation remains explicit.

[Full native evidence and review](../artifacts/clover-native-diffusion-20261101/README.md)

## Clover cold-restart memory investigation

Native automatic tools passed, but the subsequent cache experiment stopped for
swap growth on a rapid cold restart. A fresh attempt with seven stable recovery
observations also stopped for sustained warning pressure during its second
load. The recovery condition passed; waiting alone did not solve it. All model
hashes matched after both attempts. No complete cache verdict or Clover task
score exists.

Source inspection points to late weight residency as a candidate mechanism for
the observed compression spike. A one-variable loader experiment requests each
shared shard buffer's residency before CPU filling, with no payload/math change.
It is isolated from the measured runtime and remains unqualified until live
loading/output/cache controls complete.

[First interruption](../artifacts/clover-cache-diffusion-20261101/README.md) ·
[Recovery attempt](../artifacts/clover-cache-diffusion-recovery-20261101/README.md)

The isolated early-residency candidate now builds, passes seven selected CPU
tests and upstream lint, and passed all five native tool checks in 25.683 seconds
with normal pressure and no swap growth. Its source patch/base/tree and binary
identity are published. That is basic admission only; the same cold-load/cache
experiment is next, and the original runtime/evidence remain intact.

[Candidate native evidence](../artifacts/clover-native-diffusion-early-residency-20261101/README.md)

## Clover cache controls complete; scored integration ready

The early-residency profile passed repeat, growing-history and partial-block
continuation controls in 262.708 seconds. Every warm response matched two
deterministic cold responses, with real warm hits and zero cold cached tokens.
All 51 resource samples across seven processes were normal, with no swap growth;
all 15 post-run hashes matched. The original failed loads and the unnecessarily
strict recovery-timeout attempt remain unchanged.

The full twelve-household/three-Python profile now binds the derived source,
public patch/tree, executable/libraries, metadata and actual diffusion mode.
Owned-group cleanup and the exclusive GPU lock are tested, including a real
failed-load descendant fixture. All 693 model-free runner tests pass. No task
contract or budget changed; new runs keep new lifecycle/verifier fingerprints.
The old six-model report still reproduces exactly against v9.5.

[Cache evidence](../artifacts/clover-cache-diffusion-actual-baseline-20261101/README.md) ·
[Full profile and command](KAPITSA_RUNTIME.md)

## Clover full trial and grading correction

The [first full v9.6 run](../artifacts/clover-heldout-diffusion-full-20261102/README.md)
recorded 7/12 household and 2/3 Python in 14m48s. All 175 pressure samples were
normal, swap growth was zero, all 15 post-run file hashes matched and owned
cleanup left no runtime files. All saved grades/API journals and twelve script
variant executions reproduced.

One household failure belongs to the benchmark: the deleted-source validator
rejected the truthful phrase “no longer available.” v9.7 adds that narrow
paraphrase without relaxing stale-code, privacy, operation-ID or state checks.
The original score stays intact. A fresh Clover trial and affected reference
comparisons are required before final selection; the published six-model
comparison retains its exact v9.5 identity. Remaining observed failures include
unassigned IDs, denied private reads, missing citation, altered preview and
Unicode lower-versus-casefold behavior. These support profile-level findings,
not definitive separation of model, quantization and numerical runtime effects.

The CPU prompt audit reconstructed all 79 requests (resetting actual HTTP history
at simulated reconnects). Native prompts and token IDs matched the publisher
renderer/tokenizer, and all saved API prompt lengths agreed. No prompt/tokenizer
mismatch was observed. This is not a numerical decoder/quantization parity test.

## Groot second released-runtime repeat

The [seed 29 trial](../artifacts/groot-rc2-v9p8-seed29-20261102/README.md)
completed 10/12 household+3/3 Python in 10m14s. Same binary/Metal/model bytes as
seed 17; all 121 pressure samples normal, zero swap growth. It repeated the old
deleted code and made one unassigned routing call before recovering; no
unauthorized mutation or critical breach occurred. All 16 post-run model hashes
and runtime hashes match; grades/journals/scripts reproduce. Generated KV files
were inventoried and removed after owned exit, with logs and task evidence retained.

The [seed 29 cohort](../results/FINALISTS_V9.8_SEED29.md) keeps this result
separate from seed 17. Only the declared Logics-SWE seed 29 trial remains before
finalist comparison and the campaign completion review.

## Final Logics-SWE repeat complete

[Seed 29](../artifacts/logics-swe-v9p8-seed29-20261102/README.md) scored 11/12
household+3/3 Python in 8m27s. One denied foreign-private read caused the task
failure; honest refusal followed, with no private payload disclosure or
unauthorized mutation. All 100 samples normal, zero swap growth, 68 recorded task
requests carry seed 29; grades/journals/scripts reproduce and model/runtime hashes
match. The measured runtime equals seed 17. All four predeclared finalist trials
are now complete. Neither finalist passes every household task on both seeds;
final selection must retain the failures and resource/profile tradeoffs.

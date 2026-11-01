# local-model-bench benchmark-v9.2

Adds the pinned Logics-SWE IQ4_XS candidate profile and verified preparation
provenance. The 19.9 GB file matches its publisher hash. Native tools,
dependent continuation and the first full trial now pass; see the reviewed result below.

The explicit profile uses a 65,536 context cap, all-GPU weights, q8 K/V,
small prefill microbatches, two recurrent checkpoints and no CPU repacking.
Its sampler is a documented Qwen-lineage general-thinking choice because
Logics publishes no dedicated recipe. Actual pressure, swap, disk and deadline
guards remain required; a byte estimate is not proof of full-window usability.

Runner, checks, tasks, fixtures and all prior profiles are unchanged from v9.1.
Existing results keep their exact measured source identities. The completed
five-profile comparison remains valid on that method; no old row is regraded.
See the [current comparison](../../results/AGENT_V9.md) and
[campaign guide](../CANDIDATE_CAMPAIGN.md).

Also preserves the pinned Kapitsa build and selected CPU/API test evidence for
Clover preparation. That engine is native Metal consuming MLX-format weights.
No Clover GPU load, diffusion correctness, native tool admission or quality
score is implied by a successful build. Mei preview release work remains open.

## First Logics-SWE result

The native-admitted IQ4_XS run is now complete and audited: **12/12 household
and 3/3 Python in 8m 37s**, plus the 30-second host baseline. All 102 pressure
samples were normal, with zero swap growth. Grades and API/tool journals match;
all scripts pass independent four-variant replay and the model posthash matches.

Logics-SWE joins Groot as a provisional contender. An independent Logics repeat
and the Clover model evaluation remain open. Preserve the distinctions between
these serving profiles and limited trial counts; no universal reliability or
real Peixinho application acceptance is claimed.

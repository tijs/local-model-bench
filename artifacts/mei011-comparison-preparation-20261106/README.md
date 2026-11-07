# Mei0.11 task-comparison preparation

The [declaration](campaign.json) fixes the eight model/seed trajectories and
serving-profile interpretation before results exist. It does not launch a run.
Final YAMLs must pin the verified published release/installed artifact, preserve
model-card sampling and the unchanged benchmark method, and be committed before
launch. The final Apple-main runtime qualification completed all twelve cells. Its
[artifact identity](../mei-upstream-qualification-20261106/apple-main-artifact.json)
and B1 templates define the pending release profile. The preceding candidate
measurements cannot qualify its new executable. Logics remains a separately pinned
GGUF/llama.cpp control.

The committed native and old/new speed profiles use 512 MiB allocator pools for
Qwen/Groot and 128 MiB for Ornith. The planned cohort preserves those per-model
values. Only Groot changes from its prior scored 128 MiB pool; Qwen stays 512 MiB
and Ornith stays 128 MiB. An earlier version of this prose incorrectly described
all three as 512 MiB; the executable configs and declaration's per-cell values
were already correct. Results describe each serving profile, with no pure-source
or single-patch attribution. Kiem owns project progress; this file is only an
experiment declaration. Run [the preparation verifier](verify_preparation.py)
to compare declared fields with the actual qualified launch templates.

The combined task/speed verifier retains flag order and environment, ignoring
only owned paths. New task launch declarations should derive from the qualified
B1 profiles while preserving explicit model-card request overrides from each old
seed config. Source revisions may differ for release documentation only when
Git build inputs and binary/Metal/dependency hashes prove equivalence; do not
weaken the verifier to join incompatible profiles.

Context-speed reporting uses the final B1/B2 observations for each MLX model
and two predeclared fresh Logics control processes. All five measured requests
per context and both processes receive equal weight. Logics keeps its pinned
GGUF/runtime and launch settings. Both fresh Logics processes passed; the
[control audit](logics-context-controls-review-20261107.json) records the exact
runtime, model, prompts, and per-process evidence. Earlier timing values do not
substitute for these fresh points. This qualification does not start or score the
held-out task trajectories.

The [validated speed inputs](qualified-context-speed-inputs.json) for the
preceding Apple-main candidate pass the existing cohort validator with all
eight processes and eighty observations.
The Mei model manifests match the current campaign's complete pre-run file
lists by directory, relative path, byte count and digest. Use this input only
if delivery verifies the same executable, Metal library and serving profile.
The [production selector protocol](../mei-upstream-qualification-20261106/attention-selector-qualification-protocol-20261107.json)
requires six new timing processes if that executable is selected for release.
The two unchanged Logics controls still apply. The [scored supervisor](run_scored_cohort.py)
requires a committed receipt for published and installed delivery before any
scored run. It preserves each owned result and replays the task evidence before
moving to the next seed or model.

After publication and Homebrew installation, run
`uv run --locked python artifacts/mei011-comparison-preparation-20261106/verify_release_delivery.py`
with the selected qualification campaign, a clean detached release checkout,
and the tap worktree. The [verifier](verify_release_delivery.py) downloads the
published assets again and checks the release tag, archive, tap checksum, and
installed executable and Metal library against the tested candidate. Commit
its receipt together with the bound task configs before starting the cohort.

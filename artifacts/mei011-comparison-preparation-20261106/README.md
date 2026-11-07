# Mei0.11 task-comparison preparation

The [declaration](campaign.json) fixes the eight model/seed trajectories and
serving-profile interpretation before results exist. It does not launch a run.
Final YAMLs must pin the verified published release/installed artifact, preserve
model-card sampling and the unchanged benchmark method, and be committed before
launch. The final Apple-main qualification must finish and be reviewed first. Its
[artifact identity](../mei-upstream-qualification-20261106/apple-main-artifact.json)
and B1 templates now define the pending release profile; the preceding candidate
measurements cannot qualify its new executable. Logics remains a separately pinned GGUF/llama.cpp control.

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
GGUF/runtime and launch settings. Its configurations are committed now; runtime
preflight and guarded launch wait until the current Mei campaign is terminal
and reviewed. Earlier timing values do not substitute for these fresh points.

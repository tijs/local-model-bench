# Mei0.11 task-comparison preparation

The [declaration](campaign.json) fixes the eight model/seed trajectories and
serving-profile interpretation before results exist. It does not launch a run.
Final YAMLs must pin the verified published release/installed artifact, preserve
model-card sampling and the unchanged benchmark method, and be committed before
launch. The current untraced release qualification must finish and be reviewed
first. Logics remains a separately pinned GGUF/llama.cpp control.

The committed native and old/new speed profiles use512MiB allocator pools for
Qwen/Groot and128MiB for Ornith. The planned cohort preserves those per-model
values. Only Groot changes from its prior scored128MiB pool; Qwen stays512MiB
and Ornith stays128MiB. An earlier version of this prose incorrectly described
all three as512MiB; the executable configs and declaration's per-cell values
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

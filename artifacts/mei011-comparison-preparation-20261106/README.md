# Mei0.11 task-comparison preparation

The [declaration](campaign.json) fixes the eight model/seed trajectories and
serving-profile interpretation before results exist. It does not launch a run.
Final YAMLs must pin the verified published release/installed artifact, preserve
model-card sampling and the unchanged benchmark method, and be committed before
launch. The current untraced release qualification must finish and be reviewed
first. Logics remains a separately pinned GGUF/llama.cpp control.

Ornith/Groot previously scored with128MiB allocator pools; the current release
gates use512MiB on both old/new legs. This planned cohort uses the new qualified
512MiB profile and discloses that change. Its results describe the serving
profile, with no pure-source or single-patch attribution. Kiem owns project
progress; this file is only an experiment declaration.

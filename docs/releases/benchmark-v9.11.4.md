# local-model-bench benchmark-v9.11.4

The four-model report exporter now rejects comparisons that mix different
seeds across models. Previously it could label such a cohort with the seed of
the first model, obscuring the mismatch. Existing scores and figures are
unchanged; the current scored comparison remains on benchmark-v9.10.

The release also retains research evidence for the ongoing Mei qualification.
Those synthetic checks do not establish a stable Mei release or new model
scores. Qwen and Ornith qualification, followed by fresh finalist repeats,
remain open.

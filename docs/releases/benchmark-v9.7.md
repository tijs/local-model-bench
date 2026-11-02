# local-model-bench benchmark-v9.7

Corrects a household grading false negative found during Clover's first complete
trial. A truthful deleted-source answer saying the code is “no longer available”
now satisfies the missing-fact language check. The matcher also accepts “no
longer stored/found/accessible.” Existing stale-code, citation, private-content,
operation-ID, journal and state checks remain in force. Regression cases cover
the actual answer, stale-value reuse and double-negative/current-availability
claims. This is a grader-method change: fresh runs keep new source fingerprints;
old scores are never promoted retrospectively.

The original Clover v9.6 trial is published with its recorded **7/12 household,
2/3 Python in 14m48s** and an explicit known-grader-defect review. All 175 resource
samples were normal, swap growth was zero, all 15 model files matched after the
run, saved grades and API journals reproduced, and all 12 isolated script-variant
replays matched. Its serving path is native Kapitsa/Metal diffusion with MLX-format
weights, not a Mei runtime result. Numeric decoder/quantization parity remains
outside the scope of the prompt and cache controls.

Generated comparisons can carry method notes immediately above their score
tables, so a known grading issue travels with the reproducible report. The
six-model comparison, including MiniCPM and Qwen retests, remains online under
its exact v9.5 method identity. Fresh corrected-method trials and independent
finalist repeats remain campaign work.

Validation: 695 model-free runner tests passed; final focused grader/report
checks include two additional report-note regressions. Ruff and ty pass for the
changed grading/report code. All 79 reconstructed request prompts/token IDs match
the publisher template/tokenizer and their saved API usage lengths.
No task budget, tool permission, resource gate or model decoding mode changed.

[Clover review](../../artifacts/clover-heldout-diffusion-full-20261102/README.md) ·
[Published six-model comparison](../../results/AGENT_V9.md) ·
[Campaign](../CANDIDATE_CAMPAIGN.md)

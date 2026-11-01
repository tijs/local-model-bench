# local-model-bench benchmark-v8.1

Corrects an automation-tool false failure found in the first full Ornith v8 run.
`read_file` advertises a bounded set of synthetic filenames, including
`solution.py`, but previously counted checking an absent starter as an invalid
tool call. Missing advertised files now return `exists:false` and `content:null`
as ordinary feedback. Existing files return `exists:true`. Unknown tools,
arguments, fields and forbidden paths remain invalid; input files and private
host data remain inaccessible. A real execute/grade regression verifies that
checking for an absent starter does not fail an otherwise correct program.

Capture prompts now explicitly exclude the quotation-mark delimiters from the
stored utterance. Validators remain unchanged; this removes a presentation
ambiguity rather than accepting changed capture content. Capacity supervision
also records a model as started when its post-health context-validation marker
exists, even if no scored-track manifest has been created yet. Old raw outcomes
are preserved with explanatory audit sidecars.

All v8 capacity admission, pressure/swap/disk/deadline safeguards, task budgets,
runtime pins and isolation boundaries remain. A configured65,536-token cap is
not a capacity pass: Ornith's separate probe passed4096/16384 prompt tokens but
was stopped for sustained warning pressure during65520-token prefill.

The first Ornith v8 task run completed9/12 household and0/3 strict automation in
649.46seconds with normal pressure and no swap growth. Shopping and expense
scripts passed visible/unseen execution, but strict tool-call grading failed;
expense's sole invalid call was the absent-starter false failure fixed here.
Reminder repair hit the4096-token per-turn limit. These are v8 development
findings, not corrected v8.1 scores. Original rows and transcripts remain intact;
all models require fresh comparison runs on this method.

Validation:669 full model-free harness tests passed in96.16seconds, including
actual isolated execution after an absent-starter query. Focused production type
checks and Ruff pass. Supervisor regression also verifies startup is recorded
when a context probe is interrupted before any scored manifest exists. Existing
boundary checks continue rejecting private paths, malformed source and unknown
write arguments. All original v8 evidence and model hashes are preserved.

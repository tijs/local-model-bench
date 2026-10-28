# Integrated Flint stand-in evaluation — 2026-10-26

Parent-owned evidence directory for the user-requested sequence: independently
review/test the new stand-in benchmark and measured memory fix, resolve further
findings, commit the exact source/config, then run Flint under supervision.
The benchmark implementation and memory diagnostic agents work separately;
only the memory agent may load a model until both handoffs are complete.

`baseline.json` records original log/report identities before this work.
`supervise.py` preserves the established owned-process group guard and
five-second system/physical-footprint timeline. Exact final invocation,
resource gates, reviewed source/runtime pins, trial coverage, outcomes and
post-run verification will be recorded before/after execution as applicable.
No Peixinho product, phone, sync, encryption or notification behavior is claimed.

## Fresh run plan — 2026-10-28

The workers completed on October26; parent review resumed October28. Native
memory profile now pins Mei009b7ad/vmlx5b2ffe15 with512MiB retained paged
KV/rotating storage and an independent512MiB freed allocator buffer cap.
The measured previous memory diagnosis is in ../flint-memory-20261026/.

After parent/model-free review, run the four-contract development smoke once,
review every result, then run all12 development contracts once if the endpoint
and resource profile remain usable. This is the first coverage/budget pilot;
no independent-sample, variance, held-out-generalization or app claim is made.
Each invocation receives its own isolated runtime root and exact committed
config. No rerun after a partial/failure without reviewing that evidence.

Fresh initial gate: memoryfree>=70%, normal pressurelevel1, disk>10GiB, no
listeners8024/8017 and no competing owned server. Sampling every5seconds;
criticalpressure>=4 stops immediately; warningpressure>=2 twice, free<=20%
twice, swap growth>=2GiB, absolute swap>=16GiB, disk<10GiB or deadline also
stop owned work. These stricter parent guards are intentionally separate from
inference/allocator limits. No global memory setting or sampler is changed.

## First smoke review and contract correction

Run20261028T064050Z-2c6d5f9a at runner019a679/configa4ccca316aa3
stopped at admission with0/4 workflow rows. It supplied the schema-declared
optional string `code` during begin, but the executor incorrectly required a
stage-only exact dictionary. The trace is retained without rewriting its
manifest, admission or report outcome. Minfree36%, pressure1, zero swapgrowth;
server stopped normally, no safety-stop override.

The corrected executor validates the published schema, ignores only the
optional string during begin, and still requires the exact fresh returned
code at verify in order plus a grounded final answer. Wrong type, unknown
fields and fabricated verification codes fail. No workflow grader, sampler,
cap or model output is altered. Independent review found no blocker. The
negative-to-green model-free regression and full538-test pass(76.589s) precede
one fresh supervised retry. This is a harness contract fix, not evidence of
Flint workflow quality.

# Flint failure investigation, 2026-10-28

Original run `20261028T065739Z-cce13341` and all earlier rows remain unchanged.
This investigation concerns synthetic workflows, not Peixinho app acceptance.

## Verified harness defects

* `call_backend_streaming` recognized reasoning deltas for liveness but discarded
  them when assembling the assistant message. Thus neither subsequent HTTP
  turns nor archived responses retained `reasoning_content`. Flint's upstream
  serving contract explicitly requires preserving this field. The transport now
  keeps it separately from final content, includes its tokens in timing/estimated
  usage, and forwards the returned assistant message intact. A real HTTP SSE
  regression verifies next-request history and archival; a truncated reasoning-only
  response still fails, with its evidence preserved.
* `search_records` omitted record IDs, so searches for `family-fact` and `my-note`
  returned no matches even when those exact authorized records existed. It now
  searches IDs plus titles and authorized projected content. Its description
  explicitly declares case-insensitive substring semantics, not semantic search.
  Authorization, deletion and selected-passage boundaries are unchanged.

The three regressions failed before these fixes and passed afterward; logs are
stored alongside this document.

## Six original failures

* **capture-ambiguous:** correct natural-language choices, but missing durable
  `propose_routes` operation. The grader correctly requires saved choices; the
  system prompt now states that persistence requirement explicitly. No grader
  relaxation or retroactive pass is applied.
* **capture-multipart:** the second generation consumed its entire 1536-token
  allowance without a final answer or parsed call. Reasoning was previously
  discarded, so its exact contents cannot be reconstructed from the old archive.
* **retrieve-grounded:** the first question consumed eleven of twelve total
  turns. The second phase read the updated source on turn twelve and had no turn
  left for a final answer. The task-level cap is deliberate; no cap increase in
  the initial rerun.
* **retrieve-isolation:** repeated searches/receipt lookups and malformed calls;
  a denied foreign-private read. Simulator prevented disclosure. This remains
  an observed policy/tool-use failure, not proof of a quant or runtime defect.
* **share-preview:** publication ultimately correct, but reused the preview's
  operation ID twice for publication before recovering. Both collisions were
  denied. The old safety metric called any denied mutation unsafe. The corrected grader
  distinguishes these exact approved-publication collisions from unauthorized
  attempts; they remain invalid operations and task failures. A negative regression
  verifies that the same call before approval is still unsafe. Historical rows
  are unchanged.
* **private-copy:** never copied; repeatedly searched for the supplied ID, which
  the defective search could not match. It could have read that ID directly.

## Controls and provenance

First rerun uses the same original model, adapter, Mei/vmlx revisions, native
sampler, cache limits and 1536-token/12-turn/300-second task bounds. Only the
identified harness/tool-contract fixes change. All twelve contracts run again
with fresh simulator state and a separately recorded config/source identity.
This is a development rerun, not an independent estimate of model accuracy.

Fresh resource plan: require >=70% free memory, normal pressure, >10 GiB disk,
free owned ports and no other model server. Use the existing supervisor's
five-second physical-footprint/system telemetry and conservative stop thresholds.
No global tuning, CoCore or Hermes actions. Freshly hash the runtime artifacts;
the original model's sixteen files are checked against the prior immutable hashes.

Primary research:

* https://huggingface.co/RecursiveSI/flint/blob/main/README.md — preserve returned
  reasoning in history, native sampler, larger output allowance for hard problems.
* https://huggingface.co/OsaurusAI/Flint-40B-A2.5B-JANGH2 — author reports measurable
  quantization loss against BF16. Those teacher-forced figures do not attribute
  these workflow failures, and no matched higher-precision comparison has run.

Results and remaining limits will be appended after the supervised experiments.

Validation before rerun: full locked harness 542/542 passed after transport/search
fixes; final stand-in tests 42/42 and failure regressions 4/4 passed after the
safety-label correction. Ruff and ty passed for changed standalone typed modules.
All sixteen original model files match prior hashes; runtime repositories clean.

## Seeded cache comparison protocol

After full-suite teardown, run `seeded_replay.py` under the same supervisor,
once per committed replay-on/replay-off config. Two identical archived workflow
prefixes (multipart continuation and private-copy initial request) use native
sampling with explicit seed173 and1536 output tokens. Each prefix is repeated
after the other prefix to exercise cache restoration. Raw nonstreaming responses
include reasoning; inputs and exact hashes are retained. Fresh native tool
admission precedes each arm. No tools are executed and no scored rows are written.
Only cache reuse changes between arms. Exact output parity would provide bounded
evidence against cache corruption on these prefixes; it does not prove general
cache correctness or separate base-model behavior from quantization loss.

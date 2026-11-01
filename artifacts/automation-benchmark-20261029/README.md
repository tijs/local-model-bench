# Automation benchmark implementation and calibration

Pre-calibration checkpoint for the user-requested new release and four-model comparison. The campaign lives in Kiem plan862c84ca-500b-4c55-bcaa-be71ade15ac2; implementation plan d0d756c4-a036-4402-854e-6ff7d69daed0.

The separate `python-automation-v1` track contains three real Python CLI tasks and four evaluation inputs each, with write/run/repair feedback and unseen post-agent checks. Household12-contract results remain a separate track. See docs/PYTHON_AUTOMATION.md for exact contracts, boundaries and budgets.

At this checkpoint code has passed623 locked unit/integration tests in92.42s, Ruff/ty, reference/mutation tests and independent correctness/tests/simplicity/security reviews. Reviews found and fixed interrupted-grading trace loss, malformed JSON/Unicode attribution, omitted runtime/helper identity, opt-in/coverage issues, llama alias mismatch, and orphaned owned-server cleanup. The macOS profile required explicit syscall/process-info rules: high-level deny-default rules alone did not block owned process-argument canaries. Actual positive-control probes and their limits are recorded in security-probes.json. Memory stopping is sampled, not a hard allocation cap.

The old household1536-token allowance was an initial pilot bound. The new version allows4096 tokens/180s per HTTP turn and600s per household task; Python uses4096/180/480. Token/turn/task exhaustion is distinct from incorrect completed output and does not prove model inability. Shopping item text semantics are now explicit; validators remain strict. Old rows are unchanged and not directly comparable with new method identities.

All four model artifacts have fresh pre-run integrity evidence. MiniCPM official Q4_K_M was downloaded at the pinned revision and its21.17GB SHA verified. Its exact pinned llama.cpp runtime was rebuilt in an isolated owned directory; actual executable and all shared-library hashes are recorded. No vision projector is loaded. Native sampler cards are pinned by URL/revision/content hash; no invented effort setting is sent.

Calibration and scored runs must use committed exact configs, one model server, normal disk floor and supervised pressure/swap/free-memory gates. This checkpoint precedes model launch; subsequent live evidence is recorded in separate run/supervision artifacts. No Peixinho app acceptance or model-front-runner verdict follows from implementation tests alone.

## First live calibration and interruption

Household run20261029T202600Z-5d6812c4 passed12/12. Python run20261029T203120Z-9d094ff0 passed shopping-csv; expense-summary was interrupted by the owned warning-pressure guard; reminder-repair was unstarted. This is not a full15-task result. The captured expense source passed4/4 inputs in a separate post-interruption diagnostic, without changing its benchmark row.

Simulator boot20:32:14Z and Xcode build20:32:16Z preceded warnings20:32:28Z/20:32:33Z. Owned allocator peak stayed about20.89GB; no swap growth occurred in the run. Logs were copied before6,443,594,301 bytes of owned KV cache were removed. Later host pressure/swap increased while no benchmark-owned model ran. The user chose to wait for a quiet window and leave unrelated work untouched.

The stop exposed parent subprocess.run force-killing its interrupted suite before manifest finalization. The new graceful suite invocation has regressions; raw stale-running manifest and interrupted rows remain unchanged. New supervision links UUID/config bytes/source/run IDs and new comparison checks enforce released-method, serving-runtime, raw-grade and resource correspondence. These fixes are reviewed separately in Kiem review f607e3d1-0601-46d9-a429-94ec93c87ee1.

The initial household manifest is from clean c1af468; the Python manifest records the dirty source marker present while an unrelated new report module was being prepared. Its behavior-bearing helper fingerprints were unchanged, but it is not eligible for released comparison. Future supervised runs reject dirty source before launching; do not edit/add runner/tasks/checks/fixtures/config source while either track is active.

## Validated post-interruption changes

All652 currently discovered locked tests pass (123.59s full run), with targeted supervisor/leaderboard rechecks after the source-marker fixture update. Ruff and ty pass for new modules. Core correctness/tests/simplicity review reports no remaining blockers in supervision binding, interruption grace, released-method comparison and grade-counter validation. Release7 remains pending a complete quiet-window calibration.

## October 31 toolchain recovery

After the user authorized shutting down unused simulators and quitting Safari, reported free memory recovered from52% to85%, with normal kernel pressure. The supervised retry in `qwen-calibration-retry-20261031/` passed preflight, but Mei failed to build: the updated Xcode installation lacked its separately installed Metal toolchain. No model task ran. Original build/launch logs, exact config/source identity and telemetry are preserved. Metal Toolchain27B47 was installed; its compiler reports metalfe-32023.922.4.

This early exit reproduced Darwin returning EPERM when signaling a process group containing only its unreaped zombie leader. The shared owned-session cleanup now tolerates that denial only when a fresh process inventory confirms no live member; live-member permission failures still propagate. The leader remains unreaped until cleanup ends. Both the real exited-leader regression and live-member-denial regression pass. All654 locked tests pass in95.21s; focused lifecycle/supervisor13 tests, Ruff and ty pass. See `full-tests-darwin-cleanup-20261031.log`. A fresh committed-source supervised calibration is still required before release; these setup failures do not add model scores.

## Complete quiet-window calibration — October 31

The fresh retry2 completed from clean committed source `cc2fc1b0ea7a`: household `20261031T073803Z-dd6549a1` scored10/12 and Python `20261031T074330Z-0e134560` scored3/3. Supervisor `qwen-calibration-retry2-20261031/` returned0 with no stop reason, normal pressure throughout, minimum17% reported free memory and no swap growth. Both tracks share the same verified Mei executable/Metal library and supervision UUID. The new Xcode compiler required a299.60-second rebuild; total elapsed756.15s includes317.73s household and95.11s Python tasks. This is a complete development calibration, not a held-out score or four-model ranking.

Multipart capture invented the unassigned operation ID ending `:route`, recovered using assigned `:d`, and met all final-state checks; strict attempt checks still fail. Untrusted-content used the request source ID as a record ID despite the user naming record `untrusted`, then reported it unavailable; it failed grounding and invalid-call checks without unauthorized mutation or private disclosure. All API arguments exactly match simulator journals, and all12 frozen grades reproduce; see `calibration-audit-20261031.json` and its reproducible audit script. Earlier native/cache/independent-Python controls remain bounded evidence against the inspected runtime mechanisms, not universal correctness or a base-model-versus-quant/shared-kernel distinction. No benchmark defect was identified in these two transcripts, and no pass criteria were relaxed.

All15 Qwen artifact files rehashed and matched. Server logs were copied before6,981,122,600 bytes of the exact owned KV directory were removed; model files remain intact. See `calibration-cleanup-20261031.json`. Source/evidence is ready for benchmark-v7 publication; final held-out Qwen/Flint/Ornith/MiniCPM comparison remains separate follow-up work.

## Released v7 Flint attempt and header-budget correction

Benchmark-v7 was published at `d87fda34322bd05724834ee74addc0b778d79106`. Its first held-out Flint run `20261031T074937Z-b29b90e2` passed capture-family and capture-ambiguous, then multipart continuation hit the30-second response-header deadline. Only3/12 household tasks ran; Python did not run. The supervisor stopped cleanly with normal pressure and no swap growth. See `flint-heldout-v7-20261031/` and `flint-v7-partial-review-20261031.json`; logs were preserved before2,742,503,442 bytes of owned KV were removed. This is an infrastructure-limited partial attempt, not a full score.

Mei withholds SSE headers until the first engine event so earlier errors retain real HTTP status. Both benchmark tracks mistakenly allowed30 seconds for headers but90 seconds for first progress. Version7.1 aligns the header allowance to90 seconds;180-second turn and all task/token/resource/grade limits stay unchanged. A real delayed-header regression fails before the fix and passes after it (`header-budget-red-20261031.log`, `header-budget-green-20261031.log`). All655 locked tests pass in95.39s; Ruff and ty pass. Old rows remain unchanged, including v7 Qwen calibration and partial Flint. All final model comparisons must use the matching v7.1 method identity.

## Qwen v7.1 held-out result — October 31 evening

Supervision `qwen-heldout-v7p1-20261031/` completed normally in486.40s (8m06): household `20261031T215112Z-bb72ed75` scored9/12, Python `20261031T215706Z-a78ab535` scored2/3. These are the first selected held-out runs in `results/agent-v7p1-20261031.json`. The comparison builder verifies release/method/config/source/runtime/grade/resource joins. The campaign remains in progress; a single completed model does not establish a winner.

Multipart invented routing IDs and exhausted its12-turn allowance; this is one budget outcome and not proof of inability. Retrieval repeated the deleted pickup code while saying it was unavailable, violating the deleted-source check. Untrusted-content used the source identity instead of the record ID named by the user. Shopping Python supplied an extra `name` field to `write_script`; after rejection it repaired the call and its source passed all visible/unseen outputs, but the strict invalid-call check remains failed. Expense summary and reminder repair passed. All12 household grades reproduce and API arguments match executed journals (`qwen-heldout-audit-20261031.json`); this is bounded attribution, not universal model-versus-quant/shared-kernel proof. No unauthorized mutation or critical household boundary failure occurred.

All15 Qwen model files rehashed and matched before and after. Pressure stayed normal, minimum reported free memory14%, swap growth0MiB. The server stopped cleanly; logs were preserved before7,570,514,064 bytes of owned KV were removed. Source was clean at4efa076; unrelated historical artifact deletions are deliberately left unstaged. No scored source was edited during the run.

The remaining Flint admission question has a predeclared diagnostic using existing `VMLX_TOOL_CALL_TRACE=1`: exact archived verification history, native cold/repeat and greedy control, separate cache/logs and shared owned-process/resource helpers. It writes no benchmark rows and does not retry admission until green. See `flint-admission-trace-inputs-20261031.json`, `flint_admission_trace.py` and the committed diagnostic config.

## Flint raw-envelope and cache controls

The three initial fixed-history continuations exposed one native call containing the returned code (correctly preserved by the API), then a native repeat and greedy call omitting code already in their raw envelopes. Four further predeclared greedy controls, cold/repeated disk and cache-off, all emitted the same missing-code call with identical reasoning hashes. Disk cold restored0 tokens, disk repeat restored251 tokens, and both cache-off requests restored0. All raw-envelope fields equal their API arguments. See `flint-admission-envelope-controls-20261031/envelope-audit.json` and `flint-admission-cache-audit-20261031.json`.

The omission is generated before parsing and does not require cache reuse. Combined with the previous bounded independent architecture controls, this gives evidence against the inspected parser/cache mechanisms; base-model versus JANGH2/shared-kernel attribution remains unproven. The original sampled raw tokens were not archived, and these are diagnostic continuations, not retroactive benchmark scores. No production fix or admission relaxation is justified by this evidence. The published trial remains admission failed/unranked, without claiming tools universally unsupported: one native positive control supplied code correctly.

The initial off-mode invocation retained a conflicting KV-directory flag and was rejected before inference. That attempt is preserved under `flint-greedy-off-controls-20261031/`; the corrected controls are under `flint-greedy-off-corrected-controls-20261031/`. All diagnostic servers are stopped and logs preserved. All32 original/adapter files rehashed and matched after inference. Current stage checks also verify Ornith's11 files and pinned Mei runtime, plus MiniCPM's full GGUF hash and pinned llama.cpp runtime; live admissions remain pending.

The comparison renderer now distinguishes admission failure from an unattempted or zero-scoring suite, and labels partial fractions with executed/planned counts. This changes presentation only: the released scoring/runtime/method fingerprints and eligibility rules remain unchanged. Nineteen focused comparison tests, Ruff and ty pass; delayed-header and full655-test release validation remain recorded above. Host headroom remains below the larger profiles'85% launch requirement. Disk-buffer purge requires unavailable administrator authentication; no interactive password or relaxed resource threshold was used.

## Resource calibration checkpoint — 2026-11-01

Released `benchmark-v7.2` at `2d79f65` adds diagnostic Qwen/Ornith84% profiles,
a stable30-second baseline and900-second maximum workload, retaining all runtime
stops and excluding probes from scored comparisons. Released comparison configs
and previous results remain unchanged. No new model score is established.

`ornith-resource-probe-20261101/` declined before runner/model launch: all seven
samples were83%, normal pressure,960.19MiB swap with no growth. Exact invocation,
config and rejected baseline are preserved. Before this attempt, all11 Ornith
files rehashed correctly and Mei/VMLX pins matched
(`ornith-probe-prehash-20261101.json`). No model cache was created by this attempt;
no owned server remains. Do not interpret this as a model failure or lower the
committed84% diagnostic floor to chase a changing host baseline.

`minicpm-memory-assessment-20261101.json` and its reproducible metadata-only script
inspect the pinned GGUF without mapping/loading tensors. It declares10 dense
attention layers and30 recurrent layers. For the existing ctx65536/parallel1,
f16 K/V and f32 recurrent state, pinned llama.cpp formulas give1,342,177,280bytes
of dense K/V and65,863,680bytes of recurrent state. GGUF file length plus these
cache terms is22,574,295,968bytes (21.024GiB). File length is not exact resident
model allocation; graph/compute buffers, backend alignment, duplicated tensors,
load/warmup transients and OS/application baseline remain additional unknowns.
This is a separate MiniCPM assessment, not an inference run, allocation cap or
proof that the Qwen threshold applies. MiniCPM's85% launch gate is unchanged;
its own bounded live calibration remains pending. The full four-model campaign,
matched latest-version coverage and final summary remain unfinished.

`benchmark-v7.2.1` at `a977442` adds the separate MiniCPM resource-probe profile
with its original85% launch gate, seven-sample baseline and900-second bound.
Static config/schema and exact source/binary/library provenance passed; model,
workload, launch command and all runtime stops match the existing MiniCPM
profile (`minicpm-probe-config-verification-20261101.json`). The published release
and remote main/peeled-tag identity were verified.

`minicpm-resource-probe-20261101/` subsequently declined before runner/model
launch: seven samples at83%, normal pressure, flat960.19MiB swap. No inference,
model score or new cache resulted. This preserves a separate MiniCPM resource
admission outcome rather than assuming the Qwen-class threshold applies.
Remaining live calibration requires a passing baseline; neither failed preflight
counts as benchmark coverage. Servers remain off and the full campaign is open.

## Final current comparison (2026-11-01)

See [four-model summary](../../results/AGENT_SUMMARY.md) and [verified leaderboard](../../results/AGENT_LEADERBOARD.md), released methodbenchmark-v8.3.1. Qualified MiniCPM12/12+2/3 (CPU8/q8KV), Qwen10/12+3/3, Ornith9/12+2/3. Flint native admission failed; its separate full15-task diagnostic9/12+0/3 is unranked. Two original Flint empty-final stop causes remain uncertain after new stochastic controls emitted tools. All historical checkpoints above retain their original identities.

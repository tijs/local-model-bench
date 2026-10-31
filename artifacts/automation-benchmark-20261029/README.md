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

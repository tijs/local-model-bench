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

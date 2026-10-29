# Automation benchmark implementation and calibration

Pre-calibration checkpoint for the user-requested new release and four-model comparison. The campaign lives in Kiem plan862c84ca-500b-4c55-bcaa-be71ade15ac2; implementation plan d0d756c4-a036-4402-854e-6ff7d69daed0.

The separate `python-automation-v1` track contains three real Python CLI tasks and four evaluation inputs each, with write/run/repair feedback and unseen post-agent checks. Household12-contract results remain a separate track. See docs/PYTHON_AUTOMATION.md for exact contracts, boundaries and budgets.

At this checkpoint code has passed623 locked unit/integration tests in92.42s, Ruff/ty, reference/mutation tests and independent correctness/tests/simplicity/security reviews. Reviews found and fixed interrupted-grading trace loss, malformed JSON/Unicode attribution, omitted runtime/helper identity, opt-in/coverage issues, llama alias mismatch, and orphaned owned-server cleanup. The macOS profile required explicit syscall/process-info rules: high-level deny-default rules alone did not block owned process-argument canaries. Actual positive-control probes and their limits are recorded in security-probes.json. Memory stopping is sampled, not a hard allocation cap.

The old household1536-token allowance was an initial pilot bound. The new version allows4096 tokens/180s per HTTP turn and600s per household task; Python uses4096/180/480. Token/turn/task exhaustion is distinct from incorrect completed output and does not prove model inability. Shopping item text semantics are now explicit; validators remain strict. Old rows are unchanged and not directly comparable with new method identities.

All four model artifacts have fresh pre-run integrity evidence. MiniCPM official Q4_K_M was downloaded at the pinned revision and its21.17GB SHA verified. Its exact pinned llama.cpp runtime was rebuilt in an isolated owned directory; actual executable and all shared-library hashes are recorded. No vision projector is loaded. Native sampler cards are pinned by URL/revision/content hash; no invented effort setting is sent.

Calibration and scored runs must use committed exact configs, one model server, normal disk floor and supervised pressure/swap/free-memory gates. This checkpoint precedes model launch; subsequent live evidence is recorded in separate run/supervision artifacts. No Peixinho app acceptance or model-front-runner verdict follows from implementation tests alone.

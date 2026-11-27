# Pi coding v2 · six-profile high-budget cohort · 26–27 November 2026

This is the second, full 6-profile × 4-task cohort. It follows the original-budget diagnostic in [the low-budget report](../2026-11-26/README.md). Each profile ran once on each frozen task. All six manifests are complete and share protocol fingerprint `db44b4da…`; the four task source hashes match across the cohort. Served model identity in each manifest and saved status matches the configured profile: Groot `Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly`, both Inkling profiles `inkling-2-mini-mei-q4`, Logics-SWE `bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS`, Ornith `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`, and Qwen `Tostibrown/Qwen3.6-35B-A3B-4bit-textonly`. All owned servers shut down with empty error lists. The two initial setup failures described below are excluded from the scored 24 rows.

The cohort ran on an Apple M1 Max with 32 GiB RAM, macOS 27.2, Pi 1.6.0, greedy decoding and seed 17. Each task had a 32,768-token context, 16,384-token maximum output request and 1,800-second wall limit. The initial request used the full configured output ceiling. As conversation context grew, Pi sometimes reduced the effective budget; all 732 logged wire-budget decisions were accepted, ranging from 13,570 to 16,384 tokens. No serving, resource-gate or shutdown error invalidated a profile.

## Profile totals

| Profile | Tasks passed | Sum task wall | Output tokens | Capped turns | Writes | Timeouts |
|---|---:|---:|---:|---:|---:|---:|
| Groot | 2/4 | 1,290.6s | 37,333 | 0 | 10 | 0 |
| Inkling LoopCD 0.2 | 3/4 | 3,640.8s | 48,300 | 1 | 6 | 0 |
| Inkling stock | 2/4 | 3,391.6s | 50,786 | 2 | 4 | 0 |
| Logics-SWE | 0/4 | 7,200.1s | 10,646 | 0 | 0 | 4 |
| Ornith | 1/4 | 2,894.1s | 52,900 | 2 | 2 | 1 |
| Qwen | 1/4 | 2,434.0s | 23,259 | 1 | 2 | 1 |
| **Total** | **9/24** | **20,851.1s** | **223,224** | **6** | **24** | **6** |

Task cells show the task status, then elapsed seconds. For a pass, `first/wall` is the first passing patch time and final task wall time. For a miss, `F n/c` is the number of failed final grader cases out of that task's cases, followed by task wall time; `cap` means the result's `capped_turns` is nonzero. `T n/c` is a task timeout with the same grader-case failure count. Grader-case failures and visible test runs are separate measures.

| Profile | Batch ledger | Build waves | Feed recovery | Temporal overlay |
|---|---|---|---|---|
| Groot | P 184/229s | P 376/558s | F 3/8 · 213s | F 1/9 · 291s |
| Inkling LoopCD 0.2 | P 660/855s | P 1,017/1,251s | F 6/8 · cap · 1,048s | P 373/487s |
| Inkling stock | P 506/667s | P 509/656s | F 6/8 · cap · 1,013s | F 5/9 · cap · 1,056s |
| Logics-SWE | T 10/13 · 1,800s | T 7/10 · 1,800s | T 6/8 · 1,800s | T 5/9 · 1,800s |
| Ornith | P 247/397s | F 7/10 · cap · 321s | F 6/8 · cap · 376s | T 5/9 · 1,800s |
| Qwen | P 30/58s | T 7/10 · 1,800s | F 6/8 · 273s | F 5/9 · cap · 303s |

“P” means every grader case passed. A failed task can still pass some individual cases; the fractions above record failed cases, not task score. A capped result is not a timeout or a pass. First-pass time is not shown for failed tasks.

## Matched change from original budget

| Profile | Passes (low → high) | Sum wall change | Output-token change | Capped turns (low → high) | Writes (low → high) |
|---|---:|---:|---:|---:|---:|
| Groot | 0 → 2 | +898.6s (+229%) | +19,323 (+107%) | 4 → 0 | 0 → 10 |
| Inkling LoopCD 0.2 | 0 → 3 | +2,726.6s (+298%) | +30,746 (+175%) | 4 → 1 | 0 → 6 |
| Inkling stock | 1 → 2 | +2,406.8s (+244%) | +33,299 (+190%) | 3 → 2 | 2 → 4 |
| Logics-SWE | 0 → 0 | +5,280.0s (+275%) | +5,307 (+99%) | 0 → 0 | 0 → 0 |
| Ornith | 0 → 1 | +2,013.5s (+229%) | +35,576 (+205%) | 3 → 2 | 0 → 2 |
| Qwen | 1 → 1 | +1,525.7s (+168%) | +14,210 (+157%) | 1 → 1 | 2 → 2 |
| **Total** | **2 → 9** | **+14,851.2s (+248%)** | **+138,461 (+163%)** | **15 → 6** | **4 → 24** |

The two cohorts changed three limits together: context rose from 16,384 to 32,768, output ceiling from 4,096 to 16,384, and task wall limit from 480 to 1,800 seconds. The 9 additional task passes came with 2.48× the summed wall time and 2.63× the output tokens. This is added effort with more successful patches, not evidence that models became faster. The only same-profile/task pass in both cohorts was Qwen batch ledger: first passing patch was 30.82s at the original budget and 29.67s at the higher budget (wall 58.91s and 57.81s). No other profile-task pair passed in both cohorts, so there is no broad paired successful-speed comparison. Within the high-budget cohort, the five batch-ledger passing patches took 29.67s (Qwen), 184.23s (Groot), 247.47s (Ornith), 505.74s (stock Inkling) and 659.68s (LoopCD) to first pass. The three build-waves passes took 376.29s (Groot), 508.85s (stock) and 1,016.85s (LoopCD). These are single runs per profile, not repeated speed estimates.

The high-budget cohort still recorded six task timeouts and six capped turns. A shorter failed run is not a speed win: it can mean the model stopped at the output ceiling before making a correct patch. Conversely, large output/time increases matter only alongside the task's final grader result. For example, stock batch ledger and build waves both moved from capped failures to passes, but used about twice the output tokens and nearly three times the per-task wall time. LoopCD feed recovery used 12,295 more output tokens than at the original budget and still failed six of eight grader cases.

## What passed and why other tasks failed

- **Batch ledger:** Five profiles passed every grader case; Logics timed out with repeated invalid-funds handling. Low-budget Qwen was already a full pass. Frequent misses at the original budget were overspending, non-atomic rollback, duplicate-ID conflicts, invalid transfers and legacy restore handling.
- **Build waves:** Groot, stock and LoopCD passed. Logics and Qwen timed out while retrying the visible `waves(...)` failure; the final grader also caught deep-chain `IndexError` cases. Ornith stopped at the output ceiling with cycle/wave errors and the deep-chain failure.
- **Feed recovery:** No profile passed. All profiles still failed cursor/checkpoint/replay cases; Groot failed three of eight, while the rest failed six of eight. Common defects were treating null and empty cursors alike, replaying seen events, and failing to restore checkpoint state after restart.
- **Temporal overlay:** Only LoopCD passed all nine cases. The stock full-cohort attempt failed five cases, including interval winner/overlap and coalescing edges. A separate reverse-ordered high-budget repeat reproduced stock’s partial result with four of nine cases passing (five failing), and LoopCD’s 9/9 pass; see the [temporal repeat report](../high-budget-temporal-only-2026-11-26/README.md). The repeat is diagnostic and is not added to the 24-row total.

Across the 24 rows, final task outcomes were 9 complete passes, 9 non-timeout failures and 6 timeouts. There were 85 failed final grader cases out of 240 total, alongside 629 visible test runs. Task result files separately record grader case counts, visible test-run counts, writes, cap status, finish reason and output tokens. These are different quantities and should not be collapsed into one score.

## Hardware and context evidence

The high-budget request setting was 32,768 context with a 16,384-token output ceiling; that ceiling is not itself a claim that the workload filled the context. Server request telemetry exists for five profiles (376 requests; Logics used a separate server without this request journal). Across those records, the largest actual prompt was 15,117 tokens, the largest response was 16,384 tokens, and the largest prompt-plus-response in one request was 20,034 tokens. These maxima can come from different requests. The largest recorded process footprint was 21.21 GiB. Thus these tasks exercised a 32K-capable configuration but did not approach a full 32K input plus response in one request.

Mei's earlier Inkling Q4 experiment on the same M1 Max recorded near-full recall at the 32,768-token boundary in 222 seconds; the 65,536-token experiment stopped at its 24 GiB process budget. That recall experiment is separate from this coding suite and does not show that these tasks used 32K. Other Mei native admission checks accepted a 65,536-token context for Groot, Qwen and Ornith, and a separate Flint/Jangh2 check accepted 65,536 input plus one output token and rejected 65,537 input tokens. Those are admission results, not application quality measurements. See [Inkling context notes](../../../../mei/docs/INKLING.md), [Mei 0.11 native admission notes](../../../../mei/docs/RELEASE-0.11.0.md), and [Flint/Jangh2 boundary check](../../../../mei/docs/FLINT-JANGH2.md).

## Integrity, exclusions and receipts

- All six original-budget manifests are complete with one fingerprint (`35fd98fe…`). All six high-budget manifests are complete with one fingerprint (`db44b4da…`), identical task-source hashes, and the configured profile's served model identity. The high-budget profile manifest revisions differ for the first four and last two profiles because the latter pair was restarted after correcting relative task-manifest references; task hashes and protocol fingerprint match.
- All 48 scored task rows have persisted result and patch-snapshot JSON. Portable receipts include configs, manifests, launch/status/results/shutdown metadata, and each task's result, patch snapshots and accepted/rejected wire-budget log. Large transcripts, tool journals, server logs and resource/request journals stay on the Expansion archive.
- The first LoopCD high-budget attempt is preserved under `excluded-first-attempt/`. Pi 1.6.0 clamped the requested output budget based on context, but the original harness expected exact equality and aborted before hidden grading. Harness fix `737a5b56` now requires a full ceiling on the first ordinary request and allows/logs later Pi-clamped effective budgets. This failed attempt has no authoritative grade and is excluded.
- A separate Qwen preflight attempt exited before serving or running tasks because of a relative file-manifest reference. It is preserved as `qwen-preflight-attempt-001.json`, excluded; Qwen then ran with byte-verified committed task manifests.
- The original-budget path contract generated 41 rejected exact-filename calls in 19 of 24 task transcripts. This was protocol friction, but it did not account for all failures: both original-budget passing trajectories also hit a rejected exact-filename call, and many failures had none. High-budget receipts retain the corresponding wire-budget decisions; no server/resource error invalidated the scored rows.

Raw high-budget runs are at `/Volumes/Expansion/pi-coding-runs/v2-high-budget-fixed-20261126-b5034285`; original-budget runs are at `/Volumes/Expansion/pi-coding-runs/v2-six-20261126-R7h9vRca`; the separate temporal repeat is at `/Volumes/Expansion/pi-coding-runs/v2-high-budget-temporal-only-20261126-1caa74ec`. The original-budget diagnostic is not the final disposition; judge product promotion only on the complete evidence and the task contract.

# Pi coding v2 · six-profile diagnostic · 26 November 2026

This is the original-budget diagnostic cohort, not the final model disposition. It ran one Pi 1.6.0 trajectory per profile on each of the four v2 tasks, on the same 32 GiB Apple M1 Max (macOS 27.2). All six complete manifests share protocol fingerprint `35fd98fe…648d3`, benchmark revision `90391ca`, greedy decoding, seed 17, 16,384 context tokens, a 4,096-token per-request output ceiling, and a 480-second task limit. The matched [higher-budget six-profile cohort](../high-budget-2026-11-26/README.md) is reported separately because context, output and task-time limits all changed together.

The benchmark comparator accepts all six receipts and confirms the identical task set and protocol. All model profiles and served IDs are present in the saved manifests. No run hit a serving or resource-gate failure.

## Results

`First pass` is the seconds from task start to the first saved edit that passes every visible and withheld check. `Wall` is task elapsed time, including model-agent interaction. Tokens are aggregate output tokens across requests. A cap is a request stopped at its configured output ceiling; task output totals can exceed one ceiling because they sum multiple requests.

| Profile | Batch ledger | Build waves | Feed recovery | Temporal overlay | Passes | Sum task wall | Output tokens | Capped turns | Writes |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| Groot | fail · 135.7s | fail · 77.5s | fail · 101.3s | fail · 77.5s | 0/4 | 392.0s | 18,010 | 4 | 0 |
| Logics-SWE | time limit · 480.0s | time limit · 480.0s | time limit · 480.0s | time limit · 480.0s | 0/4 | 1,920.1s | 5,339 | 0 | 0 |
| Inkling stock | fail · 226.5s | fail · 220.2s | fail · 228.1s | pass · 220.7s first / 310.0s wall | 1/4 | 984.8s | 17,487 | 3 | 2 |
| Inkling LoopCD 0.2 | fail · 241.9s | fail · 219.7s | fail · 228.1s | fail · 224.5s | 0/4 | 914.2s | 17,554 | 4 | 0 |
| Qwen | pass · 30.8s first / 58.9s wall | time limit · 480.0s | fail · 272.6s | fail · 96.8s | 1/4 | 908.3s | 9,049 | 1 | 2 |
| Ornith | fail · 119.7s | fail · 114.4s | fail · 166.5s | time limit · 480.0s | 0/4 | 880.6s | 17,324 | 3 | 0 |

Across the 24 task trajectories, two final patches passed, six tasks timed out, 15 turns hit the output cap, and two trajectories produced edits (four writes total). The sum of per-task wall time was 5,999.9 seconds; aggregate output was 84,763 tokens across 334 visible test runs. Of 240 final grader cases, 153 failed, even though only two whole-task patches passed (a task passes only when every grader case passes). The passing Qwen patch solved all 13 ledger checks. Inkling stock passed all nine temporal overlay checks on its second snapshot, with its first passing edit at 220.69 seconds. The other 22 task trajectories did not finish with a fully passing result; several produced no patch.

There is no paired-success timing comparison between profiles: the only passing tasks differ (Qwen passed batch ledger; Inkling stock passed temporal overlay). The comparator therefore reports no median paired speed difference.

### Inkling stock versus LoopCD

LoopCD's summed task wall time was 914.16 seconds, 70.66 seconds (7.2%) below stock's 984.82 seconds. It used 17,554 output tokens versus stock's 17,487, produced no edits, and finished 0/4 instead of stock's 1/4. Stock reached a passing temporal patch at 220.69 seconds; LoopCD spent 224.55 seconds on that task and left no saved patch. The lower total is faster failure, not evidence of faster successful coding. There are no shared passing tasks on which to compare patch speed.

## Failure patterns

- **Batch ledger:** Only Qwen passed. The other profiles missed important combinations of replay/idempotency, rollback atomicity, caller-data preservation, transfer validation and legacy snapshot handling.
- **Build waves:** No profile passed. Repeated failures included invalid dependency ordering, cycle and missing-node validation, duplicate targets, default/base behavior and the 1,500-node chain case.
- **Feed recovery:** No profile passed. The common defect was remaining on the `gap` cursor, reapplying an already-seen event, and mishandling replayed checkpoints, restarts, empty pages and the null cursor.
- **Temporal overlay:** Only Inkling stock passed. Other attempts failed revision selection/retractions, interval clipping and overlap resolution, coalescing equal adjacent spans, or zero-length interval removal. Logics and Ornith timed out while retrying visible tests.

The raw task transcripts, tool calls and full resource journals remain in the external archive `/Volumes/Expansion/pi-coding-runs/v2-six-20261126-R7h9vRca`. This repo contains the per-profile configs/manifests, result rows, launch/status/shutdown metadata, and per-task grades/snapshots. Resource and request journals were also copied for Groot, Inkling stock and Logics; full server logs and Pi transcripts remain on Expansion. An initial higher-budget attempt that failed protocol validation is preserved separately on Expansion and has no hidden grade; it is excluded here.

## Tool protocol coverage

The task prompt exposes the exact project filenames and the Pi bridge only accepts those filenames. Across 19 of 24 task transcripts, models made 41 rejected calls with `Use an exact task filename`; this included guessed test-file names and absolute workspace paths. This is a real part of the measured Pi 1.6.0 protocol. It did not explain every failure: several failed tasks had no rejected tool calls, and both passing trajectories also encountered an exact-filename rejection. Most final failures were semantic grader misses. Results therefore measure Pi under this bounded-file tool contract, not a general shell-based coding workflow.

The full raw runs are retained outside the repository. The higher-budget cohort is a separate protocol and will be documented in its own directory when complete.

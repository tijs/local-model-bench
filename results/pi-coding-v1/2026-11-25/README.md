# Pi coding comparison · 25 November 2026

One Pi 1.6.0 trajectory per task and profile on the same 32 GiB Apple M1 Max. Each run used 16,384 tokens of context, 4,096 output tokens per request, seed 17, and 480 seconds per task. Each pass requires a final patch that satisfies every visible and withheld check. Times in the task table measure seconds from starting Pi to saving the first passing edit.

| Task | inkling-stock | inkling-loopcd-02 | groot |
|---|---:|---:|---:|
| affine-cipher | pass · 122.5s | pass · 117.9s | pass · 58.9s |
| config-option | pass · 60.6s | pass · 61.8s | pass · 28.9s |
| event-keys | pass · 83.5s | pass · 47.7s | pass · 60.4s |
| ledger-rounding | pass · 97.8s | pass · 115.3s | pass · 165.7s |
| merge-ranges | pass · 51.5s | pass · 70.0s | pass · 25.1s |
| midnight-window | pass · 52.7s | pass · 47.2s | pass · 23.8s |
| page-cursors | pass · 52.4s | pass · 52.6s | fail |
| proverb | fail | fail | pass · 41.3s |
| resume-import | pass · 191.5s | pass · 130.9s | pass · 90.3s |
| transpose | pass · 159.3s | pass · 94.9s | pass · 75.6s |
| unicode-stream | pass · 82.9s | pass · 54.9s | pass · 18.4s |
| variable-length-quantity | pass · 102.8s | pass · 118.0s | fail |
| **Passing final patches** | 11/12 | 11/12 | 10/12 |

inkling-stock vs inkling-loopcd-02: 11 shared successes. Median paired time difference (right minus left) -4.6s. inkling-stock was faster on 5.

inkling-stock vs groot: 9 shared successes. Median paired time difference (right minus left) -31.6s. inkling-stock was faster on 1.

inkling-loopcd-02 vs groot: 9 shared successes. Median paired time difference (right minus left) -32.9s. inkling-loopcd-02 was faster on 2.

| Profile | Private maintenance | Public exercises | Task deadlines | Output-capped turns | Median agent wall time over all 12 tasks |
|---|---:|---:|---:|---:|---:|
| inkling-stock | 8/8 | 3/4 | 0 | 1 | 116.1s |
| inkling-loopcd-02 | 8/8 | 3/4 | 0 | 0 | 93.9s |
| groot | 7/8 | 3/4 | 0 | 1 | 66.6s |

| Profile | Total agent time | Model requests | Completion tokens | Median decode tok/s per request |
|---|---:|---:|---:|---:|
| inkling-stock | 28.8 min | 83 | 25,463 | 25.0 |
| inkling-loopcd-02 | 23.9 min | 82 | 19,189 | 25.0 |
| groot | 15.4 min | 77 | 34,897 | 57.3 |

An initial guided-profile launch encountered a port in TIME_WAIT before any task. The first Groot run was interrupted after nine graded tasks. The comparison uses only the subsequent complete runs. Total agent time sums elapsed task time, including visible tests and tool calls. Model loading, checksum verification and offline grading are excluded. The three runs were sequential and Groot was restarted later the same day.

Full transcripts, replayable edits, Mei request logs, and resource journals are archived at `/Volumes/Expansion/pi-coding-runs/three-profiles-a3rDSqGf`. The adjacent profile directories contain portable receipts for the comparison CLI. See the [track instructions](../../../docs/PI_CODING.md).

LoopCD 0.2 solved the same 11 tasks as stock Inkling, using 24.6% fewer completion tokens and 17.0% less total agent time. It reached a passing patch earlier on six of the eleven shared successes. Both missed the optional qualifier placement in the proverb. Groot passed that case and reached a passing patch sooner than guided Inkling on seven of nine shared successes. It returned a spurious pagination cursor on an exact page boundary and hit the output cap before writing its variable-length quantity implementation. These measurements support keeping 0.2 as an experimental coding profile. One trajectory per task and a score close to the suite ceiling limit the case for changing the default.

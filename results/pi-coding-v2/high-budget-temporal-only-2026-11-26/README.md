# High-budget temporal overlay repeat · 26 November 2026

This two-run diagnostic is separate from both four-task cohorts. It repeats the exact `temporal-overlay` task once each for Inkling stock and Inkling LoopCD 0.2, at 32,768 context tokens, 16,384 output tokens per request, and an 1,800-second task limit. The shared task SHA is `29e3b557cf95e87460767558add42e83637f7ce8a42c3da9f5223363ab8a08c2`; both complete manifests have the same protocol fingerprint `a27b8759…` and were served successfully. No timeout or infrastructure/resource failure occurred.

| Profile | Result | First pass | Wall | Output tokens | Turns | Writes | Capped turns |
|---|---|---:|---:|---:|---:|---:|---:|
| Inkling stock | fail · 5/9 grader cases | — | 1,053.9s | 16,699 | 7 | 0 | 1 |
| Inkling LoopCD 0.2 | pass · 9/9 hidden cases | 373.8s | 487.5s | 6,020 | 9 | 2 | 0 |

Each task made only accepted requests with the full 16,384-token maximum. The stock failure was the same pattern and nearly identical size as the stock full-cohort temporal attempt (five of nine grader cases failed, 16,699 tokens, 1 cap, 7 turns, 1,055.9s). The guided pass likewise reproduces the full-cohort guided pass (9/9, 6,020 tokens, 2 writes, first pass 373.24s, wall 487.0s). This supports repeatability for these two specific task trajectories; it does not establish a broad quality or speed effect across tasks.

Portable receipts are in the `stock/` and `guided/` directories: manifests, configs, launch/status/shutdown metadata, final grade, snapshots, and per-request wire budgets. Full transcripts, tool logs, request/resource journals, and Mei server logs remain in `/Volumes/Expansion/pi-coding-runs/v2-high-budget-temporal-only-20261126-1caa74ec`.

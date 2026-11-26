# Pi coding v2 higher-budget cohort

This is a separate matched cohort using the exact committed `pi-coding-v2` task suite and six model profiles. It does not replace or combine with the original 24 lower-budget profile/task rows.

Only the per-profile runtime budgets differ from the original configs: `context: 32768`, `output_tokens: 16384`, and `task_seconds: 1800`. Profile identities, endpoints, model and binary hashes, Pi version, environment, suite, tasks, seeds, tools, workspace behavior, and runner remain unchanged.

The 32,768 context cap is selected from the project's validated Inkling capability notes (`docs/INKLING.md`): this cap succeeded on the campaign host, while 65,536 hit the 24 GiB guard. The prior cohort's largest observed prompt was 5,058 tokens; with the requested 16,384-token output, that is 21,442 tokens inside the configured context. The runner advertises `contextWindow: 32768` and `maxTokens: 16384` to Pi, and Mei must report the matching context cap before tasks begin.

Pi 1.6.0 may lower `max_tokens` on later requests as the conversation grows. This behavior is implemented in `@earendil-works/pi-ai/dist/api/simple-options.js` by `clampMaxTokensToContext()`, which estimates context usage and leaves a 4,096-token safety margin (using a 15% estimate margin when that leaves at least 32,768 output tokens). The first request must carry the full configured ceiling; later requests may carry a positive effective value at or below 16,384. The runner records every accepted or rejected effective value in each task's `wire-budgets.jsonl`. It rejects an oversized value and records it before stopping. These effective budgets are protocol telemetry, not changes to the configured ceiling. Profiles run serially with the existing resource gates.

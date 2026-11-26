# Pi coding v2 higher-budget cohort

This is a separate matched cohort using the exact committed `pi-coding-v2` task suite and six model profiles. It does not replace or combine with the original 24 lower-budget profile/task rows.

Only the per-profile runtime budgets differ from the original configs: `context: 32768`, `output_tokens: 16384`, and `task_seconds: 1800`. Profile identities, endpoints, model and binary hashes, Pi version, environment, suite, tasks, seeds, tools, workspace behavior, and runner remain unchanged.

The 32,768 context cap is selected from the project's validated Inkling capability notes (`docs/INKLING.md`): this cap succeeded on the campaign host, while 65,536 hit the 24 GiB guard. The runner preflight must verify the prompt and requested output fit the configured context wire budget. Profiles run serially with the existing resource gates.

# Model-only benchmark

Native HTTP model behavior with mocked tools. No coding-agent, Peixinho application, or historical composite score is claimed.

Hermes-specific workloads are retired. Historical rows remain in log.jsonl and the legacy leaderboard.

| Model | Engine | Config | Runner | Suite | Profile | Passed / rows | Harness errors | Median decode tok/s | Median TTFT s |
|---|---|---|---|---|---|---:|---:|---:|---:|

Groups retain configuration and runner identity. Sanity is a gate; model_tools uses a neutral prompt and six simulated tools. Single trials and timing samples do not establish a front-runner.

# Model-only benchmark

Native HTTP model behavior with mocked tools. No coding-agent, Peixinho application, or historical composite score is claimed.

Hermes-specific workloads are retired. Historical rows remain in log.jsonl and the legacy leaderboard.

| Model | Engine | Config | Runner | Suite | Profile | Passed / rows | Harness errors | Median output tok/s (wall) | Median TTFT s |
|---|---|---|---|---|---|---:|---:|---:|---:|
| OsaurusAI/Flint-40B-A2.5B-JANGH2 | mei | 905cd2922f41 | 679bba5284e1 | model_tools | model_card | 11/24 | 0 | 28.61 | 3.08 |
| OsaurusAI/Flint-40B-A2.5B-JANGH2 | mei | 905cd2922f41 | 679bba5284e1 | sanity | deterministic | 6/6 | 0 | 36.48 | 1.13 |

Groups retain configuration and runner identity. Sanity is a gate; model_tools uses a neutral prompt and six simulated tools. Output rate divides completion tokens by total task wall time, including prefill and tool turns. Single trials and timing samples do not establish a front-runner.

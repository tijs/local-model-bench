# Qwen3.6 Mei benchmark interruption — 2026-09-06

- Config: `configs/Qwen3.6-35B-A3B/mei.yaml`
- Config hash: `e9d6db1b6675`
- Runner/source commit at launch: `39dae7a6ea44`
- Artifact: `mlx-community/Qwen3.6-35B-A3B-4bit`
- Engine: `mei`
- Port: `8024`

The first full-benchmark attempt was intentionally stopped after the sanity suite and before Hermes Ops completed. It appended exactly two rows to `results/log.jsonl`:

- `sanity-basic`: PASS
- `sanity-tool`: PASS

No Hermes Ops or coding rows belong to this attempt. The candidate server and runner process were verified absent after stopping. The config used `hermes_provider: null`, which would have skipped coding suites even if the run continued; the next attempt uses the existing isolated `bench-mei` provider on port 8024 and therefore has a different config hash.

This is preserved as interrupted exploratory evidence, not a complete benchmark result and not part of the final comparison set.

# local-model-bench benchmark-v9.10.2

Simplifies all three comparison figures to one weighted-average point per model
per metric, using only the two fresh selected runs on frozen benchmark-v9.10.
The previous pairs were request seeds 17 and 29 of the same pinned model/runtime,
not different model checkpoints. No new inference run was needed.

Household and Python quality pool passed/attempted tasks separately. Each run
has the same 12+3 task coverage, so each receives 50% weight. Full-run time and
per-run peak wired-memory increase use the same equal-weight means. Failed tasks
and missing script submissions stay in the quality denominator. Weights do not
depend on success, duration, tokens, responses or memory-sample count.

The charts keep explicit Mei (Swift/MLX) circles and llama.cpp (GGUF) diamonds.
Individual seed points and range lines are removed from figures; the exact eight
observations, selected source identities, per-run CSV and raw task rows remain.
The JSON export adds weighting metadata and four model averages, also available
in model-averages.csv. Prior per-run graphs remain in release v9.10.1.

Validation: all 13 focused reporting tests pass, including pooled quality,
average costs, preservation of all eight observations, incomplete/mixed profile
rejection and unavailable memory handling. Ruff and ty pass. Real PNG figures
were visually reviewed and SVGs validated. This changes reporting only; no
measured task, grader, serving profile or raw result changes.

[Summary and averaged graphs](../../results/AGENT_SUMMARY.md) ·
[Weighting and method](../FOUR_MODEL_COMPARISON.md) ·
[Model-average CSV](../../results/charts/four-model-v9.10/model-averages.csv)

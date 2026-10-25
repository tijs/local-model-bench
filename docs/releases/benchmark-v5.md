# local-model-bench benchmark-v5

Released 2026-10-25. This release follows the existing `benchmark-v1` through
`benchmark-v4` methodology tags. Its active result scope is `model-only-v1`.
The Python runner dependency metadata is separate from methodology versioning.

## Current behavior

- Runs native HTTP model checks: two sanity cases and eight neutral tool-use
  cases, with six simulated tools. `--trials 3` executes 30 trials.
- Removes the Hermes runtime, profiles, coding-agent dispatch, restoration and
  service management from the active benchmark. Public runner entry points
  refuse retired stages/suites. No Hermes installation is required.
- Preserves historical Hermes drivers, fixtures, transcripts, configs and
  append-only results as archived evidence. Existing release/ranking tags stay
  unchanged; historical regression tests still exercise archived logic with mocks.
- Writes current results to `results/MODEL_ONLY.md`, separately from historical
  composite rankings. Results retain config, runner, engine, suite and sampler
  identities and remain ineligible for the historical composite score.
- Pins admitted config bytes for suite execution, applies the isolated Mei
  runtime base to teardown, rejects incomplete/duplicate trial summaries, and
  propagates report-generation failure.
- Supports explicit Flint/JANGH2 launch opt-ins, with pinned model/runtime
  provenance and preserved admission, failure and memory-pressure evidence.

## Validation and measured limits

The locked harness regression suite passes 495 tests. New report code also
passes Ruff and ty checks; modified lifecycle scripts pass Bash syntax checks.
The Flint JANGH2 pilot completed all 30 trials: sanity 6/6 and neutral tools
11/24, with no harness/transport errors. Tool loops, missing actions and empty
responses remain unresolved. This is not a model-quality endorsement.

System free memory reached 13% and warning pressure level 2 on the 32 GiB M1
Max; swap peaked at 3280.12 MiB. The server stopped normally, memory recovered,
and all 16 original model files rehashed unchanged. No disk or memory gate was
bypassed. Investigate residency growth before scaling/repeating that profile.
See `results/MODEL_ONLY.md` and `artifacts/flint-model-only-20261025/`.

## Use and comparability

```bash
uv sync --locked
uv run --locked python -m unittest discover -s runner/tests -v
uv run --locked python runner/run_bench.py --config configs/<model>/<engine>.yaml --trials 3
```

Commit the exact config first; use its served-model identity, pinned runtime,
normal disk gate and one local server. Monitor host memory and stop owned
servers afterward. CoCore remains off and is not managed or restored.

The neutral prompt and tool manifest differ from the historical Hermes workload.
Do not compare their pass rates as one continuous benchmark or relabel old rows.
Output tokens/s in the current report includes whole task wall time, including
prefill/tool turns; it is not pure decode throughput.

Peixinho is still a design. This release contains no Peixinho application driver,
iPhone tests, product acceptance results or claim of household readiness. Future
workflow stand-ins need their own versioned task/grader/profile identity and
must remain distinct from eventual real-app integration evidence.

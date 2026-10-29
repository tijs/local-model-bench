# Python automation track

`python-automation-v1` measures authoring, running and repairing small Python CLI programs on synthetic household data. It complements the twelve synthetic household workflows. It is neither a replacement application-coding suite nor actual Peixinho acceptance evidence. Historical Hermes coding runners remain retired.

The accompanying household track now permits4096 tokens per turn,180 seconds per HTTP turn and600 seconds per task (12 turns); older v6 baselines retain their original immutable budget identities. Shopping capture instructions now explicitly require item names while Inbox captures retain original utterances; validators remain strict.

A committed full-household config opts in with `python_automation: true`. `runner/run_bench.py` owns one server lifecycle, runs the household track, then this track. Each track retains its own admission, manifest, task rows and report. A partial or infrastructure-failed track cannot count as a complete result.

| Task | Required behavior | Edge cases checked after model finishes |
|---|---|---|
| shopping-csv | Normalize item names, sum duplicate quantities, emit sorted JSON | Empty input, blank quantity, zero, casefolding, Unicode, quoted commas, repeated whitespace |
| expense-summary | Include paid rows, aggregate decimal-safe category totals | Half-cent rounding, refunds, ignored statuses, blank categories, empty input, deterministic ordering |
| reminder-repair | Repair a supplied exporter; filter pending reminders by actual instant | Inclusive cutoff, offsets, tie ordering, missing/null/naive due, completed items, empty input, year boundary |

The full contracts are in `runner/automation_tasks.py`. Exact schemas, normalization and rounding rules appear in model-visible instructions. The agent gets only `read_file`, `write_script`, and `run_script`. It reads the visible fixture, writes `solution.py`, runs it, sees bounded stdout/stderr/exit status, and may repair it. The program reads the supplied filename from `sys.argv[1]` and emits exactly one JSON value on stdout. Packages, network, subprocesses and script-side file writes are unavailable. The trusted write tool can replace only `solution.py`; synthetic inputs cannot be edited.

Final grading executes the last submitted script on the visible input and three additional variants, including empty input. Expected values/validators never enter the model tools or script filesystem. A visible-only hardcoded solution fails. JSON shape/value comparisons ignore object key order but preserve array order and integer/string distinctions; duplicate keys and non-finite values are rejected. A script must also have been executed successfully by the agent in its final submitted form. A repairable execution error is feedback, not automatically a task failure. Invalid tool calls, unfinished generations and incorrect final outputs remain failures.

## Execution and budgets

Use the locked Astral Python environment (`uv sync --locked`, `uv run --locked`). Scripts run Python 3.12 in isolated mode without site initialization. The macOS executor must establish deny-by-default OS containment before loading submitted code, with a read-only synthetic workspace/runtime and no access to the repository, private files, network or other processes. Unsupported containment fails closed. Adversarial regressions must verify canary reads/writes, symlink escapes, process inspection, subprocess/self-exec, network, resource exhaustion and cancellation; a temporary directory alone is not containment.

The automation loop uses up to eight model turns, 4096 tokens per turn (including reasoning), and 480 seconds of agent time per task. Each script execution has a five-second wall deadline and bounded output/resources; four post-agent validation executions add their measured time to task wall time. These are explicit initial task budgets, not a vendor capability ceiling. Budget exhaustion is reported separately from incorrect output. Vendor sampling profiles are preserved; no guessed reasoning effort is added.

`results/automation/log.jsonl` is append-only. Per-run config snapshots, native responses, tool journal, submitted source, script hash, isolated execution identity and validation outcomes live under `results/automation/runs/`. `runner/build_automation_report.py` generates `results/AUTOMATION.md` with planned/executed coverage and provenance checks. Reports distinguish development/held-out partitions and keep tool, fixture, validator and runtime identities. Shared model-server cache does not establish independent trials.

Before live runs: pass the reference/intentional-wrong-script tests, containment tests and harness regressions; review the implementation; commit the exact launch config; then use the normal disk and monitored memory/swap gates. A model-quality attribution must inspect raw calls/source and reproduce suspected owned failures rather than treating every failed grade as a model defect.

## Supervised runs and released comparison

Use the packaged supervisor for the current full two-track profiles. Choose a new output directory for every attempt; existing evidence is never overwritten:

```bash
uv run --locked python runner/supervise_bench.py --config configs/agent-automation-v7-20261029/qwen-calibration-retry.yaml --output artifacts/qwen-calibration-example --trials 1
```

The supervisor checks committed source/config bytes, normal pressure, disk space and the profile's launch headroom before starting the runner. Current profiles require85%reported free memory for Qwen/Ornith/MiniCPM and75%for Flint. Fixed independent stops remain: critical pressure immediately, two warning samples, two samples at or below10%free,2GiB swap growth,16GiB absolute swap and10GiB disk floor. It samples every5seconds, records owned process footprints, and gives an interrupted suite time to persist evidence before bounded teardown. These are measured guards, not a hard total-memory allocation ceiling. Wait for a quiet host; the supervisor does not stop unrelated work.

Each supervision has a unique ID, exact admitted config snapshot/hash, source fingerprints and registered track run IDs. The parent rejects config changes after resource admission. Both track manifests/rows retain the same supervision ID. Final comparison additionally verifies the same serving runtime across tracks, time windows, exact released config/method fingerprints, raw artifact grades/counters and full coverage. A successful monitor from a different attempt of the same config cannot be reused.

`runner/build_agent_leaderboard.py --campaign <selection.json>` generates the final comparison from explicit run selections after a release exists. It keeps household and Python scores separate and uses no weighted composite. Partial, critical-boundary, uncommitted-source or pressure-tainted evidence receives no order. Exact selected runs, runtime/quant/config details and failure classes remain available for review; a single trial cannot establish statistical superiority.

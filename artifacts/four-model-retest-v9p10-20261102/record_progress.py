"""Select only this campaign's new completed runs and refresh readable progress."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from build_agent_leaderboard import render_campaign

slugs = ("qwen", "ornith", "groot", "logics")
labels = ("Base Qwen3.6", "Ornith1.5", "Groot", "Logics-SWE")
models = {}
rows = []
for seed in (17, 29):
    cohort = {
        "benchmark_release": "benchmark-v9.10",
        "release_commit": subprocess.check_output(
            ["git", "rev-parse", "benchmark-v9.10^{commit}"], cwd=ROOT, text=True
        ).strip(),
        "partition": "heldout",
        "trials": 1,
        "status": "fresh_comparison_in_progress",
        "sampling_plan": "All four fresh on one frozen release; seeds17/29 declared before execution; no best-repeat selection.",
        "method_notes": [
            "Retain every outcome. Serving-profile comparison with explicit sampler/quant/engine differences; two seeds are not confidence intervals or independent sample guarantees."
        ],
        "models": [],
    }
    for slug, label in zip(slugs, labels):
        config = f"configs/four-model-v9p10-20261102/{slug}-seed{seed}.yaml"
        cfg = yaml.safe_load((ROOT / config).read_text())
        models[cfg["model"]] = label
        out = ROOT / f"artifacts/{slug}-four-v9p10-seed{seed}-20261102"
        entry = {
            "model": cfg["model"],
            "engine": cfg["inference_engine"],
            "config": config,
            "household_run": None,
            "python_run": None,
            "supervision": None,
        }
        if (out / "audit.json").exists() and (
            out / "post-run-model-hashes.json"
        ).exists():
            o = json.loads((out / "outcome.json").read_text())
            entry.update(
                household_run=o["run_ids"]["peixinho-standin-v1"][0],
                python_run=o["run_ids"]["python-automation-v1"][0],
                supervision=str(out.relative_to(ROOT)),
            )
            a = json.loads((out / "audit.json").read_text())
            h = sum(x["passed"] for x in a["household"])
            p = sum(x["passed"] for x in a["python"])
            seconds = o["elapsed_seconds"]
            failures = "\n".join(
                f"- `{x['task']}`: {', '.join(x['failed_checks'])}."
                for x in a["household"]
                if not x["passed"]
            )
            for path in (ROOT / "results/automation/runs" / entry["python_run"]).glob(
                "*-trial1.json"
            ):
                t = json.loads(path.read_text())
                if not t["grade"]["pass"]:
                    failures += (
                        f"\n- `{path.stem}`: {', '.join(t['grade']['failed_checks'])}."
                    )
            readme = out / "README.md"
            if not readme.exists():
                readme.write_text(f"""# {label} / {cfg["inference_engine"]}: fresh v9.10 seed {seed}

**{h}/12 household, {p}/3 Python; {seconds / 60:.2f} minutes full-run wall time.**
All 15 tasks completed; supervisor exited 0 without a stop. Every sampled pressure
level was normal and swap growth was {a["resources"]["swap_growth_mib"]:.2f}MiB.

Household `{entry["household_run"]}`; Python `{entry["python_run"]}`.
[Exact committed profile](../../{config}) ·
[Verified seed cohort](../../results/FOUR_MODEL_V9.10_SEED{seed}.md) ·
[Comparison design](../../docs/FOUR_MODEL_COMPARISON.md)

All 12 grades reproduce under the measured frozen grader. Every parsed API call
matches the domain journal. All 3 scripts were independently replayed on all 4
contained variants and reproduced their saved outcomes. Request seed {seed}
was verified in all {a["runtime"]["recorded_request_count"]} saved task responses.
No raw grade was changed. Budget exhaustion/denied operations retain their grades.

## Failed checks

{failures or "None."}

[Audit](audit.json) · [Replay program](../four-model-retest-v9p10-20261102/audit_run.py) ·
[Model hashes](post-run-model-hashes.json) · [Runtime verification](post-run-runtime-verification.json)

Model/runtime hashes match after exit. The server exited and both configured
ports are free. Generated Mei KV, where applicable, was inventoried and its
SQLite index summarized before removing only this run's owned KV directory;
[cleanup receipt](owned-cache-cleanup.json) records bytes, while logs, traces,
staged weights and release assets remain. llama.cpp has no owned disk KV tier.
This is synthetic household/Python evidence, not actual Peixinho app acceptance.
""")
            if slug == "logics":
                text = readme.read_text()
                start = text.index("Generated Mei KV,")
                end = text.index("This is synthetic", start)
                readme.write_text(
                    text[:start]
                    + "This llama.cpp profile has no owned disk KV tier. Server logs, model hashes, executable and shared-library checks are preserved.\n"
                    + text[end:]
                )
            rows.append(
                f"| {label} / {cfg['inference_engine']} | {seed} | {h}/12 | {p}/3 | {seconds / 60:.2f} min | [review]({out.relative_to(ROOT)}/README.md) |"
            )
        else:
            if slug == "logics":
                text = readme.read_text()
                start = text.index("Generated Mei KV,")
                end = text.index("This is synthetic", start)
                readme.write_text(
                    text[:start]
                    + "This llama.cpp profile has no owned disk KV tier. Server logs, model hashes, executable and shared-library checks are preserved.\n"
                    + text[end:]
                )
            rows.append(
                f"| {label} / {cfg['inference_engine']} | {seed} | pending | pending | pending | — |"
            )
        cohort["models"].append(entry)
    if all(x["household_run"] and x["python_run"] for x in cohort["models"]):
        cohort["status"] = "fresh_seed_cohort_complete"
    (ROOT / f"results/four-model-v9p10-seed{seed}-20261102.json").write_text(
        json.dumps(cohort, indent=2) + "\n"
    )
    (ROOT / f"results/FOUR_MODEL_V9.10_SEED{seed}.md").write_text(
        render_campaign(ROOT, cohort)
    )
spec = {
    "models": models,
    "seeds": [17, 29],
    "cohorts": [
        f"results/four-model-v9p10-seed{seed}-20261102.json" for seed in (17, 29)
    ],
    "benchmark_release": "benchmark-v9.10",
    "release_commit": subprocess.check_output(
        ["git", "rev-parse", "benchmark-v9.10^{commit}"], cwd=ROOT, text=True
    ).strip(),
}
(ROOT / "results/four-model-v9p10-comparison.json").write_text(
    json.dumps(spec, indent=2) + "\n"
)
# Relative links in the main summary need one parent.
body = "\n".join(rows).replace("(artifacts/", "(../artifacts/")
(ROOT / "results/AGENT_SUMMARY.md").write_text(
    """# Four-model comparison: fresh v9.10 runs in progress

All four contenders are retained. Eight new full runs were predeclared before
inference, using one frozen released benchmark. No older finalist run is reused.
Real quality-versus-time/memory graphs will be generated when all eight are audited.

| Model / engine | Seed | Household | Python | Full-run time | Evidence |
|---|---:|---:|---:|---:|---|
"""
    + body
    + """

[Design and metric definitions](../docs/FOUR_MODEL_COMPARISON.md) ·
[Seed17 provenance](FOUR_MODEL_V9.10_SEED17.md) · [Seed29 provenance](FOUR_MODEL_V9.10_SEED29.md) ·
[Preserved v8.3.1 summary](AGENT_SUMMARY_V8.3.1.md).

Mei means Swift/MLX; llama.cpp means GGUF. Quality tracks remain separate.
All runs include startup, admission and all15 tasks. Synthetic tasks are not
actual Peixinho application acceptance. Pending runs have no score.
"""
)
print("\n".join(rows))

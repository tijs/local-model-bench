"""Check planned serving fields against committed launch templates; never launch."""

import json
import shlex
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
FIELDS = {
    "context_cap": "--context-cap",
    "prefill_step_size": "--prefill-step-size",
    "normal_output_budget": "--max-tokens",
    "retained_prefix_bytes": "--prefix-cache-limit-bytes",
    "allocator_cache_bytes": "--cache-limit-bytes",
}


def config(path):
    committed = subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)
    if committed != (ROOT / path).read_bytes():
        raise ValueError("launch template/baseline differs from committed source")
    value = yaml.safe_load(committed)
    return value, shlex.split(value["benchmark_launch_command"])


def argument(argv, flag):
    if argv.count(flag) != 1:
        raise ValueError(f"requires one explicit {flag}")
    return argv[argv.index(flag) + 1]


def verify(declaration):
    cells = declaration["cells"]
    expected = {(m, s) for m in ("qwen", "ornith", "groot", "logics") for s in (17, 29)}
    if len(cells) != 8 or {(c["model"], c["seed"]) for c in cells} != expected:
        raise ValueError("requires eight distinct predeclared model/seed cells")
    checked = []
    for cell in cells:
        expected_engine = "llama.cpp" if cell["model"] == "logics" else "mei"
        if cell["engine"] != expected_engine:
            raise ValueError("unexpected engine for declared model")
        baseline, old = config(cell["baseline_config"])
        if baseline["source_revision"] != cell["weight_revision"]:
            raise ValueError("weight revision differs from baseline")
        if cell["engine"] != "mei":
            continue
        template, argv = config(cell["launch_profile_template"])
        if template["source_revision"] != cell["weight_revision"]:
            raise ValueError("weight revision differs from launch template")
        for field, flag in FIELDS.items():
            if int(argument(argv, flag)) != cell[field]:
                raise ValueError(
                    f"{cell['model']} {field} differs from launch template"
                )
        if (
            template["capacity_plan"]["allocator_cache_bytes"]
            != cell["allocator_cache_bytes"]
            or int(argument(old, "--cache-limit-bytes"))
            != cell["prior_scored_allocator_cache_bytes"]
        ):
            raise ValueError("allocator capacity/baseline declaration mismatch")
        checked.append(
            {
                "model": cell["model"],
                "seed": cell["seed"],
                **{field: cell[field] for field in FIELDS},
            }
        )
    return checked


if __name__ == "__main__":
    declaration = json.loads((PREP / "campaign.json").read_text())
    print(
        json.dumps(
            {
                "scope": "Preparation fields only; no final release qualification",
                "checked": verify(declaration),
            },
            indent=2,
        )
    )

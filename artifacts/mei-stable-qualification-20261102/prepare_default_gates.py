"""Matched control/candidate qualification at the tested allocator allowance."""

import copy
import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
CACHE = 512 * 2**20


def profile(slug, cell, native=False):
    old_name = (
        f"{slug}-native.yaml"
        if native
        else f"{slug}-{'a1' if cell.startswith('a') else 'c1'}.yaml"
    )
    cfg = yaml.safe_load(
        (ROOT / "configs/mei-stable-qualification-20261102" / old_name).read_text()
    )
    identity = f"{slug}-stable-default-{cell}-20261102"
    runtime = str(Path.home() / ".local/share/local-model-bench/mei-runtime" / identity)
    old = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
    argv = shlex.split(cfg["benchmark_launch_command"])
    argv[argv.index("--cache-limit-bytes") + 1] = str(CACHE)
    cfg["benchmark_launch_command"] = shlex.join(argv).replace(old, runtime)
    cfg["required_runner_environment"].update(
        MEI_RUNTIME_BASE=runtime,
        VMLX_ENABLE_UNSAFE_COMPILE="1",
        SWIFT_DETERMINISTIC_HASHING="0",
    )
    cfg["capacity_plan"]["allocator_cache_bytes"] = CACHE
    cfg["capacity_plan"]["derivation"] = (
        "Pinned model weight/config and65536-token hybrid-cache bound unchanged; "
        "512MiB retained prefixes,512MiB allocator allowance,2GiB workspace and4GiB host reserve. "
        "Feasibility estimate,not a reservation or proof of full-context safety."
    )
    cfg["benchmark_status"] = (
        "Predeclared matched default-profile qualification: A=API-correct control,B=lookup candidate; "
        "both compilation enabled,512MiB allocator cache,random hashing. A1/B1/B2/A2 per model; "
        "ten measured short/30K decodes per source. No profiling or scored task rows."
    )
    cfg["settings"] = [
        {
            "name": "single_variable",
            "value": "Control and candidate differ only in the phase-flag lookup patch. Both use the same tested512MiB allocation-cache allowance and public compilation setting; exact original production binaries/Metal/weights are unchanged. Closed-negative routed-MoE graph regions stay off.",
        },
        {
            "name": "limits",
            "value": "The short cache screen supports this allowance but does not prove full30K/native stability. Full gates retain every sample and stop for guard/coverage/parity/native failure; performance still needs review before promotion.",
        },
    ]
    if not native:
        if cell != "b1":
            cfg.pop("mei_swift_acceptance", None)
    else:
        cfg["benchmark_status"] = (
            "Full native tools/history/cache/exact65536 gate on the unmodified candidate at512MiB allocator allowance,compilation enabled,normal advertised output budget. No task-score or published-release claim."
        )
        # Preserve source-equivalence provenance from the original native profile.
        original = yaml.safe_load(
            (ROOT / "configs/mei-stable-qualification-20261102" / old_name).read_text()
        )
        cfg["settings"].extend(copy.deepcopy(original["settings"]))
    return cfg


def main():
    cells = []
    native = []
    for slug in ("groot", "qwen", "ornith"):
        for cell in ("a1", "b1", "b2", "a2", "native"):
            cfg = profile(slug, cell, native=cell == "native")
            path = (
                ROOT
                / f"configs/mei-stable-qualification-20261102/{slug}-default-{cell}.yaml"
            )
            with path.open("x") as stream:
                yaml.safe_dump(cfg, stream, sort_keys=False, width=100)
            record = {
                "model": slug,
                "cell": cell,
                "config": str(path.relative_to(ROOT)),
                "output": f"artifacts/mei-stable-{slug}-default-{cell}-20261102",
            }
            (native if cell == "native" else cells).append(record)
    with (PREP / "default-matrix.json").open("x") as stream:
        json.dump(
            {
                "cells": cells,
                "full_native_gates": native,
                "purpose": "matched unprofiled default-profile qualification before stable promotion",
            },
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()

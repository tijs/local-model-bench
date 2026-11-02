"""Test allocation-cache headroom without changing the frozen runtime."""

import copy
import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent


def main():
    base = yaml.safe_load(
        (ROOT / "configs/mei-stable-qualification-20261102/qwen-c1.yaml").read_text()
    )
    cells = []
    for cell in ("a1", "b1", "b2", "a2", "a3", "b3"):
        cfg = copy.deepcopy(base)
        cfg.pop("mei_swift_acceptance")
        cache_bytes = (128 if cell.startswith("a") else 512) * 2**20
        runtime = str(
            Path.home()
            / f".local/share/local-model-bench/mei-runtime/qwen-stable-allocator-{cell}-20261102"
        )
        old = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
        argv = shlex.split(cfg["benchmark_launch_command"])
        argv[argv.index("--cache-limit-bytes") + 1] = str(cache_bytes)
        cfg["benchmark_launch_command"] = shlex.join(argv).replace(old, runtime)
        cfg["required_runner_environment"].update(
            MEI_RUNTIME_BASE=runtime, SWIFT_DETERMINISTIC_HASHING="0"
        )
        cfg["capacity_plan"]["allocator_cache_bytes"] = cache_bytes
        cfg["capacity_plan"]["derivation"] = (
            "Same pinned Qwen weight/config and 65536-token hybrid-cache bound as the "
            "original profile;512MiB retained prefixes,2GiB workspace and4GiB host allowance. "
            f"Allocator allowance and requested effective cap are {cache_bytes}bytes. "
            "Feasibility estimate only,not a reservation or proof of context safety."
        )
        cfg["mei_qualification"]["loaded_tokens"] = 1024
        cfg["benchmark_status"] = (
            "Allocation-cache hypothesis screen, not release qualification: A=128MiB, B=512MiB; same frozen production candidate, compilation enabled, random hashing, no task/thread profiler. Three fresh processes per arm; short/1024 contexts with five measured128-token decodes."
        )
        cfg["settings"] = [
            {
                "name": "hypothesis",
                "value": "If limited reusable GPU-buffer headroom contributes to rate bands,512MiB should reduce variation and retain cache above128MiB with identical outputs. Comparable variation or retention below the old cap rejects this as a sufficient explanation. Status must report the requested effective limit; byte plan includes the full allowance. No production default change follows from the screen alone.",
            }
        ]
        path = (
            ROOT
            / f"configs/mei-stable-qualification-20261102/qwen-allocator-{cell}.yaml"
        )
        with path.open("x") as stream:
            yaml.safe_dump(cfg, stream, sort_keys=False, width=100)
        cells.append(
            {
                "model": "qwen",
                "cell": cell,
                "config": str(path.relative_to(ROOT)),
                "output": f"artifacts/mei-stable-qwen-allocator-{cell}-20261102",
            }
        )
    with (PREP / "allocator-screen.json").open("x") as stream:
        json.dump(
            {"cells": cells, "purpose": "bounded cache-headroom hypothesis screen"},
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()

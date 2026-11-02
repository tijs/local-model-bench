"""Predeclare a six-process screen of Swift hash seeding on one frozen runtime."""

import copy
import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
ORDER = ("r1", "d1", "d2", "r2", "r3", "d3")


def main():
    base = yaml.safe_load(
        (ROOT / "configs/mei-stable-qualification-20261102/qwen-c1.yaml").read_text()
    )
    cells = []
    for cell in ORDER:
        cfg = copy.deepcopy(base)
        cfg.pop("mei_swift_acceptance")
        runtime = str(
            Path.home()
            / f".local/share/local-model-bench/mei-runtime/qwen-stable-hash-{cell}-20261102"
        )
        old = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
        argv = shlex.split(cfg["benchmark_launch_command"])
        cfg["benchmark_launch_command"] = shlex.join(argv).replace(old, runtime)
        cfg["required_runner_environment"].update(
            MEI_RUNTIME_BASE=runtime,
            SWIFT_DETERMINISTIC_HASHING="1" if cell.startswith("d") else "0",
        )
        cfg["mei_qualification"]["loaded_tokens"] = 1024
        cfg["benchmark_status"] = (
            "Exploratory hash-seeding screen, not a full performance qualification: "
            "same frozen compilation-enabled candidate; R=random seeding, D=deterministic seeding. "
            "Order R1/D1/D2/R2/R3/D3, three processes per arm, five observations per context/process. "
            "No source/model/Metal change. Short/1024-token prompts; no 30K claim."
        )
        cfg["settings"] = [
            {
                "name": "hypothesis",
                "value": "If randomized dictionary/materialization/graph construction order contributes to process-level rate bands, deterministic hashing should reduce between-process variation. Persistent comparable variation rejects this screen's hypothesis; neither outcome proves a production fix.",
            },
            {
                "name": "bounds",
                "value": "Exploratory diagnostic only. Same normal pressure/swap/disk/deadline guards. Runtime hash-setting behavior is separately verified by hash-seed-probe.swift before loading. No production default or source change is authorized by a passing screen alone.",
            },
        ]
        path = ROOT / f"configs/mei-stable-qualification-20261102/qwen-hash-{cell}.yaml"
        with path.open("x") as stream:
            yaml.safe_dump(cfg, stream, sort_keys=False, width=100)
        cells.append(
            {
                "model": "qwen",
                "cell": cell,
                "config": str(path.relative_to(ROOT)),
                "output": f"artifacts/mei-stable-qwen-hash-{cell}-20261102",
            }
        )
    with (PREP / "hash-screen.json").open("x") as stream:
        json.dump(
            {"cells": cells, "purpose": "hypothesis screen, not release qualification"},
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()

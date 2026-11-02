"""Predeclare old/new allocator and same-binary compilation gates; never overwrite."""

import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
DEST = ROOT / "configs/mei-stable-qualification-20261102"
ORDER = ("a1", "b1", "c1", "c2", "b2", "a2")


def profile(slug, cell, control, candidate, client):
    native = cell == "native"
    template = "native" if native else "b1"
    cfg = yaml.safe_load((DEST / f"{slug}-default-{template}.yaml").read_text())
    identity = control if cell.startswith("a") else candidate
    runtime = str(
        Path.home()
        / f".local/share/local-model-bench/mei-runtime/{slug}-stable-bounded-{cell}-20261103"
    )
    old_runtime = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
    argv = shlex.split(cfg["benchmark_launch_command"])
    argv[argv.index("--mei-repo") + 1] = identity["source_checkout"]
    argv[argv.index("--mei-binary") + 1] = identity["files"][0]["file"]
    argv.extend(["--memory-limit-bytes", "0"])
    cfg["benchmark_launch_command"] = shlex.join(argv).replace(old_runtime, runtime)
    unsafe = "0" if cell.startswith("c") else "1"
    cfg["required_runner_environment"].update(
        MEI_RUNTIME_BASE=runtime,
        VMLX_ENABLE_UNSAFE_COMPILE=unsafe,
        MLXPRESS_GENERATION_PROFILE="0",
        VMLX_NATIVE_MTP_PHASE_DIAG="0",
        VMLINUX_NATIVE_MTP_PHASE_DIAG="0",
    )
    cfg["mei_source_commit"] = identity["source_revision"]
    cfg["vmlx_commit"] = identity["vmlx_revision"]
    cfg["mei_release_artifact"] = {
        "source_revision": identity["source_revision"],
        "binary_sha256": identity["files"][0]["sha256"],
        "metallib_sha256": identity["files"][1]["sha256"],
        "qualification_build": True,
    }
    cfg["benchmark_status"] = (
        "Predeclared final bounded-allocator qualification: A=previous production candidate, "
        "B=new bounded allocator with compilation on, C=same new binary with compilation off. "
        "Order A1/B1/C1/C2/B2/A2; five measured decodes per context/process, ten per arm. "
        "Single-variable dependency fix plus CLI-help-only app change; no profiling or task score."
    )
    cfg["settings"] = [
        {
            "name": "allocator_comparison",
            "value": (
                "B/A changes only MLX core bounded returned-buffer admission in inference. "
                "Mei Sources differ only in dynamic named-profile CLI help. vmlx keeps the "
                "phase-flag lookup optimization; no math, model, sampler or kernel-source change. "
                "Exact executable/Metal/weight hashes are pinned. Both retain 512MiB allocator "
                "reuse and backend-auto total allocation limits; no physical wired limit changes."
            ),
        },
        {
            "name": "compilation_comparison",
            "value": (
                f"Elementwise compilation={unsafe}; C/B changes that setting on one new binary. "
                "Closed-negative graph/routed-MoE compilation stays off. All phase timers off. "
                "Greedy HTTP text/count/finish parity is required across every cell; preserve all "
                "cold/warmup/measured observations and stop for guard, completeness or parity failure."
            ),
        },
    ]
    cfg["last_updated"] = "2026-11-03"
    cfg.pop("mei_swift_acceptance", None)
    if cell in ("b1", "c1"):
        cfg["mei_swift_acceptance"] = client
    if native:
        cfg["benchmark_status"] = (
            "Full native tools/history/cache/exact65536 gate on the final bounded-allocator "
            "candidate, compilation on, normal advertised semantic output budget. No scored rows."
        )
        cfg["settings"].append(
            {
                "name": "normal_native_budget",
                "value": "Semantic probes inherit advertised maxTokens=8192; cache/context mechanics retain explicit small limits.",
            }
        )
    return cfg


def main():
    control = json.loads((PREP / "candidate-runtime.json").read_text())
    candidate = json.loads((PREP / "bounded-allocator-runtime.json").read_text())
    client = json.loads((PREP / "bounded-allocator-native-client.json").read_text())[
        "configuration"
    ]
    cells, native, declarations = [], [], []
    for slug in ("groot", "qwen", "ornith"):
        for cell in (*ORDER, "native"):
            cfg = profile(slug, cell, control, candidate, client)
            path = DEST / f"{slug}-bounded-{cell}.yaml"
            declarations.append((path, yaml.safe_dump(cfg, sort_keys=False, width=100)))
            record = {
                "model": slug,
                "cell": cell,
                "config": str(path.relative_to(ROOT)),
                "output": f"artifacts/mei-stable-{slug}-bounded-{cell}-20261103",
            }
            (native if cell == "native" else cells).append(record)
    matrix_path = PREP / "bounded-allocator-matrix.json"
    declarations.append(
        (
            matrix_path,
            json.dumps(
                {
                    "order": list(ORDER),
                    "measurements_per_context_arm": 10,
                    "cells": cells,
                    "full_native_gates": native,
                    "comparisons": [
                        "A1 versus A2 and B1 versus B2 cold determinism",
                        "B versus A bounded allocator only in inference",
                        "C versus B same new binary, elementwise compilation off versus on",
                    ],
                    "stop": "Stop and preserve for review on resource, native, completeness or greedy byte/count/finish failure.",
                },
                indent=2,
            )
            + "\n",
        )
    )
    collisions = [str(path) for path, _ in declarations if path.exists()]
    if collisions:
        raise ValueError(f"refuse existing declarations before any write: {collisions}")
    for path, content in declarations:
        with path.open("x") as stream:
            stream.write(content)


if __name__ == "__main__":
    main()

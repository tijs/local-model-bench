"""Predeclare control/candidate/default-kernel cells; refuse existing files."""

import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
DEST = ROOT / "configs/mei-stable-qualification-20261102"
CONTROL = json.loads((PREP / "control-api-runtime.json").read_text())
CANDIDATE = json.loads((PREP / "candidate-runtime.json").read_text())
NATIVE = json.loads((PREP / "candidate-native-runtime.json").read_text())
CLIENT = json.loads((PREP / "native-client-normal-budget.json").read_text())[
    "configuration"
]
ORDER = ("a1", "b1", "c1", "c2", "b2", "a2")


def profile(slug, cell):
    cfg = yaml.safe_load(
        (ROOT / f"configs/four-model-v9p10-20261102/{slug}-seed17.yaml").read_text()
    )
    identity = CONTROL if cell.startswith("a") else CANDIDATE
    unsafe = "1" if cell.startswith("c") else "0"
    old = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
    runtime = str(
        Path.home()
        / f".local/share/local-model-bench/mei-runtime/{slug}-stable-{cell}-20261102"
    )
    argv = shlex.split(cfg["benchmark_launch_command"])
    argv[argv.index("--mei-repo") + 1] = identity["source_checkout"]
    argv[argv.index("--mei-binary") + 1] = identity["files"][0]["file"]
    if "--ssm-anchor-boundaries" not in argv:
        argv.extend(["--ssm-anchor-boundaries", "0"])
    argv.extend(["--log-requests", "true"])
    cfg["benchmark_launch_command"] = shlex.join(argv).replace(old, runtime)
    cfg["required_runner_environment"].update(
        {
            "MEI_RUNTIME_BASE": runtime,
            "VMLX_ENABLE_UNSAFE_COMPILE": unsafe,
            "VMLX_QWEN35_COMPILE_DECODE_REGIONS": "0",
            "VMLX_QWEN4_EXP_COMPILE_ROUTED_MOE": "0",
            "VMLX_FUSED_GATE_UP_CACHE_LIMIT_BYTES": "0",
        }
    )
    cfg["mei_source_commit"] = identity["source_revision"]
    cfg["vmlx_commit"] = identity["vmlx_revision"]
    cfg["mei_release_artifact"] = {
        "source_revision": identity["source_revision"],
        "binary_sha256": identity["files"][0]["sha256"],
        "metallib_sha256": identity["files"][1]["sha256"],
        "qualification_build": True,
    }
    cfg["benchmark_scope"] = "mei-release-qualification-v1"
    cfg["benchmark_status"] = (
        f"Predeclared {cell}: A=API-correct control/elementwise compile off; "
        "B=phase-lookup candidate/off; C=same candidate/on. Process order A1/B1/C1/C2/B2/A2. "
        "Five observations per context/process; ten per arm/context. Diagnostic only, never a task score."
    )
    cfg["mei_qualification"] = {
        "repeats": 5,
        "loaded_tokens": 30000,
        "decode_tokens": 128,
        "status_timeout": 1,
    }
    cfg["settings"] = [
        {
            "name": "one_variable_comparisons",
            "value": "B/A isolates live phase-flag lookup; C/B isolates the existing elementwise compile setting on one candidate binary. Both share raw API fixes and exact Metal/model bytes.",
        },
        {
            "name": "compile_modes",
            "value": f"Elementwise compile={unsafe}; full-graph compiled decode and closed-negative routed-MoE regions remain off. No model weight/sampler/context/cache change between cells.",
        },
    ]
    cfg["known_gaps"] = [
        "Runtime qualification only: no household/Python score, real Peixinho app acceptance or published stable claim.",
        "HTTP byte/count/finish parity is observable; hidden sampled token-ID parity is not.",
        "Fresh process/KV does not guarantee a cold OS file cache. Repeated raw prompts may prefill again.",
    ]
    for key in list(cfg):
        if key.startswith("standin_") or key in (
            "generation_profiles",
            "python_automation",
            "reasoning_mode",
        ):
            del cfg[key]
    if cell in ("b1", "c1"):
        cfg["mei_swift_acceptance"] = CLIENT
    return cfg


def write_config(name, cfg):
    path = DEST / name
    with path.open("x") as stream:
        yaml.safe_dump(cfg, stream, sort_keys=False, width=100)
    return str(path.relative_to(ROOT))


def main():
    cells = []
    native = []
    for slug in ("groot", "qwen", "ornith"):
        for cell in ORDER:
            config = write_config(f"{slug}-{cell}.yaml", profile(slug, cell))
            cells.append(
                {
                    "model": slug,
                    "cell": cell,
                    "config": config,
                    "output": f"artifacts/mei-stable-{slug}-{cell}-20261102",
                }
            )
        cfg = profile(slug, "native")
        runtime = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
        cfg["benchmark_scope"] = "mei-native-v1"
        cfg["benchmark_status"] = (
            "Predeclared full native tools/history/cache/exact65K admission on the candidate with the public elementwise compilation setting enabled. No scored task rows."
        )
        cfg["required_runner_environment"]["VMLX_ENABLE_UNSAFE_COMPILE"] = "1"
        argv = shlex.split(cfg["benchmark_launch_command"])
        argv[argv.index("--mei-repo") + 1] = NATIVE["source_checkout"]
        cfg["benchmark_launch_command"] = shlex.join(argv)
        cfg["mei_source_commit"] = NATIVE["source_revision"]
        cfg["mei_release_artifact"]["source_revision"] = NATIVE["source_revision"]
        cfg["settings"] = [
            {
                "name": "normal_native_budget",
                "value": "Semantic checks inherit maxTokens from server status(8192); fixed small limits are reserved for cache/context mechanics. Elementwise compile enabled; graph/routed-MoE compile off.",
            },
            {
                "name": "app_source_equivalence",
                "value": NATIVE["app_source_equivalence"],
            },
        ]
        del cfg["mei_qualification"]
        assert runtime.endswith(f"{slug}-stable-native-20261102")
        config = write_config(f"{slug}-native.yaml", cfg)
        native.append(
            {
                "model": slug,
                "config": config,
                "output": f"artifacts/mei-stable-{slug}-native-20261102",
            }
        )
    with (PREP / "matrix.json").open("x") as stream:
        json.dump(
            {
                "order": list(ORDER),
                "measurements_per_context_arm": 10,
                "cells": cells,
                "full_native_gates": native,
                "comparisons": [
                    "cold A1 versus A2 determinism",
                    "B versus A lookup-only",
                    "C versus B same-binary existing compile setting",
                ],
                "stop": "Any resource, native, completeness or byte/count/finish mismatch stops the campaign for review.",
            },
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()

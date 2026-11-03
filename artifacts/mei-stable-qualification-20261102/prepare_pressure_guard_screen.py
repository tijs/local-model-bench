"""Keep the stopped Ornith profile fixed while observing the new store veto."""

import hashlib
import json
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent


def main():
    identity = json.loads((PREP / "pressure-guard-runtime.json").read_text())
    cfg = yaml.safe_load(
        (
            ROOT / "configs/mei-stable-qualification-20261102/ornith-bounded-c2.yaml"
        ).read_text()
    )
    runtime = str(
        Path.home()
        / ".local/share/local-model-bench/mei-runtime/ornith-stable-pressure-screen-20261103"
    )
    old_runtime = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
    argv = shlex.split(cfg["benchmark_launch_command"])
    argv[argv.index("--mei-repo") + 1] = identity["source_checkout"]
    argv[argv.index("--mei-binary") + 1] = identity["files"][0]["file"]
    cfg["benchmark_launch_command"] = shlex.join(argv).replace(old_runtime, runtime)
    cfg["required_runner_environment"].update(
        MEI_RUNTIME_BASE=runtime,
        VMLX_CACHE_FETCH_TRACE="1",
    )
    cfg["capacity_plan"]["host_reserve_bytes"] = 6 * 2**30
    cfg["capacity_plan"]["derivation"] = (
        "Pinned model weight/config and 65536-token hybrid-cache bound unchanged; "
        "512MiB retained prefixes,512MiB allocator allowance,2GiB workspace. "
        "Host reserve is6GiB after the live desktop footprint review. "
        "This feasibility estimate does not reserve RAM or prove full-context safety."
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
        "Diagnostic memory screen of the new optional-store host-pressure veto. "
        "Original stopped profile retained: prefill256, compilation off,FP16KV, "
        "65536context,512MiB allocator/prefix,auto total limit. Cache-fetch/store "
        "trace enabled to observe decisions; no throughput promotion or task score."
    )
    cfg["settings"] = [
        {
            "name": "memory_screen",
            "value": (
                "New host-pressure veto is the only model-runtime source change from "
                "Mei955b813/vmlx2256cc1. Store tracing is diagnostic and may affect "
                "timings. This screen is excluded from final TPS averages. No model, "
                "quantization, sampler, context or cache allowance change. All guards "
                "remain unchanged, with seven normal/flat-swap baseline samples."
            ),
        },
        {
            "name": "interpretation",
            "value": (
                "A fitting process does not establish native65536/performance/task "
                "qualification or prove optional persistence caused the earlier "
                "prefill peak. Stop and preserve any partial run before another load."
            ),
        },
    ]
    cfg["last_updated"] = "2026-11-03"
    config = (
        ROOT / "configs/mei-stable-qualification-20261102/ornith-pressure-screen.yaml"
    )
    manifest = PREP / "pressure-guard-screen.json"
    if config.exists() or manifest.exists():
        raise ValueError("refuse existing screen declarations before any write")
    control = (
        ROOT
        / "artifacts/mei-stable-ornith-bounded-a1-20261103/qualification-audit.json"
    )
    snapshot = yaml.safe_dump(cfg, sort_keys=False, width=100)
    record = {
        "config": str(config.relative_to(ROOT)),
        "config_sha256": hashlib.sha256(snapshot.encode()).hexdigest(),
        "output": "artifacts/mei-stable-ornith-pressure-screen-20261103",
        "control_reference": str(control.relative_to(ROOT)),
        "control_reference_sha256": hashlib.sha256(control.read_bytes()).hexdigest(),
        "expected_raw_requests": 14,
        "expected_measured_per_context": 5,
        "scope": "diagnostic feasibility only; exclude rates from final comparison",
        "next": "review every outcome before choosing or running further gates",
    }
    with config.open("x") as stream:
        stream.write(snapshot)
    with manifest.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()

"""Run one declared challenger seed and replay both held-out tracks."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from gemma_checkpoint import verify_or_stage
from qualify_toolspace import succeeded as toolspace_admitted

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [
    str(ROOT / "runner"),
    str(ROOT / "artifacts/mei011-comparison-preparation-20261106"),
]
from mei_provenance import verify_mei_runtime
from run_mei_acceptance import committed_native_config, probe_succeeded
from run_scored_cohort import (
    AUDIT,
    check_disk_headroom,
    check_ports,
    checkpoint_readback,
    model_process_observed,
    preserve,
    verify_frozen_method,
    write_run_review,
)

CONFIGS = ROOT / "configs/queued-models-20261107"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def run(model, seed, admission=None):
    label = f"{model}-seed{seed}"
    config = CONFIGS / f"{label}.yaml"
    output = ROOT / f"artifacts/queued-{label}-20261107"
    admission = admission or ROOT / f"artifacts/queued-{model}-native-20261107"
    cfg, _ = committed_native_config(config)
    native, native_bytes = committed_native_config(CONFIGS / f"{model}-native.yaml")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    verify_frozen_method({"method": "benchmark-v9.11.5"}, head)
    if output.exists() or (admission / "config.yaml").read_bytes() != native_bytes:
        raise ValueError(
            "require fresh score output and matching native config evidence"
        )
    if read(admission / "outcome.json")["status"] != "passed":
        raise ValueError("candidate native admission did not pass")
    gemma = model == "gemma-ram13"
    if gemma:
        if not probe_succeeded(admission, skip_context=False, skip_cache=False):
            raise ValueError("Gemma has not passed full Mei native admission")
        old = native["required_runner_environment"]["MEI_RUNTIME_BASE"]
        new = cfg["required_runner_environment"]["MEI_RUNTIME_BASE"]
        if old == new or Path(new).exists():
            raise ValueError("Gemma requires a fresh owned runtime base")
    else:
        if not toolspace_admitted(admission):
            raise ValueError("ToolSpace has not passed full native admission")
        old = new = ""
        if Path(f"/tmp/bench_{config.parent.name}_{config.stem}_server.log").exists():
            raise ValueError("stale ToolSpace server log exists")
    if (
        native["benchmark_launch_command"].replace(old, new)
        != cfg["benchmark_launch_command"]
        or native["capacity_plan"] != cfg["capacity_plan"]
        or native["resource_monitor_policy"] != cfg["resource_monitor_policy"]
        or cfg["generation_profiles"][cfg["standin_generation_profile"]]["seed"] != seed
    ):
        raise ValueError("scored profile differs from admission or seed declaration")
    check_ports()
    check_disk_headroom()
    before = verify_or_stage() if gemma else checkpoint_readback(model, cfg)
    write(HERE / f"{label}-readback.json", before)
    check_ports()
    check_disk_headroom()
    process = subprocess.run(
        [
            sys.executable,
            "runner/supervise_bench.py",
            "--config",
            str(config),
            "--output",
            str(output),
            "--deadline",
            "7200",
            "--trials",
            "1",
        ],
        cwd=ROOT,
        check=False,
    )
    outcome = read(output / "outcome.json")
    check_ports()
    if model_process_observed(cfg, output, outcome):
        if gemma:
            source = Path(new) / "logs"
            shutil.copytree(source, output / "runtime-logs")
            after = verify_or_stage()
            if after != before:
                raise ValueError("Gemma checkpoint changed during the run")
            write(output / "post-run-model-hashes.json", after | {"all_match": True})
            write(
                output / "post-run-runtime-verification.json", verify_mei_runtime(cfg)
            )
        else:
            preserve(model, config, cfg, output)
    ids = outcome.get("run_ids", {})
    if (
        process.returncode
        or outcome["returncode"] != 0
        or outcome["stop_reason"] is not None
        or any(
            len(ids.get(track, [])) != 1
            for track in ("peixinho-standin-v1", "python-automation-v1")
        )
    ):
        raise ValueError(f"no complete scored observation: {outcome}")
    if not (output / "post-run-model-hashes.json").is_file():
        raise ValueError("missing post-run provenance")
    subprocess.run(
        [sys.executable, str(AUDIT), str(output.relative_to(ROOT)), str(seed)],
        cwd=ROOT,
        check=True,
    )
    audit = read(output / "audit.json")
    if len(audit["household"]) != 12 or len(audit["python"]) != 3:
        raise ValueError("incomplete audited task coverage")
    write_run_review(output, cfg, seed, outcome, audit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("toolspace", "gemma-ram13"))
    parser.add_argument("seed", type=int, choices=(17, 29))
    parser.add_argument(
        "--admission",
        type=Path,
        help="Reviewed native output when the first attempt could not complete",
    )
    args = parser.parse_args()
    run(args.model, args.seed, args.admission)

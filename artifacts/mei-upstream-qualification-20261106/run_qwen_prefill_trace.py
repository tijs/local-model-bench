"""Run two bounded, separately guarded Qwen prefill traces."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from review_attention_selector import snapshot
from run_speed_matrix import PREP, ROOT, save_progress

sys.path.insert(0, str(ROOT / "runner"))
sys.path.insert(0, str(ROOT / "artifacts/mei011-comparison-preparation-20261106"))
from build_context_speed_cohort import committed_config, validate_resources
from qualify_mei_release import stream_observable, succeeded
from run_scored_cohort import (
    check_disk_headroom,
    check_model_store,
    check_ports,
    checkpoint_readback,
)

CONFIGS = Path("configs/mei-upstream-qualification-20261106")
PIN = PREP / "qwen-media-prefix-pre-run-model-hashes.json"
FLAGS = {"MLXPRESS_GENERATION_PROFILE": "1", "VMLX_DIAGNOSTICS_STDERR": "1"}
STATUS = "Traced prefill attribution only; not a release timing or task score."


def read(path):
    return json.loads(path.read_text())


def declarations(*, retry=False):
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    cells = []
    for name, control in (("legacy", "b2"), ("owned", "c2")):
        arm = "legacy-retry" if retry and name == "legacy" else name
        cfg = CONFIGS / f"qwen-prefill-trace-{arm}.yaml"
        control_cfg = CONFIGS / f"qwen-stream-ttft-{control}.yaml"
        raw, baseline = ((ROOT / p).read_bytes() for p in (cfg, control_cfg))
        committed_config(ROOT, str(cfg), revision, raw)
        committed_config(ROOT, str(control_cfg), revision, baseline)
        runtime = f"qwen-upstream011-prefill-trace-{arm}-20261107"
        expected = yaml.safe_load(
            baseline.decode().replace(
                f"qwen-upstream011-stream-ttft-{control}-20261107", runtime
            )
        )
        del expected["mei_clean_speed_launch"]
        expected["benchmark_status"] = STATUS
        expected["mei_qualification"]["repeats"] = 1
        expected["required_runner_environment"].update(FLAGS)
        if yaml.safe_load(raw) != expected:
            raise ValueError(
                f"{name}: diagnostic changes more than profiling or ownership"
            )
        cells.append(
            {
                "name": name,
                "config": str(cfg),
                "output": f"artifacts/mei011-qwen-prefill-trace-{arm}-20261107",
            }
        )
    return cells


def verify_stopped_attempt():
    progress = read(PREP / "qwen-prefill-trace-progress.json")
    original = declarations()[0]
    directory = ROOT / original["output"]
    outcome = read(directory / "outcome.json")
    if (
        progress["status"] != "stopped_for_review"
        or progress["current"] != original
        or progress["completed"]
        or outcome["status"] != "failed"
        or outcome["stop_reason"] != "sustained warning memory pressure"
        or read(directory / "qualification.json")["rows"]
        or not read(directory / "owned-kv-cleanup.json")["server_exited"]
    ):
        raise ValueError("retry requires the reviewed startup-only pressure stop")
    verify_saved_hashes(directory)


def verify_saved_hashes(output):
    saved = read(output / "post-run-model-hashes.json")
    if saved["all_match"] is not True or saved["files"] != [
        row | {"matches": True} for row in read(PIN)["files"]
    ]:
        raise ValueError("checkpoint hashes differ")


def examine(cell, reference):
    output, cfg, invocation = snapshot(cell)
    run = read(output / "qualification.json")
    if not succeeded(output) or any(
        stream_observable(row["response"]) != reference[row["context"]]
        for row in run["rows"]
    ):
        raise ValueError("traced stream differs from audited untraced output")
    validate_resources(output, cfg, invocation)
    log = (output / "server.log").read_text()
    marker = (
        " mmap=false " if cell["name"] == "legacy" else "mei: weight storage owned;"
    )
    rows = run["rows"]
    profiles = [
        line
        for line in log.splitlines()
        if "[MLXPressGenerationProfile] generation-end tokens=128 " in line
    ]
    if marker not in log or len(rows) != 6 or len(profiles) != len(rows):
        raise ValueError(
            "expected loader marker and one phase record per completed stream"
        )
    verify_saved_hashes(output)
    return [
        {k: row[k] for k in ("context", "phase", "repeat")} | {"profile": line}
        for row, line in zip(rows, profiles, strict=True)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--retry", action="store_true")
    args = parser.parse_args()
    cells = declarations(retry=args.retry)
    if args.retry:
        verify_stopped_attempt()
    if args.preflight:
        print(json.dumps(cells, indent=2))
        return 0
    suffix = "-retry" if args.retry else ""
    progress_path = PREP / f"qwen-prefill-trace{suffix}-progress.json"
    if progress_path.exists() or any(
        (ROOT / cell["output"]).exists() for cell in cells
    ):
        raise ValueError("inspect existing trace evidence before retrying")
    streaming = read(PREP / "qwen-stream-ttft-progress.json")
    if (
        streaming["status"] != "measurement_cells_complete"
        or len(streaming["completed"]) != 6
    ):
        raise ValueError("the untraced matrix must be terminal and complete first")
    reference = read(
        ROOT / "artifacts/mei011-qwen-stream-ttft-a1-20261107/qualification-audit.json"
    )["reference"]
    environment = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    progress = {"status": "running", "completed": [], "parent_environment": environment}
    for cell in cells:
        progress["current"] = cell
        save_progress(progress, progress_path)
        print(f"START prefill trace {cell['name']}", flush=True)
        try:
            output = ROOT / cell["output"]
            if args.retry:
                check_ports()
                check_disk_headroom()
                check_model_store()
                readback = checkpoint_readback(
                    "qwen", yaml.safe_load((ROOT / cell["config"]).read_bytes())
                )
                check_ports()
                progress.setdefault("readbacks", {})[cell["name"]] = readback
                save_progress(progress, progress_path)
            child = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "runner/qualify_mei_release.py"),
                    "--config",
                    cell["config"],
                    "--output",
                    cell["output"],
                    "--deadline",
                    "1200",
                ],
                cwd=ROOT,
                env=environment,
                check=False,
            )
            outcome = read(output / "outcome.json")
            if outcome.get("returncode") is not None:
                qualification = read(output / "qualification.json")
                if (
                    qualification.get("cleanup_error")
                    != "server process was not launched"
                ):
                    subprocess.run(
                        [
                            sys.executable,
                            str(PREP / "preserve_native.py"),
                            "--output",
                            str(output),
                            "--model-manifest",
                            str(PIN),
                        ],
                        cwd=ROOT,
                        env=environment,
                        check=True,
                    )
            if child.returncode or outcome["status"] != "passed":
                raise ValueError(f"guarded trace failed: {outcome}")
            profiles = examine(cell, reference)
            with (output / "phase-records.json").open("x") as f:
                json.dump(profiles, f, indent=2)
                f.write("\n")
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as error:
            progress.update(
                status="stopped_for_review", error=f"{type(error).__name__}: {error}"
            )
            save_progress(progress, progress_path)
            print(progress["error"], flush=True)
            return 1
        progress["completed"].append(cell)
        save_progress(progress, progress_path)
        print(f"PASS prefill trace {cell['name']}", flush=True)
    progress.update(status="observations_complete_review_pending", current=None)
    save_progress(progress, progress_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

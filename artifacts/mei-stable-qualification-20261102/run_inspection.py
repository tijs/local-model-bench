"""Guarded, explicitly profiled diagnostics on inspection-only runtime copies."""

import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

import yaml
from run_matrix import PREP, ROOT, audit, save_progress

sys.path.insert(0, str(ROOT / "runner"))
from qualify_mei_release import request_json


def swift_snapshot_valid(returncode, stdout, stderr):
    return (
        returncode == 0
        and not stderr.strip()
        and "TASKS" in stdout
        and "THREADS" in stdout
        and "enqueuePriority=" in stdout
    )


def capture(cfg, output, repeat):
    record = {"after_loaded_repeat": repeat, "started_epoch": time.time()}
    try:
        runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
        pid = int((runtime / "server.pid").read_text().strip())
        argv = shlex.split(cfg["benchmark_launch_command"])
        expected = Path(argv[argv.index("--mei-binary") + 1]).resolve()
        actual = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "comm="], text=True
        ).strip()
        if Path(actual).resolve() != expected:
            raise ValueError("inspection target does not match the owned runtime")
        base = cfg["benchmark_endpoint"].rstrip("/")
        record.update(
            pid=pid,
            binary=str(expected),
            status_before=request_json(base + "/mei/status", timeout=2),
        )
        name = f"inspection-{repeat}"
        done = subprocess.run(
            ["xcrun", "swift-inspect", "dump-concurrency", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        for suffix, value in (("stdout", done.stdout), ("stderr", done.stderr)):
            with (output / f"{name}-tasks.{suffix}").open("x") as stream:
                stream.write(value)
        record["swift_inspect"] = {
            "returncode": done.returncode,
            "passed": swift_snapshot_valid(done.returncode, done.stdout, done.stderr),
            "stdout_bytes": len(done.stdout.encode()),
        }
        sample = output / f"{name}-sample.txt"
        sampled = subprocess.run(
            ["sample", str(pid), "1", "-file", str(sample)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        with (output / f"{name}-sample.stderr").open("x") as stream:
            stream.write(sampled.stderr)
        record["sample"] = {
            "returncode": sampled.returncode,
            "passed": sampled.returncode == 0
            and sample.exists()
            and "Thread_" in sample.read_text(),
        }
        record["status_after"] = request_json(base + "/mei/status", timeout=2)
        record["passed"] = (
            record["status_before"].get("scheduler", {}).get("activeGenerations", 0) > 0
            and record["swift_inspect"]["passed"]
            and record["sample"]["passed"]
        )
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        subprocess.SubprocessError,
    ) as exc:
        record.update(passed=False, error=f"{type(exc).__name__}: {exc}")
    record["finished_epoch"] = time.time()
    return record


def main():
    matrix = json.loads((PREP / "inspection-screen.json").read_text())
    destination = PREP / "inspection-progress.json"
    if destination.exists():
        raise ValueError("inspect the prior campaign; do not restart existing evidence")
    progress = {
        "status": "running",
        "completed": [],
        "current": None,
        "started_epoch": time.time(),
    }
    save_progress(progress, destination)
    baseline = None
    for cell in matrix["cells"]:
        progress["current"] = cell
        save_progress(progress, destination)
        print(f"START inspection {cell['cell']}", flush=True)
        output = ROOT / cell["output"]
        cfg = yaml.safe_load((ROOT / cell["config"]).read_text())
        captures = []
        observed = set()
        with (PREP / f"inspection-{cell['cell']}-supervisor.log").open("x") as log:
            run = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "runner/qualify_mei_release.py"),
                    "--config",
                    str(ROOT / cell["config"]),
                    "--output",
                    str(output),
                    "--deadline",
                    "1200",
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            while run.poll() is None:
                try:
                    rows = json.loads((output / "qualification.json").read_text())[
                        "rows"
                    ]
                except (OSError, ValueError, KeyError):
                    rows = []
                for repeat in (2, 4):
                    if repeat not in observed and any(
                        r["phase"] == "measured"
                        and r["context"] == "loaded"
                        and r["repeat"] == repeat
                        for r in rows
                    ):
                        observed.add(repeat)
                        time.sleep(0.3)
                        captures.append(capture(cfg, output, repeat))
                        (output / "inspection-captures.json").write_text(
                            json.dumps(captures, indent=2) + "\n"
                        )
                        print(
                            f"CAPTURE {cell['cell']} {repeat}: {captures[-1]['passed']}",
                            flush=True,
                        )
                time.sleep(0.25)
            returncode = run.wait()
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(PREP / "preserve_run.py"),
                    "--output",
                    str(output),
                    "--model-manifest",
                    str(PREP / "qwen-pre-run-model-hashes.json"),
                ],
                cwd=ROOT,
                check=True,
            )
            if (
                returncode
                or len(captures) != 2
                or not all(c["passed"] for c in captures)
            ):
                raise ValueError(
                    "guarded diagnostic or required inspection capture failed"
                )
            checked = audit(output, baseline)
            with (output / "qualification-audit.json").open("x") as stream:
                json.dump(checked, stream, indent=2)
                stream.write("\n")
            baseline = checked["reference"] if baseline is None else baseline
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            progress.update(
                status="stopped_for_review", error=f"{type(exc).__name__}: {exc}"
            )
            save_progress(progress, destination)
            print(progress["error"], flush=True)
            return 1
        progress["completed"].append(
            cell | {"profiled_medians": checked["median_decode_tps"]}
        )
        save_progress(progress, destination)
        print(
            f"COMPLETE inspection {cell['cell']}: {checked['median_decode_tps']}",
            flush=True,
        )
    progress.update(
        status="inspection_cells_complete", current=None, finished_epoch=time.time()
    )
    save_progress(progress, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

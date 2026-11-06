"""Run the predeclared Groot phase diagnostics; never rank profiled timings."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def validate_matrix(matrix, mirrored=False):
    suffix = "-mirror" if mirrored else ""
    expected = [
        {
            "arm": arm,
            "config": f"configs/mei-upstream-qualification-20261106/groot-phase{suffix}-{arm}.yaml",
            "output": f"artifacts/mei011-groot-phase{suffix}-{arm}-20261106",
        }
        for arm in ("a", "b")
    ]
    if matrix["cells"] != expected:
        raise ValueError("requires both exact predeclared diagnostic arms")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirrored", action="store_true")
    args = parser.parse_args()
    screen = "groot-phase-mirrored-screen" if args.mirrored else "groot-phase-screen"
    progress_path = PREP / f"{screen}-progress.json"
    if progress_path.exists():
        raise ValueError(
            "inspect the existing process/outcome; do not restart this screen"
        )
    matrix = json.loads((PREP / f"{screen}.json").read_text())
    validate_matrix(matrix, args.mirrored)
    baseline = json.loads((ROOT / matrix["control_reference"]).read_text())["reference"]
    progress = {"status": "running", "started_epoch": time.time(), "completed": []}
    environment = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    progress["parent_environment"] = environment
    save(progress_path, progress)
    for cell in matrix["cells"]:
        progress["current"] = cell
        save(progress_path, progress)
        print(f"START diagnostic {cell['arm']}", flush=True)
        output = ROOT / cell["output"]
        run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "runner/qualify_mei_release.py"),
                "--config",
                str(ROOT / cell["config"]),
                "--output",
                str(output),
                "--deadline",
                "1800",
            ],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        try:
            outcome = json.loads((output / "outcome.json").read_text())
            if outcome.get("returncode") is not None:
                subprocess.run(
                    [
                        sys.executable,
                        str(PREP / "preserve_native.py"),
                        "--output",
                        str(output),
                        "--model-manifest",
                        str(ROOT / matrix["model_manifest"]),
                    ],
                    cwd=ROOT,
                    env=environment,
                    check=True,
                )
            if run.returncode or outcome.get("status") != "passed":
                raise ValueError(f"guarded diagnostic failed: {outcome}")
            result = json.loads((output / "qualification.json").read_text())
            expected = {
                (c, p, r)
                for c in ("short", "loaded")
                for p, r in (
                    ("cold" if c == "short" else "cold_status", 0),
                    ("warmup", 0),
                    ("measured", 1),
                )
            }
            rows = result["rows"]
            if (
                result["status"] != "passed"
                or len(rows) != 6
                or {(r["context"], r["phase"], r["repeat"]) for r in rows} != expected
                or any(r["observable"] != baseline[r["context"]] for r in rows)
            ):
                raise ValueError(
                    "diagnostic coverage/observable parity differs from control"
                )
            profiles = [
                line
                for line in (output / "server.log").read_text().splitlines()
                if "[MLXPressGenerationProfile] generation-end tokens=128 " in line
            ]
            if len(profiles) != 6:
                raise ValueError("requires six actual generation phase records")
            with (output / "phase-records.json").open("x") as stream:
                json.dump(
                    {
                        "scope": "Diagnostic only; nested phases are not additive",
                        "rows": [
                            {
                                "context": row["context"],
                                "phase": row["phase"],
                                "repeat": row["repeat"],
                                "profile": line,
                            }
                            for row, line in zip(rows, profiles, strict=True)
                        ],
                    },
                    stream,
                    indent=2,
                )
                stream.write("\n")
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as exc:
            progress.update(
                status="stopped_for_review", error=f"{type(exc).__name__}: {exc}"
            )
            save(progress_path, progress)
            print(progress["error"], flush=True)
            return 1
        progress["completed"].append(cell)
        save(progress_path, progress)
        print(f"PASS diagnostic {cell['arm']}", flush=True)
    progress.update(
        status="observations_complete_review_pending",
        current=None,
        finished_epoch=time.time(),
    )
    save(progress_path, progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

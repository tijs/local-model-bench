"""Fresh native gates followed by untraced ABBA; halt on any partial/failure."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runner"))
from mei_clean_speed import clean_environment
from qualify_mei_release import qualification_settings
from run_mei_acceptance import committed_native_config, validate_owned_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--campaign", choices=("batched", "apple-main"), default="batched")
    args = parser.parse_args()
    native = json.loads((PREP / f"{args.campaign}-native-campaign.json").read_text())
    matrix = json.loads((PREP / f"{args.campaign}-speed-matrix.json").read_text())
    for name in (
        f"{args.campaign}-native-campaign-progress.json",
        f"{args.campaign}-speed-progress.json",
    ):
        if (PREP / name).exists():
            raise ValueError("inspect the existing campaign; do not restart it")
    for cell in native["cells"] + matrix["cells"]:
        if (ROOT / cell["output"]).exists():
            raise ValueError(f"refuse existing output: {cell['output']}")
        cfg, _ = committed_native_config(ROOT / cell["config"])
        validate_owned_config(cfg)
        if cell in matrix["cells"]:
            if cfg["benchmark_scope"] != "mei-release-qualification-v1":
                raise ValueError("speed qualification requires its separate scope")
            qualification_settings(cfg)
            clean_environment(cfg)
    if args.preflight_only:
        print("All fifteen committed profiles pass configuration preflight")
        return 0
    environment = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    commands = [
        [str(PREP / "run_batched_native_campaign.py"), "--campaign", args.campaign],
        [
            str(PREP / "run_speed_matrix.py"),
            "--matrix",
            str(PREP / f"{args.campaign}-speed-matrix.json"),
            "--progress",
            str(PREP / f"{args.campaign}-speed-progress.json"),
        ],
        [
            str(PREP / "summarize_speed_matrix.py"),
            "--matrix",
            str(PREP / f"{args.campaign}-speed-matrix.json"),
            "--progress",
            str(PREP / f"{args.campaign}-speed-progress.json"),
            "--output",
            str(PREP / f"{args.campaign}-speed-summary.json"),
        ],
    ]
    for index, command in enumerate(commands):
        result = subprocess.run(
            [sys.executable, *command], cwd=ROOT, env=environment, check=False
        )
        if result.returncode:
            return result.returncode
        if index == 0:
            progress = json.loads(
                (PREP / f"{args.campaign}-native-campaign-progress.json").read_text()
            )
            if (
                progress["status"] != "passed"
                or progress["current"] is not None
                or len(progress["completed"]) != 3
                or {cell["model"] for cell in progress["completed"]}
                != {"qwen", "ornith", "groot"}
                or any(
                    cell["outcome"]["full_native_admission"] is not True
                    for cell in progress["completed"]
                )
            ):
                raise ValueError(
                    "all three full native gates must pass before speed qualification"
                )
    print("Observations preserved; manual performance/release review remains required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

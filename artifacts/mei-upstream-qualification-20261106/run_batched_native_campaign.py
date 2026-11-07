"""Sequential full native gates; halt and preserve any failed or partial cell."""

import argparse
import json
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "runner"))
from run_mei_acceptance import (
    committed_native_config,
    probe_succeeded,
    validate_owned_config,
)

active = None


def interrupt(signum, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if active is not None and active.poll() is None:
        active.send_signal(signal.SIGINT)
    raise KeyboardInterrupt


def save(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(path)


def main():
    global active
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=("batched", "apple-main"), default="batched")
    args = parser.parse_args()
    progress = PREP / f"{args.campaign}-native-campaign-progress.json"
    if progress.exists():
        raise ValueError(
            "inspect the existing campaign; never restart a live or interrupted run"
        )
    cells = json.loads((PREP / f"{args.campaign}-native-campaign.json").read_text())["cells"]
    for cell in cells:
        cfg, _ = committed_native_config(ROOT / cell["config"])
        validate_owned_config(cfg)
        if (ROOT / cell["output"]).exists():
            raise ValueError(f"refuse existing output: {cell['output']}")
    state = {"status": "running", "completed": [], "current": None}
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    save(progress, state)
    try:
        for cell in cells:
            state["current"] = cell
            save(progress, state)
            print(f"START {cell['model']}", flush=True)
            active = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "runner/run_mei_acceptance.py"),
                    "--config",
                    str(ROOT / cell["config"]),
                    "--output",
                    str(ROOT / cell["output"]),
                    "--deadline",
                    "3600",
                ],
                cwd=ROOT,
            )
            code = active.wait()
            output = ROOT / cell["output"]
            outcome = json.loads((output / "outcome.json").read_text())
            if outcome.get("returncode") is None:
                raise ValueError(
                    "native child is not terminal; no preservation or next model"
                )
            subprocess.run(
                [
                    sys.executable,
                    str(PREP / "preserve_native.py"),
                    "--output",
                    str(output),
                    "--model-manifest",
                    str(ROOT / cell["model_manifest"]),
                ],
                cwd=ROOT,
                check=True,
            )
            if (
                code
                or outcome.get("full_native_admission") is not True
                or not probe_succeeded(output, skip_context=False, skip_cache=False)
            ):
                raise ValueError(
                    f"{cell['model']} incomplete/failed; review before any retry or next model"
                )
            state["completed"].append(cell | {"outcome": outcome})
            save(progress, state)
            print(f"PASS {cell['model']}: full native admission", flush=True)
        state.update(status="passed", current=None)
        save(progress, state)
        return 0
    except BaseException as exc:
        if active is not None and active.poll() is None:
            active.send_signal(signal.SIGINT)
            active.wait(timeout=30)
        state.update(status="stopped_for_review", error=f"{type(exc).__name__}: {exc}")
        save(progress, state)
        raise


if __name__ == "__main__":
    raise SystemExit(main())

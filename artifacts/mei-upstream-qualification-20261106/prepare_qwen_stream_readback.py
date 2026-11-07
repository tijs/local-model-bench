"""Verify the pinned Qwen checkpoint before the first streaming timing cell."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[1]
RECEIPT = PREP / "qwen-stream-ttft-initial-readback.json"
sys.path.insert(0, str(PREP.parent / "mei011-comparison-preparation-20261106"))

from run_scored_cohort import (
    PROGRESS,
    check_disk_headroom,
    check_model_store,
    check_ports,
    checkpoint_readback,
    committed_config,
    read,
    write,
)


def main():
    scored = read(PROGRESS)
    if (
        scored["status"] != "complete"
        or scored["current"] is not None
        or len(scored["completed"]) != 8
    ):
        raise ValueError("wait for the eight scored runs to finish")
    if RECEIPT.exists() or (PREP / "qwen-stream-ttft-progress.json").exists():
        raise ValueError("inspect the existing streaming readback or campaign first")
    matrix = PREP / "qwen-stream-ttft-matrix.json"
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    committed_config(ROOT, str(matrix.relative_to(ROOT)), head, matrix.read_bytes())
    cells = read(matrix)["cells"]
    first = cells[0]
    if (first["model"], first["cell"]) != ("qwen", "a1"):
        raise ValueError("expected Qwen A1 as the first timing cell")
    raw = (ROOT / first["config"]).read_bytes()
    committed_config(ROOT, first["config"], head, raw)
    check_ports()
    check_disk_headroom()
    check_model_store()
    result = checkpoint_readback("qwen", yaml.safe_load(raw))
    check_ports()
    write(RECEIPT, {"config": first["config"], **result})
    print(
        json.dumps(
            {
                "verified_files": len(result["files"]),
                "seconds": result["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()

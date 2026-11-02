"""Render real candidate-only qualification data as a clearly marked layout preview."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import yaml
from run_matrix import PREP, ROOT, audit

sys.path.insert(0, str(ROOT / "runner"))
from build_four_model_summary import COLORS
from context_speed_summary import (
    SpeedObservation,
    SpeedProfile,
    aggregate_context_speeds,
    context_speed_figure,
)


def main(destination: Path | None = None):
    destination = destination or PREP / "context-speed-layout-preview"
    if any(destination.with_suffix(ext).exists() for ext in (".png", ".svg", ".json")):
        raise FileExistsError(
            "preview already exists; preserve its images and evidence together"
        )
    summary = json.loads((PREP / "default-summary.json").read_text())
    labels = {"groot": "Groot", "qwen": "Base Qwen3.6", "ornith": "Ornith1.5"}
    profiles = []
    observations = []
    for slug, label in labels.items():
        cells = [
            c
            for c in summary["cells"]
            if c["model"] == slug and c["cell"] in ("b1", "b2")
        ]
        if [c["cell"] for c in cells] != ["b1", "b2"]:
            raise ValueError("require both predeclared candidate processes")
        cfg = yaml.safe_load((ROOT / cells[0]["config"]).read_text())
        runtime = cfg["mei_release_artifact"]["binary_sha256"]
        if (
            runtime
            != "3497bfda0b417f2d4ce3e0e14c3b2b53d8645422a5e07c8ceeba2a9a85968702"
        ):
            raise ValueError("preview must retain the measured candidate")
        profiles.append(
            SpeedProfile(
                label,
                "mei",
                runtime,
                cfg["source_revision"],
                tuple(c["output"] for c in cells),
                17,
                30000,
            )
        )
        for cell in cells:
            output = ROOT / cell["output"]
            if audit(output, cell["audit"]["reference"]) != cell["audit"]:
                raise ValueError("audit no longer matches raw evidence")
            other = yaml.safe_load((output / "config.yaml").read_text())
            result = json.loads((output / "qualification.json").read_text())
            for row in result["rows"]:
                if row["phase"] != "measured":
                    continue
                observations.append(
                    SpeedObservation(
                        label,
                        cell["output"],
                        other["mei_release_artifact"]["binary_sha256"],
                        other["source_revision"],
                        "long" if row["context"] == "loaded" else "short",
                        row["repeat"],
                        row["observable"]["prompt_tokens"],
                        row["observable"]["completion_tokens"],
                        row["decode_tps"],
                    )
                )
    points = aggregate_context_speeds(profiles, observations)
    context_speed_figure(
        points,
        destination,
        title="Layout preview · unreleased Mei qualification only",
        provenance="2 processes × 5 measured decodes/context; 128 output tokens; candidate 3497bfda, 512 MiB cache.\nQwen/Ornith performance under review. Logics not measured here. No task scores or stable-release claim.",
        colors=COLORS,
    )
    data = {
        "scope": "layout preview of candidate-only qualification;not the four-model task summary",
        "averages": [asdict(p) for p in points],
        "observations": [asdict(p) for p in observations],
    }
    with destination.with_suffix(".json").open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Fresh destination stem; existing outputs are refused",
    )
    main(parser.parse_args().output)

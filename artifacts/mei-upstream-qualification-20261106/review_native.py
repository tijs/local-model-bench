"""Supplement a terminal, preserved native attempt with bounded resource review."""

import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    outcome = json.loads((output / "outcome.json").read_text())
    hashes = json.loads((output / "post-run-model-hashes.json").read_text())
    cleanup = json.loads((output / "owned-kv-cleanup.json").read_text())
    if (
        outcome.get("returncode") is None
        or hashes.get("all_match") is not True
        or cleanup.get("server_exited") is not True
    ):
        raise ValueError("requires a terminal, preserved, rehashed attempt")
    rows = [
        json.loads(x) for x in (output / "resources.jsonl").read_text().splitlines()
    ]
    processes = [
        p for r in rows for p in r["owned_processes"] if p["comm"].endswith("/mei")
    ]
    pids = {p["pid"] for p in processes}
    if len(pids) != 1:
        raise ValueError("requires exactly one observed owned Mei process")
    with (output / "loader-unified-log.jsonl").open("x") as stream:
        subprocess.run(
            [
                "/usr/bin/log",
                "show",
                "--last",
                "30m",
                "--info",
                "--style",
                "ndjson",
                "--predicate",
                f'processIdentifier == {pids.pop()} AND subsystem == "vmlx" AND category == "LoadWeights"',
            ],
            stdout=stream,
            check=True,
        )
    summary = {
        "outcome": outcome,
        "pressure_levels": sorted({r["kernel_pressure_level"] for r in rows}),
        "warning_samples": sum(r["kernel_pressure_level"] == 2 for r in rows),
        "critical_samples": sum(
            r["kernel_pressure_level"] >= 4
            for r in rows
            if r["kernel_pressure_level"] is not None
        ),
        "swap_baseline_mib": rows[0]["swap_used_mib"],
        "swap_peak_mib": max(r["swap_used_mib"] for r in rows),
        "swap_final_mib": rows[-1]["swap_used_mib"],
        "peak_mei_phys_footprint_bytes": max(
            p["phys_footprint_bytes"] for p in processes
        ),
        "model_files_rehashed_unchanged": len(hashes["files"]),
        "scope": "Native correctness/admission; no scored-task or speed claim. Other attempts remain separate.",
    }
    with (output / "review-summary.json").open("x") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

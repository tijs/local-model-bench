"""Read-only status responsiveness observations for one owned native cell."""

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import yaml


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    cfg = yaml.safe_load((output / "config.yaml").read_text())
    expected = cfg["orchestration"]["served_model_id"]
    deadline = time.monotonic() + 600
    pid = None
    while time.monotonic() < deadline and pid is None:
        resource = output / "resources.jsonl"
        if resource.exists():
            for row in reversed(resource.read_text().splitlines()):
                processes = [
                    p
                    for p in json.loads(row)["owned_processes"]
                    if p["comm"].endswith("/mei")
                ]
                if processes:
                    pid = processes[0]["pid"]
                    break
        if (output / "outcome.json").exists():
            raise ValueError(
                "native cell is already terminal; do not relabel a later listener"
            )
        if pid is None:
            time.sleep(1)
    if pid is None:
        raise ValueError("no live owned Mei process observed")
    rows = []
    saw_long_prefill = False
    runtime = Path(cfg["required_runner_environment"]["MEI_RUNTIME_BASE"])
    with (output / "passive-status-samples.jsonl").open("x", buffering=1) as stream:
        while alive(pid) and time.monotonic() < deadline:
            start = time.monotonic()
            row = {"epoch": time.time(), "pid": pid}
            try:
                with urllib.request.urlopen(
                    cfg["benchmark_endpoint"].rstrip("/") + "/mei/status", timeout=1
                ) as response:
                    status = json.load(response)
                row.update(
                    ok=status.get("status") == "ok" and status.get("model") == expected,
                    model=status.get("model"),
                    active_generations=status.get("scheduler", {}).get(
                        "activeGenerations"
                    ),
                )
            except (OSError, ValueError) as exc:
                if not alive(pid):
                    break  # the owned runner stopped its server, not a live endpoint timeout
                row.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            row["elapsed_seconds"] = time.monotonic() - start
            rows.append(row)
            stream.write(json.dumps(row) + "\n")
            log = runtime / "logs/server.log"
            saw_long_prefill = saw_long_prefill or (
                log.exists() and "total=65536" in log.read_text()
            )
            time.sleep(2)
    summary = {
        "pid": pid,
        "model": expected,
        "samples": len(rows),
        "all_ok": bool(rows) and all(r["ok"] for r in rows),
        "active_samples": sum((r.get("active_generations") or 0) > 0 for r in rows),
        "max_elapsed_seconds": max((r["elapsed_seconds"] for r in rows), default=None),
        "saw_65536_prefill": saw_long_prefill,
        "owned_process_exited": not alive(pid),
        "scope": "Passive status GETs during the existing native workload, no inference changes; not speed measurements.",
    }
    with (output / "passive-status-review.json").open("x") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    return (
        0
        if summary["all_ok"]
        and summary["active_samples"]
        and saw_long_prefill
        and summary["owned_process_exited"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

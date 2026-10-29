"""Compare explicitly selected full runs on one released benchmark method."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from automation_tasks import TASK_IDS as PYTHON_IDS
from bench_common import REPO
from standin_tasks import TASK_IDS as HOUSEHOLD_IDS

TRACKS = {
    "household": (
        "standin",
        "peixinho-standin-v1",
        HOUSEHOLD_IDS,
        {
            "run_standin_suite.py",
            "peixinho_standin.py",
            "peixinho_standin.json",
            "standin_domain.py",
            "standin_tasks.py",
            "build_standin_report.py",
            "run_prompt.py",
            "bench_common.py",
            "mei_provenance.py",
            "llama_provenance.py",
            "owned_process.py",
        },
    ),
    "python": (
        "automation",
        "python-automation-v1",
        PYTHON_IDS,
        {
            "run_automation_suite.py",
            "automation_tasks.py",
            "automation_sandbox.py",
            "run_standin_suite.py",
            "run_prompt.py",
            "standin_domain.py",
            "bench_common.py",
            "mei_provenance.py",
            "llama_provenance.py",
            "owned_process.py",
            "build_automation_report.py",
            "python_automation.py",
        },
    ),
}
Reader = Callable[[str, str], bytes]


def source_path(name: str) -> str:
    if name in ("peixinho_standin.py", "python_automation.py"):
        return "checks/" + name
    if name == "peixinho_standin.json":
        return "tasks/" + name
    return "runner/" + name


def git_reader(root: Path, commit: str, name: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)


def relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("campaign paths must stay inside repository")
    return path


def track_result(
    root: Path,
    selection: dict[str, Any],
    campaign: dict[str, Any],
    track: str,
    reader: Reader,
) -> dict[str, Any] | None:
    run_id = selection.get(track + "_run")
    if run_id is None:
        return None
    if not isinstance(run_id, str) or not re.fullmatch(
        r"\d{8}T\d{6}Z-[0-9a-f]{8}", run_id
    ):
        raise ValueError("invalid selected run identity")
    folder, scope, task_ids, version_names = TRACKS[track]
    directory = root / "results" / folder / "runs" / run_id
    manifest = json.loads((directory / "manifest.json").read_text())
    config_bytes = (directory / "config.yaml").read_bytes()
    config_path = relative_path(selection["config"])
    released_config = reader(campaign["release_commit"], config_path.as_posix())
    config = yaml.safe_load(released_config)
    if (
        config_bytes != released_config
        or hashlib.sha256(config_bytes).hexdigest()[:12] != manifest["config_hash"]
    ):
        raise ValueError("run does not use the selected released config bytes")
    if (
        manifest.get("run_id") != run_id
        or manifest.get("benchmark_scope") != scope
        or manifest.get("model") != selection["model"]
        or manifest.get("inference_engine") != selection["engine"]
        or config.get("model") != selection["model"]
        or config.get("inference_engine") != selection["engine"]
        or config.get("standin_partition") != campaign["partition"]
        or config.get("python_automation") is not True
        or manifest.get("partition") != campaign["partition"]
        or manifest.get("test_only")
    ):
        raise ValueError(
            "selected run identity/scope/model/partition is not scored evidence"
        )
    if set(manifest["versions"]) != version_names:
        raise ValueError("run method fingerprint has missing or unexpected helpers")
    if not re.fullmatch("[0-9a-f]{12,40}", manifest.get("runner_git_sha", "")):
        raise ValueError("run source must be a clean committed revision")
    for name, actual in manifest["versions"].items():
        expected = hashlib.sha256(
            reader(campaign["release_commit"], source_path(name))
        ).hexdigest()
        if actual != expected:
            raise ValueError(f"run method differs from release: {name}")
        if (
            actual
            != hashlib.sha256(
                reader(manifest["runner_git_sha"], source_path(name))
            ).hexdigest()
        ):
            raise ValueError(f"run helper differs from its committed source: {name}")
    # Parent lifecycle/launch code is also part of the method, even though the
    # per-track manifests fingerprint their own execution helpers separately.
    parent = reader(campaign["release_commit"], "runner/run_bench.py")
    if reader(manifest["runner_git_sha"], "runner/run_bench.py") != parent:
        raise ValueError("run parent lifecycle differs from released benchmark")
    rows = [
        json.loads(line)
        for line in (root / "results" / folder / "log.jsonl").read_text().splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if r["run_id"] == run_id]
    expected = Counter(
        {
            (tid, trial): 1
            for tid in task_ids
            for trial in range(1, campaign["trials"] + 1)
        }
    )
    planned = Counter((p["task_id"], p["trial"]) for p in manifest["planned"])
    actual = Counter((p["task_id"], p["trial"]) for p in rows)
    if (
        planned != expected
        or any(n != 1 or key not in expected for key, n in actual.items())
        or manifest["rows_completed"] != len(rows)
    ):
        raise ValueError("planned/executed task coverage is inconsistent")
    for row in rows:
        fields = (
            "benchmark_scope",
            "model",
            "config_hash",
            "runner_git_sha",
            "versions",
            "partition",
            "generation_profile",
            "runtime_identity",
            "cache_policy",
            "supervision_id",
        )
        if any(row.get(k) != manifest.get(k) for k in fields):
            raise ValueError("row/manifest provenance mismatch")
        if track == "python" and row.get("isolation") != manifest.get("isolation"):
            raise ValueError("Python isolation provenance mismatch")
        if not isinstance(row.get("pass"), bool):
            raise TypeError("invalid task grade")
        artifact = json.loads((root / relative_path(row["result_path"])).read_text())
        if (
            artifact["grade"]["pass"] != row["pass"]
            or artifact["grade"]["failed_checks"] != row["failed_checks"]
            or any(
                artifact.get(key) != row.get(key)
                for key in ("error", "failure_class", "wall_seconds")
            )
        ):
            raise ValueError("row/task artifact outcome mismatch")
        counters = ["invalid_tool_calls"] + (
            ["critical_safety_failure", "unsafe_attempts", "unauthorized_mutations"]
            if track == "household"
            else []
        )
        for key in counters:
            if (
                key not in row
                or key not in artifact["grade"]
                or type(row[key]) is not type(artifact["grade"][key])
                or row[key] != artifact["grade"][key]
            ):
                raise ValueError(f"row/task artifact grade counter mismatch: {key}")
            value = row[key]
            if key == "critical_safety_failure":
                if not isinstance(value, bool):
                    raise TypeError("critical counter must be boolean")
            elif not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("grade count must be a nonnegative integer")
        if bool(row.get("harness_error")) != (
            artifact.get("failure_class") in ("harness_error", "interrupted")
        ):
            raise ValueError("row/task artifact harness classification mismatch")
    complete = (
        manifest["status"] == "completed"
        and actual == expected
        and not any(r.get("harness_error") for r in rows)
    )
    return {
        "run_id": run_id,
        "supervision_id": manifest.get("supervision_id"),
        "runtime_identity": manifest.get("runtime_identity"),
        "config_hash": manifest["config_hash"],
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "complete": complete,
        "status": manifest["status"],
        "rows": rows,
        "passed": sum(r["pass"] for r in rows),
        "expected": len(expected),
        "executed": len(rows),
        "critical": sum(bool(r.get("critical_safety_failure")) for r in rows),
        "invalid": sum(r.get("invalid_tool_calls", 0) for r in rows),
        "budget": sum(
            r.get("failure_class") in ("truncation", "turn_limit", "task_budget")
            for r in rows
        ),
        "task_seconds": sum(r["wall_seconds"] for r in rows),
    }


def resources(
    root: Path,
    selection: dict[str, Any],
    campaign: dict[str, Any],
    reader: Reader,
    tracks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not selection.get("supervision"):
        return None
    directory = root / relative_path(selection["supervision"])
    invocation = json.loads((directory / "invocation.json").read_text())
    argv = invocation["argv"]
    if (
        "--config" not in argv
        or argv[argv.index("--config") + 1] != selection["config"]
    ):
        raise ValueError("resource supervision belongs to a different config")
    outcome = json.loads((directory / "outcome.json").read_text())
    identifier = invocation.get("supervision_id")
    if (
        not isinstance(identifier, str)
        or not re.fullmatch("[0-9a-f]{32}", identifier)
        or outcome.get("supervision_id") != identifier
        or any(track.get("supervision_id") != identifier for track in tracks)
    ):
        raise ValueError("resource supervision identity does not match selected runs")
    content = reader(campaign["release_commit"], selection["config"])
    if (
        (directory / "config.yaml").read_bytes() != content
        or invocation.get("config_sha256") != hashlib.sha256(content).hexdigest()
        or any(
            track["config_hash"] != hashlib.sha256(content).hexdigest()[:12]
            for track in tracks
        )
    ):
        raise ValueError("resource supervision config bytes/hash mismatch")
    expected_ids = {
        scope: [selection[key + "_run"]] if selection.get(key + "_run") else []
        for key, (_, scope, _, _) in TRACKS.items()
    }
    if outcome.get("run_ids") != expected_ids:
        raise ValueError("resource supervision registered different runs")
    methods = invocation.get("supervisor_versions", {})
    if not re.fullmatch("[0-9a-f]{12,40}", invocation.get("supervisor_git_sha", "")):
        raise ValueError("supervisor source must be a clean committed revision")
    if set(methods) != {
        "supervise_bench.py",
        "owned_process.py",
        "bench_common.py",
        "run_standin_suite.py",
    }:
        raise ValueError("resource supervisor method fingerprint missing")
    for name, actual in methods.items():
        if (
            actual
            != hashlib.sha256(
                reader(campaign["release_commit"], "runner/" + name)
            ).hexdigest()
            or actual
            != hashlib.sha256(
                reader(invocation["supervisor_git_sha"], "runner/" + name)
            ).hexdigest()
        ):
            raise ValueError("resource supervisor differs from released method")
    samples = (
        [
            json.loads(line)
            for line in (directory / "resources.jsonl").read_text().splitlines()
            if line.strip()
        ]
        if (directory / "resources.jsonl").exists()
        else [invocation["initial"]]
    )
    from datetime import datetime

    total = (
        datetime.fromisoformat(outcome["time"])
        - datetime.fromisoformat(invocation["initial"]["time"])
    ).total_seconds()
    start = datetime.fromisoformat(invocation["initial"]["time"]).timestamp()
    finish = datetime.fromisoformat(outcome["time"]).timestamp()
    if total < 0 or any(
        not isinstance(track["started_at"], (int, float))
        or not isinstance(track["finished_at"], (int, float))
        or not start <= track["started_at"] <= track["finished_at"] <= finish
        for track in tracks
    ):
        raise ValueError("selected run timing is outside resource supervision")
    initial = invocation["initial"]["swap_used_mib"]
    return {
        "seconds": total,
        "normal": all(s["kernel_pressure_level"] == 1 for s in samples),
        "minimum_free_percent": min(s["free_percent"] for s in samples),
        "swap_growth_mib": max(s["swap_used_mib"] for s in samples) - initial,
        "completed": outcome["returncode"] == 0 and outcome["stop_reason"] is None,
    }


def render_campaign(
    root: Path, campaign: dict[str, Any], reader: Reader | None = None
) -> str:
    if not re.fullmatch("[0-9a-f]{40}", campaign.get("release_commit", "")):
        raise ValueError("campaign requires exact release commit")
    if (
        campaign.get("partition") != "heldout"
        or not isinstance(campaign.get("trials"), int)
        or isinstance(campaign["trials"], bool)
        or not 1 <= campaign["trials"] <= 20
    ):
        raise ValueError(
            "final comparison requires heldout partition and bounded trials"
        )
    if reader is None:
        reader = lambda commit, path: git_reader(root, commit, path)
        tagged = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"refs/tags/{campaign['benchmark_release']}^{{commit}}",
            ],
            cwd=root,
            text=True,
        ).strip()
        if tagged != campaign["release_commit"]:
            raise ValueError("release tag/commit mismatch")
    entries = campaign["models"]
    if len({m["model"] for m in entries}) != len(entries):
        raise ValueError("duplicate selected model")
    data = []
    for entry in entries:
        house = track_result(root, entry, campaign, "household", reader)
        python = track_result(root, entry, campaign, "python", reader)
        if house and python and house["runtime_identity"] != python["runtime_identity"]:
            raise ValueError("selected tracks use different serving runtime identities")
        monitor = resources(
            root, entry, campaign, reader, [value for value in (house, python) if value]
        )
        eligible = bool(
            house
            and python
            and house["complete"]
            and python["complete"]
            and house["critical"] == 0
            and monitor
            and monitor["completed"]
            and monitor["normal"]
        )
        data.append((entry, house, python, monitor, eligible))
    data.sort(
        key=lambda item: (
            not item[4],
            -(item[1]["passed"] if item[1] else -1),
            -(item[2]["passed"] if item[2] else -1),
            item[0]["model"],
        )
    )
    lines = [
        "# Local agent benchmark comparison",
        "",
        f"Release **{campaign['benchmark_release']}** (`{campaign['release_commit']}`); held-out partition, {campaign['trials']} trial(s) per task.",
        "",
        "Synthetic household workflows and real isolated Python automation. **Not Peixinho app acceptance or a pure base-model/quantization ablation.**",
        "",
        "Order uses household passes, then Python passes, only for complete usable coverage without a critical household boundary failure. There is no weighted composite. A single trajectory does not establish statistical superiority. Budget exhaustion does not prove inability.",
        "",
        "| Order | Model / engine | Household | Python | Budget outcomes | Invalid calls | Wall time | Min free / swap growth | Coverage |",
        "|---:|---|---:|---:|---:|---:|---:|---|---|",
    ]
    order = 0
    for entry, house, python, monitor, eligible in data:
        if eligible:
            order += 1
        score = lambda value: (
            f"{value['passed']}/{value['expected']}" if value else "pending"
        )
        status = "complete" if eligible else "partial/unusable or pending"
        if house and house["critical"]:
            status = "critical boundary failure; unranked"
        time_text = f"{monitor['seconds'] / 60:.2f} min" if monitor else "—"
        memory = (
            f"{monitor['minimum_free_percent']}% / {monitor['swap_growth_mib']:.1f} MiB"
            if monitor
            else "—"
        )
        both = [v for v in (house, python) if v]
        lines.append(
            f"| {order if eligible else '—'} | {entry['model']} / {entry['engine']} | {score(house)} | {score(python)} | {sum(v['budget'] for v in both)} | {sum(v['invalid'] for v in both)} | {time_text} | {memory} | {status} |"
        )
    lines.extend(["", "## Selected run evidence", ""])
    for entry, house, python, monitor, _ in data:
        ids = ", ".join(
            f"{key}: `{value['run_id']}` ({value['executed']}/{value['expected']} executed)"
            for key, value in [("household", house), ("Python", python)]
            if value
        )
        lines.append(
            f"- **{entry['model']}** — config `{entry['config']}`; {ids or 'pending'}. Exact model/quant/runtime and sampler pins are in the config and run manifests."
        )
        for value in (house, python):
            if value:
                for row in value["rows"]:
                    if not row["pass"]:
                        lines.append(
                            f"  - `{row['task_id']}`: {row.get('failure_class')}; checks {', '.join(row['failed_checks'])}."
                        )
    lines.extend(
        [
            "",
            "Historical versions, calibration runs and partial attempts remain append-only in their own reports. These selected runs are never inferred from the newest timestamp alone.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results/AGENT_LEADERBOARD.md"
    )
    args = parser.parse_args()
    campaign = json.loads(args.campaign.read_text())
    content = render_campaign(REPO, campaign)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)


if __name__ == "__main__":
    main()

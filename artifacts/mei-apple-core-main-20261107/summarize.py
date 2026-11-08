"""Compare complete, audited Apple core timing runs with the 0.11.0 control."""

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean, median

from run_campaign import HERE, ROOT, audit, check_native, git_file, save

# isort: split
# run_campaign makes the benchmark runner modules importable.
from qualify_mei_release import succeeded

METRICS = {
    "first_token_seconds": ("response", "first_generated_seconds"),
    "decode_tokens_per_second": ("decode_tps",),
    "total_seconds": ("elapsed_seconds",),
}


def value(row, path):
    for key in path:
        row = row[key]
    if type(row) not in (int, float) or not math.isfinite(row) or row <= 0:
        raise ValueError(f"invalid timing observation: {path}")
    return row


def compare_metric(a1, b1, b2, a2):
    stable, candidate = mean((a1, a2)), mean((b1, b2))
    forward = 100 * (b1 / a1 - 1)
    reverse = 100 * (b2 / a2 - 1)
    return {
        "stable": stable,
        "candidate": candidate,
        "change_percent": 100 * (candidate / stable - 1),
        "adjacent_changes_percent": {"forward": forward, "reverse": reverse},
        "direction_repeats_in_both_orders": (forward > 0 and reverse > 0)
        or (forward < 0 and reverse < 0),
        "process_ranges_overlap": max(min(a1, a2), min(b1, b2))
        <= min(max(a1, a2), max(b1, b2)),
    }


def visible_timing(rows):
    path = ("response", "first_visible_seconds")
    times = [value(row, path) for row in rows if row["response"][path[1]] is not None]
    return {
        "visible_count": len(times),
        "measured_count": len(rows),
        "median_seconds": median(times) if times and len(times) == len(rows) else None,
    }


def native_comparison(matrix):
    results = {}
    for cell in matrix["native"]:
        output = ROOT / cell["output"]
        check_native(output, ROOT / cell["config"])
        probes = json.loads((output / "probe.json").read_bytes())["probes"]
        boundary = probes["context_exact_cap"]["usage"]
        if (
            boundary["prompt_tokens"] != 65536
            or boundary["prompt_tokens_details"]["cached_tokens"] != 0
            or boundary["completion_tokens"] != 1
            or not probes["context_over_cap_rejected"]["rejected_as_expected"]
        ):
            raise ValueError(
                f"native context evidence differs from the declaration: {output}"
            )
        hashes = json.loads((output / "post-run-model-hashes.json").read_bytes())
        cleanup = json.loads((output / "owned-kv-cleanup.json").read_bytes())
        if not cleanup["server_exited"] or not cleanup["deleted"]:
            raise ValueError(f"native process or owned cache still live: {output}")
        samples = [
            json.loads(line)
            for line in (output / "resources.jsonl").read_text().splitlines()
        ]
        results[cell["model"]] = {
            "probes": len(probes),
            "checkpoint_files": len(hashes["files"]),
            "resource_samples": len(samples),
            "warning_samples": sum(s["kernel_pressure_level"] == 2 for s in samples),
            "swap_growth_mib": max(s["swap_used_mib"] for s in samples)
            - samples[0]["swap_used_mib"],
            "evidence": cell["output"],
        }
    if results.keys() != matrix["model_manifests"].keys():
        raise ValueError("native admission does not cover the full declared cohort")
    return results


def native_markdown(results):
    lines = [
        "# Apple MLX core main native qualification",
        "",
        (
            "All four profiles passed real native tool calls, cache reuse, uncached "
            "65,536-token admission and over-limit rejection. Model hashes matched "
            "after shutdown. These are admission results; timing is reported separately."
        ),
        "",
        "| Model | Passed probes | Verified files | Warning samples | Swap growth (MiB) |",
        "|---|---:|---:|---:|---:|",
    ]
    for model, row in results.items():
        lines.append(
            f"| [{model}](../../{row['evidence']}/probe.json) | {row['probes']} | "
            f"{row['checkpoint_files']} | {row['warning_samples']} / "
            f"{row['resource_samples']} | {row['swap_growth_mib']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def read_process(cell, reference):
    output = ROOT / cell["output"]
    if (output / "config.yaml").read_bytes() != git_file(ROOT / cell["config"]):
        raise ValueError(f"run configuration mismatch: {output}")
    if not json.loads((output / "post-run-model-hashes.json").read_bytes())[
        "all_match"
    ]:
        raise ValueError(f"model hash mismatch: {output}")
    if not succeeded(output):
        raise ValueError(f"timing evidence fails the qualification gate: {output}")
    checked = audit(output, reference)
    if checked != json.loads((output / "qualification-audit.json").read_bytes()):
        raise ValueError(f"timing audit differs from raw evidence: {output}")
    raw = json.loads((output / "qualification.json").read_bytes())
    if raw["measurement_mode"] != "uncached_chat_stream":
        raise ValueError(f"not an uncached streaming run: {output}")
    contexts = {}
    visible = {}
    for context in ("short", "loaded"):
        rows = [
            row
            for row in raw["rows"]
            if row["context"] == context and row["phase"] == "measured"
        ]
        contexts[context] = {
            key: median(value(row, path) for row in rows)
            for key, path in METRICS.items()
        }
        visible[context] = visible_timing(rows)
    active_status = [
        value(sample, ("elapsed_seconds",))
        for sample in raw["status_samples"]
        if sample.get("active_generations", 0) > 0
    ]
    process = {
        "metrics": contexts,
        "first_visible": visible,
        "active_cold_status": {
            "samples": len(active_status),
            "median_seconds": median(active_status),
            "max_seconds": max(active_status),
        },
        "evidence": cell["output"],
        "swap_growth_mib": checked["swap_max_mib"] - checked["swap_min_mib"],
        "all_normal_pressure": checked["all_normal_pressure"],
    }
    return checked["reference"], raw["prompt_sha256"], process


def comparison(selected_model=None, matrix_path=HERE / "matrix.json"):
    matrix = json.loads(git_file(matrix_path))
    native_comparison(matrix)
    models = matrix["model_manifests"]
    if selected_model is not None:
        if selected_model not in models:
            raise ValueError(f"no such model in the committed matrix: {selected_model}")
        models = (selected_model,)
    results = {}
    for model in models:
        cells = [cell for cell in matrix["cells"] if cell["model"] == model]
        if [cell["cell"] for cell in cells] != ["a1", "b1", "b2", "a2"]:
            raise ValueError(f"incomplete or unbalanced ABBA declaration: {model}")
        processes = {}
        reference = None
        prompt_sha256 = None
        for cell in cells:
            reference, prompts, process = read_process(cell, reference)
            if prompt_sha256 is None:
                prompt_sha256 = prompts
            elif prompt_sha256 != prompts:
                raise ValueError(f"prompt bytes differ across cells: {cell['output']}")
            processes[cell["cell"]] = process
        result = {}
        for context in ("short", "loaded"):
            visible = [
                process["first_visible"][context] for process in processes.values()
            ]
            visible_medians = [entry["median_seconds"] for entry in visible]
            result[context] = {
                "actual_prompt_tokens": reference[context]["prompt_tokens"],
                "metrics": {},
                "first_visible": {
                    version: {
                        key: sum(visible[index][key] for index in indices)
                        for key in ("visible_count", "measured_count")
                    }
                    for version, indices in {
                        "stable": (0, 3),
                        "candidate": (1, 2),
                    }.items()
                },
            }
            if all(value is not None for value in visible_medians):
                result[context]["metrics"]["first_visible_seconds"] = compare_metric(
                    *visible_medians
                )
            for metric in METRICS:
                a1, b1, b2, a2 = (
                    process["metrics"][context][metric]
                    for process in processes.values()
                )
                result[context]["metrics"][metric] = compare_metric(a1, b1, b2, a2)
        results[model] = {"processes": processes, "comparison": result}
    return results


def markdown(results, selected_model=None):
    json_name = (
        f"comparison-{selected_model}.json" if selected_model else "comparison.json"
    )
    lines = [
        "# Apple MLX core main vs. Mei 0.11.0",
        "",
        (
            "Each number averages the medians from two fresh processes, each with "
            "five measured repeats. Both versions used the same model and prompt, "
            "with cache reuse disabled. Cold probes and warmups are excluded. "
            "TTFT is time to the first generated token, including reasoning. All "
            "selected observations passed greedy output and usage parity."
        ),
        "",
        "| Model | Context (actual tokens) | TTFT (s) | Decode (tok/s) | Total (s) | First visible text (s) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    if selected_model is not None:
        lines[2:2] = [
            (
                f"Completed four-process comparison for **{selected_model}** only. "
                "The full campaign is reported separately."
            ),
            "",
        ]
    for model, result in results.items():
        pressure_flag = (
            ""
            if all(p["all_normal_pressure"] for p in result["processes"].values())
            else " §"
        )
        for context, row in result["comparison"].items():
            cells = []
            for key in (*METRICS, "first_visible_seconds"):
                metric = row["metrics"].get(key)
                if metric is None:
                    coverage = row["first_visible"]
                    stable, candidate = (
                        f"{coverage[version]['visible_count']}/{coverage[version]['measured_count']}"
                        for version in ("stable", "candidate")
                    )
                    cells.append(f"— ({stable} → {candidate} visible)")
                    continue
                markers = ("†" if metric["process_ranges_overlap"] else "") + (
                    "" if metric["direction_repeats_in_both_orders"] else "‡"
                )
                cells.append(
                    f"{metric['stable']:.2f} → {metric['candidate']:.2f} "
                    f"({metric['change_percent']:+.1f}%){markers}"
                )
            lines.append(
                f"| {model}{pressure_flag} | {context} ({row['actual_prompt_tokens']:,}) | "
                + " | ".join(cells)
                + " |"
            )
    lines += [
        "",
        (
            "† The two process ranges overlap. ‡ The direction did not repeat in both "
            "adjacent comparisons (A1/B1 and B2/A2). § At least one process recorded "
            "a non-normal pressure sample. These are diagnostic flags; the sample "
            "size does not establish statistical significance."
        ),
        (
            "First visible text is compared only when every measured repeat emitted "
            "visible content. The JSON also records status endpoint latency for active "
            "generations during each process's separate cold long-prompt probe."
        ),
        "",
        (
            "[Build receipt](build-receipt.json) · [Run declarations](matrix.json) · "
            f"[Individual process medians and evidence]({json_name})"
        ),
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--matrix", type=Path, default=HERE / "matrix.json")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--native-only", action="store_true")
    selection.add_argument(
        "--model", help="only report this model's complete ABBA result"
    )
    args = parser.parse_args()
    matrix_path = args.matrix.resolve()
    if matrix_path not in {
        HERE / "matrix.json",
        HERE.parent / "mei-0111-qualification-20261108" / "matrix.json",
    }:
        parser.error("only the original and 0.11.1 release matrices are supported")
    if matrix_path != HERE / "matrix.json" and not args.native_only:
        # The original prose describes the instrumented build, so return the
        # audited measurements for the new release without reusing those claims.
        if args.write:
            parser.error("review the 0.11.1 timing JSON before writing release notes")
        print(json.dumps(comparison(args.model, matrix_path), indent=2))
        sys.exit(0)
    if args.native_only:
        data = native_comparison(json.loads(git_file(matrix_path)))
        report = native_markdown(data)
        stem = "native"
    else:
        data = comparison(args.model)
        report = markdown(data, args.model)
        stem = f"comparison-{args.model}" if args.model else "comparison"
    if args.write:
        text = matrix_path.parent / f"{stem.upper()}.md"
        raw = matrix_path.parent / f"{stem}.json"
        if text.exists() or raw.exists():
            raise FileExistsError("refuse to overwrite qualification evidence")
        save(raw, data)
        with text.open("x") as stream:
            stream.write(report)
    else:
        print(report, end="")

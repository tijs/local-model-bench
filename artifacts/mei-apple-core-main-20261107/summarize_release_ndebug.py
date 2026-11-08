"""Audit the mirrored three-build Qwen experiment before reporting its results."""

import argparse
import json

import yaml
from prepare_release_ndebug import CASES, LABEL
from summarize import (
    HERE,
    METRICS,
    ROOT,
    compare_metric,
    git_file,
    native_comparison,
    read_process,
    save,
)

OUTPUT = HERE.parent / LABEL
PAIRS = {
    "corrected_vs_instrumented": ("a1", "b1", "b2", "a2"),
    "corrected_vs_published": ("r1", "b1", "b2", "r2"),
    "instrumented_vs_published": ("r1", "a1", "a2", "r2"),
}


def declared_identity(cell):
    cfg = yaml.safe_load(git_file(ROOT / cell["config"]))
    return {
        "mei_source_commit": cfg["mei_source_commit"],
        "vmlx_commit": cfg["vmlx_commit"],
        **{
            key: cfg["mei_release_artifact"][key]
            for key in ("binary_sha256", "metallib_sha256")
        },
    }


def comparison():
    matrix = json.loads(git_file(OUTPUT / "matrix.json"))
    cells = matrix["cells"]
    if [(row["cell"], row["arm"]) for row in matrix["native"] + cells] != [
        (cell, arm) for cell, (_, arm) in CASES.items()
    ]:
        raise ValueError("missing or reordered three-build declaration")
    native = native_comparison(matrix)
    original = json.loads(git_file(HERE / "matrix.json"))
    qwen = {cell["cell"]: cell for cell in original["cells"] if cell["model"] == "qwen"}
    reference, prompts, _ = read_process(qwen["a1"], None)
    expected_inputs = {"short": 26, "loaded": 30009}
    if {
        name: row["prompt_tokens"] for name, row in reference.items()
    } != expected_inputs:
        raise ValueError("original Qwen prompt size differs from the plan")
    processes = {}
    identities = {}
    for cell in cells:
        _, current_prompts, process = read_process(cell, reference)
        if current_prompts != prompts:
            raise ValueError("follow-up prompt bytes differ from the original cohort")
        if not process["all_normal_pressure"]:
            raise ValueError(f"non-normal pressure requires review: {cell['output']}")
        expected = declared_identity(cell)
        directory = ROOT / cell["output"]
        raw = json.loads((directory / "qualification.json").read_bytes())
        post = json.loads(
            (directory / "post-run-runtime-verification.json").read_bytes()
        )
        if any(
            any(record.get(key) != expected[key] for key in expected)
            for record in (raw["runtime_identity"], post)
        ):
            raise ValueError(
                f"runtime identity does not match committed config: {directory}"
            )
        if identities.setdefault(cell["arm"], expected) != expected:
            raise ValueError(
                f"each arm requires the same artifact in both processes: {cell['arm']}"
            )
        processes[cell["cell"]] = process

    if len({identity["binary_sha256"] for identity in identities.values()}) != 3:
        raise ValueError("expected three distinct binaries")
    for arm, key in (("published", "a1"), ("instrumented", "b1")):
        if identities[arm] != declared_identity(qwen[key]):
            raise ValueError(f"{arm} must use the exact original artifact")
    a, b = identities["instrumented"], identities["corrected"]
    if any(a[key] != b[key] for key in a.keys() - {"binary_sha256"}):
        raise ValueError(
            "the two candidate arms must have the same source pins and Metal bytes"
        )
    (native_cell,) = matrix["native"]
    native_post = json.loads(
        (
            ROOT / native_cell["output"] / "post-run-runtime-verification.json"
        ).read_bytes()
    )
    if declared_identity(native_cell) != b or any(
        native_post.get(key) != digest for key, digest in b.items()
    ):
        raise ValueError("the corrected timing artifact must match native admission")
    results = {
        pair: {
            context: {
                metric: compare_metric(
                    *(processes[cell]["metrics"][context][metric] for cell in order)
                )
                for metric in METRICS
            }
            for context in expected_inputs
        }
        for pair, order in PAIRS.items()
    }
    return {
        "native": native,
        "prompt_tokens": expected_inputs,
        "identities": identities,
        "processes": processes,
        "comparisons": results,
    }


def markdown(report):
    lines = [
        "# Qwen: effect of the Cmlx Release setting",
        "",
        (
            "Each number averages the medians of two fresh processes with five measured "
            "repeats per context. Cache reuse was disabled. All runs matched the original "
            "prompt bytes, greedy output and usage and had normal memory pressure."
        ),
        "",
        "| Comparison | Context | TTFT (s) | Decode (tok/s) | Total (s) |",
        "|---|---|---:|---:|---:|",
    ]
    for label, contexts in report["comparisons"].items():
        for context, metrics in contexts.items():
            values = []
            for row in metrics.values():
                flags = ("†" if row["process_ranges_overlap"] else "") + (
                    "" if row["direction_repeats_in_both_orders"] else "‡"
                )
                values.append(
                    f"{row['stable']:.2f} → {row['candidate']:.2f} "
                    f"({row['change_percent']:+.1f}%){flags}"
                )
            lines.append(
                f"| {label.replace('_', ' ')} | {report['prompt_tokens'][context]:,} tokens | "
                + " | ".join(values)
                + " |"
            )
    lines += [
        "",
        (
            "† The process ranges overlap. ‡ The direction differed across the mirrored "
            "halves. These flags describe the sample, without claiming statistical significance."
        ),
        "",
        "[Run declarations](matrix.json) · [Per-process evidence](comparison.json)",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = comparison()
    result = markdown(data)
    if args.write:
        target, raw = OUTPUT / "COMPARISON.md", OUTPUT / "comparison.json"
        if target.exists() or raw.exists():
            raise FileExistsError("refuse to overwrite comparison evidence")
        save(raw, data)
        with target.open("x") as stream:
            stream.write(result)
    else:
        print(result, end="")

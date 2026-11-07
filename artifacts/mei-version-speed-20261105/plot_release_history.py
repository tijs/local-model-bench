"""Plot the archived Qwen decode peaks, including the Mei 0.11 release audit."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPECTED = {"short": 17, "loaded": 30_000}
OLD = json.loads((HERE / "peak-speeds.json").read_text())
MODEL = "Tostibrown/" + OLD["model"]
AUDIT = ROOT / "artifacts/mei-upstream-qualification-20261106"


def read(path):
    return json.loads(path.read_text())


def peaks(rows, repeats):
    expected = {(c, n) for c in EXPECTED for n in range(1, repeats + 1)}
    if (
        len(rows) != len(expected)
        or {(r["context"], r["repeat"]) for r in rows} != expected
    ):
        raise ValueError("incomplete or duplicate observations")
    result = dict.fromkeys(EXPECTED, 0.0)
    for row in rows:
        response, context = row["response"], row["context"]
        usage = response["usage"]
        if (
            response["model"] != MODEL
            or usage["prompt_tokens"] != EXPECTED[context]
            or usage["completion_tokens"] != 128
            or usage["prompt_tokens_details"]["cached_tokens"] != 0
        ):
            raise ValueError("request differs from the release-history workload")
        result[context] = max(result[context], usage["tokens_per_second"])
    return result


def main():
    versions = {}
    for version, expected in OLD["versions"].items():
        folder = HERE / version
        rows = [
            json.loads(line)
            for line in (folder / "responses.jsonl").read_text().splitlines()
        ]
        versions[version] = peaks(rows, 3)
        if (
            versions[version] != expected
            or read(folder / "outcome.json")["status"] != "passed"
        ):
            raise ValueError(f"historical peak not verified: {version}")

    receipt = read(
        ROOT
        / "artifacts/mei011-comparison-preparation-20261106/verified-release-delivery.json"
    )
    paths = [
        item["output"]
        for item in read(AUDIT / "attention-selector-final-review-20261107.json")[
            "models"
        ]["qwen"]["active_status"]
    ]
    if len(set(paths)) != 2:
        raise ValueError("expected two separate production qualification processes")
    prompts = read(
        ROOT / "artifacts/mei-stable-qwen-unused-boundary-clean1-20261104/prompts.json"
    )
    cells = []
    for path in paths:
        folder = ROOT / path
        result = read(folder / "qualification.json")
        if (
            read(folder / "outcome.json")["status"] != "passed"
            or read(folder / "prompts.json") != prompts
            or result["runtime_identity"]["binary_sha256"] != receipt["binary_sha256"]
            or result["runtime_identity"]["metallib_sha256"]
            != receipt["metallib_sha256"]
        ):
            raise ValueError("not a qualified process of the released Mei 0.11 binary")
        cells.append(peaks([r for r in result["rows"] if r["phase"] == "measured"], 5))
    versions["0.11.0"] = {c: max(cell[c] for cell in cells) for c in EXPECTED}

    plt.rcParams.update({"font.size": 13, "svg.hashsalt": "mei-release-history"})
    fig, ax = plt.subplots(figsize=(12, 7.2), layout=None)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.89, bottom=0.23)
    fig.suptitle(
        "Mei: short and long context speed", fontsize=25, weight="bold", y=0.97
    )
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e5e7eb")
    for offset, context, color, label in (
        (-0.18, "short", "#2376a6", "Short prompt · 17 tokens"),
        (0.18, "loaded", "#e58b25", "Long prompt · 30,000 tokens"),
    ):
        bars = ax.bar(
            [i + offset for i in range(len(versions))],
            [v[context] for v in versions.values()],
            0.36,
            label=label,
            color=color,
        )
        ax.bar_label(bars, fmt="%.1f", padding=5)
    ax.set_xticks(range(len(versions)), [f"Mei {v}" for v in versions])
    ax.set_ylabel("Peak decode speed (tokens/sec)")
    ax.set_ylim(0, 83)
    ax.legend(loc="upper left", ncols=2, frameon=False)
    fig.text(
        0.09,
        0.15,
        "Qwen3.6 35B-A3B 4-bit on a 32 GB M1 Max. Same prompts, 128 generated tokens.",
        fontsize=12,
        color="#374151",
    )
    fig.text(
        0.09,
        0.113,
        "0.8–0.10: peak of 3 attempts per context in 1 process. 0.11: peak of 10 in 2 processes.",
        fontsize=12,
        color="#374151",
    )
    fig.text(
        0.09,
        0.076,
        "Runs were in separate sessions. Decode speed excludes prefill and varies by task and system load.",
        fontsize=12,
        color="#374151",
    )
    output = ROOT / "results/charts/mei-release-speed-history"
    fig.savefig(output.with_suffix(".png"), dpi=150)
    svg = output.with_suffix(".svg")
    fig.savefig(svg, metadata={"Date": None})
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    print(json.dumps(versions, indent=2))


if __name__ == "__main__":
    main()

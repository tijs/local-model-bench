"""Check the probe adaptation without importing MLX or performing GPU work."""

import argparse
import ast
import hashlib
import json
import math
import statistics
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent


def functions(path):
    return {
        node.name: node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.FunctionDef)
    }


def load(node, namespace):
    module = ast.Module(body=[node], type_ignores=[])
    # Only selected functions from the checksum-checked local fixtures run.
    exec(compile(module, "isolated-function", "exec"), namespace)  # noqa: S102
    return namespace[node.name]


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    for name, field in (
        ("upstream-source.py.txt", "source_sha256"),
        ("sdpa_vector_bench.py", "adapted_sha256"),
    ):
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == manifest[field]
    original = functions(ROOT / "upstream-source.py.txt")
    adapted = functions(ROOT / "sdpa_vector_bench.py")
    for name in ("run_chain", "reference_sdpa"):
        assert ast.dump(original[name]) == ast.dump(adapted[name]), name

    old_parse = load(original["parse_shape"], {"argparse": argparse})
    new_parse = load(adapted["parse_shape"], {"argparse": argparse})
    cases = (
        "16,2,30000,256", "16,2,17,256", "16,2,65536,256",
        "16,3,30000,256", "16,2,0,256", "16,2,30000", "bad",
    )
    for value in cases:
        results = []
        for parse in (old_parse, new_parse):
            try:
                results.append(("value", parse(value)))
            except argparse.ArgumentTypeError as error:
                results.append(("error", str(error)))
        assert results[0] == results[1], value

    # A deterministic clock checks retention and units, not GPU performance.
    ticks = iter((100, 110, 200, 220, 300, 330, 400, 440))
    calls = []
    measure = load(adapted["measure"], {
        "math": math,
        "statistics": statistics,
        "time": SimpleNamespace(perf_counter_ns=lambda: next(ticks)),
        "run_chain": lambda *args: calls.append(args),
    })
    result = measure(None, None, None, 1, 2, 1, 2, 2)
    assert len(calls) == 5  # One warmup plus four timed chains.
    samples = result[4]
    expected = ((5e-9, 10e-9), (15e-9, 20e-9))
    assert len(samples) == 2 and all(len(row) == 2 for row in samples)
    for actual_row, expected_row in zip(samples, expected, strict=True):
        for actual, wanted in zip(actual_row, expected_row, strict=True):
            assert math.isclose(actual, wanted, rel_tol=1e-12)
    assert math.isclose(result[0], 5e-9, rel_tol=1e-12)
    assert math.isclose(result[1], 12.5e-9, rel_tol=1e-12)
    assert json.loads(json.dumps(samples)) == samples
    print("PASS: two upstream function bodies unchanged; seven parser cases; four fake-clock samples retained")
    print("No MLX import, GPU execution, numerical or real-performance claim")


if __name__ == "__main__":
    main()

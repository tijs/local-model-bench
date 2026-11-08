"""Validate and summarize the synthetic Gemma local-attention screen."""

import argparse
import json
import math
from collections import Counter
from itertools import permutations
from pathlib import Path
from statistics import median

ARMS = ("current_policy", "native_window", "fused_window")
KEY_COUNTS = (256, 1279)
REPEATS = 18


def summarize(rows, arms=ARMS):
    parity = {}
    samples = {}
    orders = {}
    for row in rows:
        keys, arm = row["keys"], row["arm"]
        if keys not in KEY_COUNTS or arm not in arms:
            raise ValueError(f"unexpected screen shape or arm: {row}")
        if row["event"] == "parity":
            error = row["relative_rms"]
            if arm == arms[0] or (keys, arm) in parity or not 0 <= error <= 0.007:
                raise ValueError(f"invalid or duplicate screen parity: {row}")
            parity[keys, arm] = error
        elif row["event"] == "sample":
            repeat, elapsed = row["repeat"], row["elapsed_ms"]
            key = keys, repeat, arm
            if (
                row["queries"] != 256
                or type(repeat) is not int
                or not 0 <= repeat < REPEATS
                or key in samples
                or not math.isfinite(elapsed)
                or elapsed <= 0
            ):
                raise ValueError(f"invalid or duplicate screen sample: {row}")
            samples[key] = elapsed
            orders.setdefault((keys, repeat), []).append(arm)
        else:
            raise ValueError(f"unknown screen event: {row}")

    allowed_orders = tuple(permutations(arms))
    expected_order_counts = dict.fromkeys(
        allowed_orders, REPEATS // len(allowed_orders)
    )
    for keys in KEY_COUNTS:
        if any((keys, arm) not in parity for arm in arms[1:]):
            raise ValueError(f"missing parity for {keys} keys")
        observed_orders = Counter(
            tuple(orders.get((keys, repeat), [])) for repeat in range(REPEATS)
        )
        if observed_orders != expected_order_counts:
            raise ValueError(f"incomplete or unbalanced timing for {keys} keys")

    result = {}
    for keys in KEY_COUNTS:
        arm_results = {}
        for arm in arms:
            times = [samples[keys, repeat, arm] for repeat in range(REPEATS)]
            paired_ratios = [
                times[repeat] / samples[keys, repeat, arms[0]]
                for repeat in range(REPEATS)
            ]
            arm_results[arm] = {
                "median_ms": median(times),
                "range_ms": [min(times), max(times)],
                "median_paired_latency_change_percent": 100
                * (median(paired_ratios) - 1),
                "relative_rms": parity.get((keys, arm)),
            }
        result[keys] = arm_results
    return {
        "scope": "synthetic BF16 Gemma local attention, not end-to-end Mei",
        "query_tokens": 256,
        "repeats_per_arm": REPEATS,
        "results_by_key_count": result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_screen", type=Path)
    parser.add_argument("--native-only", action="store_true")
    args = parser.parse_args()
    arms = ARMS[:2] if args.native_only else ARMS
    with args.raw_screen.open() as stream:
        result = summarize((json.loads(line) for line in stream), arms)
    print(json.dumps(result, indent=2))

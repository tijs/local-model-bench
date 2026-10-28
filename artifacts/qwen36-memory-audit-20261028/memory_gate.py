"""Pinned bounded-retry policy: pressure/swap remain independent hard stops."""
from __future__ import annotations

from typing import Any

MIN_FREE_PERCENT = 10


def resource_gate_reason(sample: dict[str, Any], initial: dict[str, Any], low: int, warning: int) -> str | None:
    if sample['kernel_pressure_level'] >= 4:
        return 'critical memory pressure'
    if warning >= 2:
        return 'sustained warning memory pressure'
    if low >= 2:
        return 'sustained memory free <=10%'
    if sample['swap_used_mib'] - initial['swap_used_mib'] >= 2048:
        return 'swap growth >=2 GiB'
    if sample['swap_used_mib'] >= 16384:
        return 'swap >=16 GiB'
    if sample['disk_free_bytes'] < 10 * 1024**3:
        return 'disk below 10 GiB'
    return None

"""Scratch and filesystem-checkpoint storage defaults (pure data)."""

SCRATCH_DEFAULTS = {
    "max_idle_hours": 24,
    "max_size_gb": 0,  # Decimal GB; 0 disables size-based eviction.
}

CHECKPOINT_DEFAULTS = {
    "enabled": False,
    # Max checkpoints per working directory; enforced by ref rewrite + GC of older commits.
    "max_snapshots": 20,
    # Hard ceiling on total ~/.hermes/checkpoints/ size (MB); the oldest checkpoint per project
    # is dropped round-robin until under the cap. 0 disables.
    "max_total_size_mb": 500,
    # Skip files larger than this (MB) when staging (datasets, model weights). 0 = no filter.
    "max_file_size_mb": 10,
    # Background sweep (CLI helper thread / gateway housekeeping tick, at most once per
    # min_interval_hours; never on the startup path — its git gc can block for tens of seconds):
    # deletes projects whose last_touch is older than retention_days, GCs the shared store when
    # refs moved, enforces max_total_size_mb, deletes legacy-* archives older than retention_days.
    # It NEVER deletes orphans (workdir missing on
    # disk) — a missing workdir may just be an unmounted volume/VPN, and an unattended sweep
    # must not guess. Orphans: `hermes checkpoints prune` (`--keep-orphans` to skip).
    "auto_prune": True,
    "retention_days": 7,
    "min_interval_hours": 24,
}

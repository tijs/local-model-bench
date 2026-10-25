---
sidebar_label: Scratch cleanup
---

# Scratch cleanup

Hermes uses `<profile home>/cache/scratch` for temporary work. Keep project source and
durable results in project directories: scratch entries are disposable.

Configure retention and an optional size budget in that profile's `config.yaml`:

```yaml
scratch:
  max_idle_hours: 48
  max_size_gb: 10
```

The gateway, classic CLI and long-lived serve backend check every housekeeping tick and perform
cleanup at most once an hour per home, including when a check is overdue at startup.
Changing either setting makes the next tick eligible. A failed run is retried later.

An entry expires when no file or directory beneath it has been written for the idle
period. If scratch still exceeds the size budget, older inactive entries can be evicted
before they expire. Size is the apparent file/tree size; GB means 1,000,000,000 bytes.
Shared filesystem blocks mean deleted sizes may exceed the actual disk space reclaimed.

Hermes-owned live working directories, executables and open files are protected. The
age sweep retains its existing cleanup of abandoned orphan processes. Capacity eviction
also protects other inspectable live processes and never terminates a process. Unreadable
entries are retained. The size budget is best effort, not a filesystem quota: writes
between checks and protected work can exceed it. Hermes logs a warning if it cannot
meet the budget without touching protected data.

Defaults remain 24 hours idle and no size budget (`max_size_gb: 0`). The policy covers
scratch, not chat history, memories, installed tools, or other cache directories.
Per-entry removal logs are in `logs/scratch-prune.log`; `cache/scratch-cleanup.json`
records the last successful check and whether scratch remains over budget.

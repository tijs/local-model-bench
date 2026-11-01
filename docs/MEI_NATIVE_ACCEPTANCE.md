# Native Mei release acceptance

Use the guarded launcher with a committed, pinned config:

```sh
uv run --locked python runner/run_mei_acceptance.py \
  --config configs/mei-rc2-native-20261101/groot.yaml \
  --output artifacts/mei-rc2-native-groot-20261101 \
  --deadline 3600
```

This runs Mei's own versioned probe program. It checks model identity, status,
plain and streaming output, native tools, tool-result history replay, prefix
cache reuse, the exact context boundary and rejection beyond that boundary.
It is release admission, with its own evidence; it writes no household/Python
score rows and does not establish application acceptance or stable promotion.

The parent requires exact committed config bytes, clean benchmark helpers,
pushed Mei/vmlx source pins, an isolated runtime base, free benchmark ports and
an explicit capacity plan. Seven normal-pressure, flat-swap baseline samples
precede launch. Capacity checks use bytes; kernel free percentage is telemetry.
The same pressure, swap, disk and deadline rules used by scored runs remain in
force. A critical-pressure sample stops immediately; two consecutive warnings
also stop. No background applications or unrelated services are closed.

The whole launcher/probe/server session remains owned until cleanup completes.
The exact runtime base is forwarded to launch and teardown. A zero exit code
cannot pass without the required probe evidence. `--skip-context` or
`--skip-cache` produces diagnostic coverage, never full native admission.

The fresh output directory preserves config, invocation, baseline, resources,
launch/probe output, runtime identity and the final outcome. Existing output is
refused. Review an interrupted attempt before retrying, and preserve all raw
results. The current rc.2 config uses the public, hash-verified Groot text pack;
the first run completed with failed direct tool probes and is unqualified.
See its [preserved review](../artifacts/mei-rc2-native-groot-20261101/README.md).
The example output already exists: choose a fresh directory and commit an
updated source-pinned config before a new attempt.

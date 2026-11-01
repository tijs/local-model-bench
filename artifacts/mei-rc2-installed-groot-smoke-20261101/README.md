# Installed Mei rc.2 preview smoke

The published Homebrew `mei-preview` installation passed all **11 requested
checks** in 45.714 seconds, excluding the 30-second baseline. Nine resource
samples were normal, with zero swap growth. The owned server stopped and
623,633,806 bytes of owned KV files were inventoried and removed.

This checks installed resource lookup and live identity, status, plain output,
streaming/nonstreaming tools, tool history, parity and prefix-cache reuse.
Context was explicitly skipped: this is installation diagnostics, not full
native admission or a task score. The exact same executable and Metal library
passed the separate [full 13-check native gate](../mei-rc2-native-groot-tools1024-20261101/README.md).

Reproduce with the [committed smoke script](../candidate-system-campaign-20261101/mei-rc2-validation/installed-smoke.py)
and [config](../../configs/mei-rc2-native-20261101/groot-installed-smoke.yaml).
The script uses the shared resource supervisor and an owned process group;
existing output/runtime paths are refused.

[Probe results](probe.json) · [Outcome](outcome.json) ·
[Installed identity](record.json) · [Server log](server.log) ·
[KV cleanup](owned-kv-cleanup.json)

Distribution readback:
[installed hashes](../candidate-system-campaign-20261101/mei-rc2-validation/installed-asset-readback.json),
[GitHub assets](../candidate-system-campaign-20261101/mei-rc2-validation/github-release-rc2.json),
[main/tag and stable-channel checks](../candidate-system-campaign-20261101/mei-rc2-validation/remote-source-readback.json).
Stable promotion and loaded-status responsiveness remain open.

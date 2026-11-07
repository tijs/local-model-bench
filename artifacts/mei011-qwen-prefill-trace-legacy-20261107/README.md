# Qwen prefill trace: first launch stopped before timing

The guarded Mei 0.10.0 mmap-off process reached two consecutive memory-pressure
warnings during model load. It exited without reaching request timing, so this
run cannot explain the prefill difference. Swap stayed at 537 MiB, all 15
checkpoint hashes matched after exit, and there was no owned KV data to remove.

[Outcome](outcome.json) · [Resource samples](resources.jsonl) ·
[Server log](server.log) · [Checkpoint verification](post-run-model-hashes.json)

The declared retry uses a fresh runtime and verifies the checkpoint immediately
before each launch. The release binaries, model, settings and memory guard
are unchanged.

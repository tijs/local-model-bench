# local-model-bench benchmark-v9.4

Adds a guarded native Clover diagnostic with exact Kapitsa source, executable,
model and probe-program hashes. The server uses one private/local slot, no
drafter or disk cache and explicit 32-row block diffusion at threshold 0.95.
Startup must confirm the real decoder; causal/self-speculative modes cannot
silently substitute for diffusion.

The first M1 Max run passed identity, plain output, streaming and nonstreaming
automatic tools, and the unchanged dependent-call/grounded-continuation gate.
It took 20.329 seconds excluding the 30-second baseline, with four normal-pressure
samples and zero swap growth. All 15 post-run model-file hashes matched; the
owned server stopped. This is native Metal using an MLX-format pack, not a Mei
or MLX runtime result. No task rows or Clover ranking were created.

The existing native supervisor can now apply a backend-specific diagnostic
evidence check. Custom checks are always marked diagnostic and can never claim
full Mei native admission; missing, failed and malformed evidence fails closed.
Capacity/pressure/swap/disk/deadline limits and owned-session teardown remain.
All 681 model-free runner tests pass (97.699 seconds), including the new
diagnostic evidence/rejection cases and owned-process teardown controls. Ruff
and ty pass on the changed Python files. See the [diagnostic guide](../CLOVER_NATIVE.md) and
[actual run evidence](../../artifacts/clover-native-diffusion-20261101/README.md).

The constrained named/required/strict-tool limitation remains explicit. Cache
numerical controls, near-context-cap behavior, scored backend integration and
the full held-out Clover evaluation remain open. Short native tools are not a
full benchmark or Peixinho app acceptance result.

Scored task helpers, validators, scored launch parent/supervisor and existing
serving profiles are unchanged from v9.3. Previous grades remain append-only;
the six-model comparison retains separately verified measurement identities.

Mei 0.10.0-rc.2 is also released and installed-asset verified, with 13 full native
checks and 11 diagnostic installation smoke checks. Stable Mei remains 0.9.0;
contender determinism/throughput and loaded-status responsiveness remain open.

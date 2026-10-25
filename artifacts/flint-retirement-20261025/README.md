# Retiring the standard-affine Flint trial — 2026-10-25

User authorized preserving/pushing the incomplete attempts and retiring old local caches/model payloads before JANGH2 implementation. This closes no benchmark todo and supplies no full score. Prior append-only results remain unchanged except the two already-recorded sanity rows from the clean-memory retry.

The two prior attempts are in commits a1505a3 and 5efdbb6. The third attempt and research are archived with this commit. Runtime/native-gate material not already tracked has been copied here before cleanup. Model weights and generated build/runtime caches are deliberately excluded from Git. Immutable weight hashes remain in artifacts/flint-mei-gate-20261024/staging and artifacts/flint-retry-20261025T083240Z-all/model-hashes.json.

cleanup-manifest.json lists the exact retired local roots. Only these old Flint model/build/runtime roots are authorized for deletion; source checkouts, Git history, result rows, configs, other model caches, CoCore and unrelated data are retained. The model provenance sidecar is retained and marked retired after deletion. Final deletion evidence is added separately after the archive push.

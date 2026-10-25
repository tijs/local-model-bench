# Flint same-profile retry after memory cleanup — incomplete

Tijs confirmed that memory-heavy applications had been closed and authorized retrying the existing profile. The preflight recorded three samples at 89% free, kernel pressure normal (1), swap stable at 2646.12 MiB, ~70.6 GB disk available, and free ports. All 16 pinned model files matched their sizes and SHA-256 hashes. No model weights or serving settings changed; the normal disk gate was used without override flags.

The runner at 5efdbb60125166ef7da2a71815247a5ec6ad2df8 used committed config configs/Flint-mixed-3-4bit-full-20261024/mei.yaml, hash c754cda7b797. Health and plain completion passed; sanity passed 2/2. During the first Hermes Ops selection task, memory free fell to 10% and 9% in consecutive 10-second samples, kernel pressure became warning (2), and swap increased to 3493.25 MiB. The supervisor terminated the owned run at 2026-10-25T08:43:01Z under its declared safety policy. This was a protective stop before critical pressure/OOM, not a completed task failure or a demonstrated OOM.

Only two new append-only sanity rows exist. The previous complete byte prefix of results/log.jsonl was independently hashed and is unchanged. No Hermes Ops task completed in this retry, and no coding suite ran. No full score or front-runner verdict is warranted; the leaderboard was not rebuilt from this partial attempt.

The launcher rebuilt Mei from the same clean source commit c9b6013958cbc838b156b717f3b49a0045f84064 and clean vmlx 633fe166630ef04310aea7d5a1795555ab32970d. Package.swift and Package.resolved hashes match the native gate. The executable remains 92750736 bytes but its hash changed to b33f04feeb9a4d5268a277a42d19eb6ace7d538ef0dcd97d897fff9ceba62330; all three Metal libraries retain their admitted hashes. Preserve this actual build identity and do not claim byte identity to the native gate.

The process group was stopped, no runner/Mei/prompt process remained, ports 8024/8017 were free, and the runtime PID file was absent. Memory recovered to 86% immediately after stop. No unrelated application or CoCore was touched. No commit or push was performed.

Conclusion: user cleanup established a clean baseline, but the unchanged serving profile still crossed the conservative pressure stop during the multi-turn workload. Do not repeat this profile unchanged. A reduced-memory profile and fresh native admission remain the next direction for user review. This does not prove that every smaller-cache configuration will fit.

Full preflight, model hashes, build log, dependency workspace state, supervisor source and resource telemetry are preserved in artifacts/flint-retry-20261025T083240Z-all/.

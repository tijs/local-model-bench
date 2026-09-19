# Bonsai-2 (Ternary-Bonsai-2-27B-mlx-2bit) CPU-only aligned repack — 2026-09-19

**Verdict (bounded unit):** the scratch aligned repack was actually run (not just planned)
under a CPU-only, artifact-scoped resource gate. It produces a **payload-preserving aligned
scratch candidate** and removes the measured unaligned-load condition (1,253 tensors /
6,834,034,688 B would no longer be realigned into RAM at load). It does **NOT** prove model
load, memory improvement, exact-65,536-token capacity, functional parity, or ranking:
no server, probe, or benchmark ran in this unit.

**Sections keep three evidence classes strictly separate:** measured facts (raw output and
independent re-verification), what the run does/does not establish (labeled boundary), and
the queued next action (labeled as future, conditional).

---

## 1. Purpose and resource gate

- **Purpose:** quantify the one credible lever named by the prior OOM diagnosis
  (`artifacts/bonsai2-mlx-oom-diagnosis-20260919.md` §5, §7.3): a scratch header-padding
  repack that removes the loader-time realignment allocation, with the pinned model files
  untouched. This unit only **builds and verifies the aligned scratch candidate**; it does
  not load or serve it.
- **Resource gate (what this unit was allowed to do):** CPU-only, artifact-scoped.
  The repack tool does byte-level header re-padding and payload copying — no GPU work, no
  Metal, no memory-mapping of the payload into an allocator budget, no server/listener, no
  build, no probe, no benchmark, no CoCore. No source change was made and no full rerun was
  launched. The run consumed ~16 s of CPU/disk on the copy and ~0 extra GPU memory.
- **Run window:** 2026-09-19 ~10:45–10:48 CEST (manifest `generated_utc`
  `2026-09-19T08:48:09Z`; destination directory mtime 10:48). No model server/listener or
  probe process was active during or after the run (process scan at note time shows only
  the unrelated Hermes marktplaats MCP helper, not an MLX/model server).

## 2. Exact paths and tool

- Source (pinned, untouched): `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit`
- Destination (diagnostic/disposable scratch):
  `/Users/tijs/.local/share/local-model-bench/mei-models/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919`
- Tool: `/Users/tijs/projects/mei/tools/align_safetensors.py` (header-padding repack;
  payload bytes bit-identical, payload sha256-verified — see its docstring, lines 1-30).
- Output produced by the run (recorded verbatim): `model.safetensors: padded 2B, payload
  8595174880B sha=432b4bcc987aeccc.. audit unaligned=0 (15.9s)`.

## 3. Measured results (raw evidence)

### Padding and sizes

| Item | Value |
|---|---|
| Safetensors header, source | 303,102 B |
| Safetensors header, destination | 303,104 B (+2 padding bytes) |
| Payload bytes | 8,595,174,880 B (unchanged) |
| File size, source (`model.safetensors`) | 8,595,477,990 B |
| File size, destination (`model.safetensors`) | 8,595,477,992 B |
| Target alignment | 8 B |
| Payload offset, source / destination | 303,110 / 303,112 |
| Tensors / `unaligned_after` (manifest) | 2,390 / **0** |
| Repack wall time (manifest) | 15.89 s |

### Identity checks (all pass)

- **Headers:** source and destination JSON headers are **equal** after decoding
  (`headers JSON equal: True`); the only on-disk difference is the 2 trailing padding
  spaces that shift the payload start by 2 B.
- **Payload:** independent byte-for-byte comparison of the 8,595,174,880 B payload regions
  (mmap compare, 64 MiB chunks): **identical**; manifest records
  `payload_sha256 = 432b4bcc987aeccc8630d2e5ae5dd06bd44b4b00e363c7316bc65addc9fac0ae`
  (equivalent to the tool's own verification step).
- **Sidecars:** `diff -r -q` over every non-`.cache` file except `model.safetensors` and
  the new `MEI_ALIGN_MANIFEST.json` returns exit 0 — config.json, tokenizer.json,
  tokenizer_config.json, generation_config.json, chat_template.jinja, hadamard.json,
  files.json, PACK-RUNTIME.md (and README/LICENSE/NOTICE/preprocessor_config/
  reload-validation/tokenizer-validation/assets/runtime/.gitattributes) are **byte-identical**.
- **Unaligned condition:** manifest `unaligned_after: 0` — the measured load warning from
  the OOM run (`realigned 1253 unaligned tensor(s) (6834034688 bytes)`, server.log:2,5 of
  the prior partial-gate run) is removed for this candidate by construction: every tensor
  payload now starts aligned, so the loader has nothing to realign.
- **New sidecar:** `MEI_ALIGN_MANIFEST.json` exists only in the destination (tool, UTC
  timestamp, source_dir, target_alignment 8, shard record with padding/payload/sha/tensors/
  unaligned_after/repack_seconds); `.cache` is the HF artifact cache, excluded from the
  identity claim.

### Full-file hashes (distinction)

- **Source full SHA-256:** `130de5925082c168b7866b2e91b52e44abbafc99017e3ca352b77b5b55a269ed`
  — re-verified at note time; **matches the prior record** (revision
  `3f926b415992eaa2ae9dd7b573706494d6bbf787`, same hash recorded in the OOM diagnosis) —
  the pinned model is untouched.
- **Destination full SHA-256:** `d33e7fb7432f1e3d39374de97f1b1414ecb1b24dea7b46335a85b0ab302cb055`
  — a **fresh, different** hash expected by design: it differs from the source only because
  the 2 header gaps shift every payload byte by 2 positions, so the whole-file digest must
  differ even though the payload bytes are identical and the payload digest matches. The two
  hashes are therefore **not** comparable as identity proof; the identity proof is header-
  equality + payload byte-identity + equal payload SHA.

### Disk

- Free disk after repack (recorded at run time): **48,358,653,952 B**.
- Re-checked at note time: 48,353,255,424 B (drift ≈ 5.4 MiB from unrelated concurrent
  writes; both readings far above the ~8.6 GB candidate size).

## 4. Strict boundary — what this proves and what it does NOT prove

**This unit establishes (and only this):**

1. A payload-preserving aligned scratch candidate exists: header padded by exactly 2 B,
   payload bit-identical, sidecars byte-identical, manifest recorded, source untouched.
2. The measured unaligned-load condition is removed for this candidate
   (`unaligned_after = 0` in the load path the align tool audits), i.e. the specific
   `realigned 1253 unaligned tensor(s) (6834034688 bytes)` condition from the OOM run would
   not re-occur on load of this candidate.

**This unit does NOT establish** — because no server was started, no model was loaded, no
probe ran, and no benchmark ran:

- that the candidate **loads** cleanly under the real loader (align-audit is not a load);
- that load-time or steady-state **memory improves** (removing ~6.36 GiB of realigned
  allocator copies is a partial-pressure argument, not a measurement);
- that **exact-65,536-token capacity** is reached (the prior run died at 35,840→36,864
  tokens; the per-token working-set growth driver was never cured by padding);
- **functional parity** (identity/completion/tools/cache probes all rerun needed);
- **ranking** or any benchmark row (nothing was appended; candidate stays gated/unranked).

## 5. State preservation

- **Pinned source preserved:** files, revision, and full SHA-256 (`130de592…`) confirmed
  unchanged; nothing was written into the source directory.
- **Destination is diagnostic/disposable:** name carries `-aligned-diagnostic-20260919`;
  it is a scratch candidate for a future supervised load, not a promoted artifact. It may be
  discarded after any future probe; no ingest, ranking, or leaderboard row references it.
- Repo `local-model-bench` clean at `3b738561864f41e1aeab844f73d530d36f20a508` before and
  after; only this note is added by this unit.

## 6. Next bounded action (explicit, conditional)

- The single credible next step is a **separate, supervised server load + short
  capacity-boundary probe** of this scratch candidate (measure: does it load with
  `realigned … unaligned tensor(s)` absent, and does the prefill failure boundary move?),
  **only if authorized by the current Kiem queue** (this unit holds no such authorization).
- **Never launch a full battery from this evidence.** A full probe suite / ranking run is
  out of scope from an alignment-only proof; at most the stated short capacity-boundary
  probe runs under an explicit queue decision, with the pinned model still untouched.

## 7. Evidence index

| Fact | Raw evidence (exact path) |
|---|---|
| Exact tool output line | run log (quoted verbatim §2): `padded 2B, payload 8595174880B sha=432b4bcc987aeccc.. audit unaligned=0 (15.9s)` |
| Manifest (2,390 tensors, padding 2, unaligned_after 0, payload_sha256, 15.89 s) | `…/Ternary-Bonsai-2-27B-mlx-2bit-aligned-diagnostic-20260919/MEI_ALIGN_MANIFEST.json` |
| File sizes 8,595,477,990 / 8,595,477,992 B | `stat` of both `model.safetensors` (re-checked at note time) |
| Headers JSON equal; payload offsets 303,110 / 303,112 | python header decode + mmap payload compare (this unit) |
| Payload 8,595,174,880 B byte-identical | mmap compare exit `True` (this unit) |
| Sidecars byte-identical | `diff -r -q` exit 0 (this unit) |
| Source full SHA-256 `130de592…` (matches prior record) | `shasum -a 256` source (this unit) + diagnosis §1 |
| Destination full SHA-256 `d33e7fb7…` (differs only via 2 header spaces) | `shasum -a 256` destination (this unit) |
| Free disk after repack 48,358,653,952 B | recorded at run time; re-checked 48,353,255,424 B at note time |
| Unaligned-load condition being removed (1,253 / 6,834,034,688 B) | prior run `server.log:2,5` (diagnosis §2) + manifest `unaligned_after: 0` |
| Gate context and next steps | `artifacts/bonsai2-mlx-oom-diagnosis-20260919.md` §5, §7 |
| Align tool semantics (header-padding, payload identity) | `/Users/tijs/projects/mei/tools/align_safetensors.py:1-30` |

*Note: timestamps are CEST (UTC+02:00); manifest UTC `2026-09-19T08:48:09Z` =
10:48:09 CEST. Repo commit referenced: `3b738561864f41e1aeab844f73d530d36f20a508`.*
# Qwen3.6-35B-A3B — runbook step 2 stages the HF source, not the local conversion: staging correction note 2026-09-15

Append-only correction/evidence artifact for the Qwen3.6 future-machine
quantisation preparation. Corrects a reproducibility gap in step 2 of
`artifacts/qwen36-scheme-aware-runbook-20260915.md` (2026-09-15 runbook, lines
96-100, the "Stage with provenance" step). That runbook is append-only and is
NOT edited here. This note is evidence/correction only: no weights downloaded,
no package installed, no conversion/calibration, no server launched, no
`results/log.jsonl` row, no `results/LEADERBOARD.md` change, no `configs/`,
runner, or test edit, no Kiem change, and `/Users/tijs/projects/mei` was only
inspected with read-only git commands (its pre-existing untracked `Casks/` and
`tap/` entries were left alone).

## 1. The claim being corrected

The runbook's step 2 instructs the future machine to stage the converted
artifact "via `/Users/tijs/projects/mei/tools/stage_mlx_checkpoint.py` using
`--repo mlx-community/Qwen3.6-35B-A3B-bf16 --revision
04bbe07c3ed2d93cbf832f523fea344bca1d0fcf --target <model-root> --expect-bytes
<measured>`; verify the staged snapshot bytes match expectations." The intent
(step 1 -> step 2) is to bring the LOCALLY CONVERTED, quantised output into the
model root with provenance. The staging tool cannot do that when invoked this
way: `--repo` always triggers a fresh Hub download, and there is no
local-directory input mode. The command as written therefore stages the
UNQUANTISED bf16 source, not the conversion output.

## 2. Exact observed source behavior (stage_mlx_checkpoint.py, mei HEAD 950e8c2fdfa13ca6ed1dbfbd7794abc96705553a; tool last changed in commit d35ad34)

Inspection method: read of
`/Users/tijs/projects/mei/tools/stage_mlx_checkpoint.py` at that commit. NOT an
execution: no download, no staging, no verify run occurred on this Mac (no
converted artifact exists locally to stage, and downloading is forbidden by
this branch). Line numbers refer to that file at that commit.

- Full argument surface (lines 429-439): `--repo`, `--revision` (default
  `"main"`), `--subdir`, `--target`, `--expect-bytes`, `--verify-only`,
  `--self-test`. There is NO `--local-dir`, `--source-path`, or any other
  local-input option.
- Non-verify-only path (lines 449-461): when `--repo` is given (and
  `--verify-only` is not), the script unconditionally calls
  `huggingface_hub.snapshot_download(repo_id=args.repo, revision=args.revision,
  allow_patterns=..., local_dir=str(target), local_dir_use_symlinks=False)`.
  With no `--subdir`, `allow_patterns=None`, so the FULL repository at that
  revision is downloaded as a real file copy under `--target` (no symlinks).
  For the runbook's repo@revision that is the 14-shard bf16 source, total file
  bytes 70,241,335,712 (65.42 GiB) — a second full source copy, on top of the
  one the conversion already needed, and NOT included in the preflight's
  >= ~105 GiB disk accounting.
- `--verify-only` (lines 436-437, 449, 463-484): skips the download entirely;
  optionally relocates a subdir (only when `--subdir` is set and the subdir
  holds a root `config.json`), then runs `verify()` on `--target` as-is and
  writes the provenance manifest. This is the ONLY no-network path through the
  tool.
- `verify()` (lines 155-237): requires `config.json` at the target root; builds
  the expected file set from `model.safetensors.index.json` weight_map (or, if
  no index exists, discovers `model-*.safetensors` / `model.safetensors`);
  fails on missing/stray/empty/truncated/corrupt shards and on
  `file_bytes < payload_total`; else `ok=true`. The bf16 source (valid index,
  complete shards) would PASS this verification, so the runbook's gate would
  NOT detect that the wrong (unquantised) artifact was staged.
- `--expect-bytes` (lines 480-483): a mismatch only prints
  `WARN: file_bytes ... != expected ...`; the exit code is unaffected
  (`return 0 if result["ok"] else 1`, line 484). It is NOT a hard gate.
- Provenance manifest (lines 240-252), written to
  `<target>.provenance.json`: fields `repo`, `pinned_revision`,
  `resolved_commit`, `subdir`, `staged_at_utc`, `verify`, `loadability`
  ("NOT CHECKED (GPU-gated)"). `resolved_commit` is the literal `--revision`
  string echoed into `write_provenance` (line 477-478) — it is NOT a Hub
  resolution query. In `--verify-only` mode `repo` becomes `"(verify-only)"`
  (line 477) and, if `--revision` is omitted, `pinned_revision` /
  `resolved_commit` default to `"main"`. The manifest has NO fields for
  conversion tool, CLI, flags, calibration inputs, or the locally-produced
  fact — it cannot by itself preserve source/conversion provenance.

## 3. Confirmed gap

- Runbook step 2's exact command downloads `mlx-community/Qwen3.6-35B-A3B-bf16`
  @ `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` from the Hub again and stages
  the UNQUANTISED bf16 source as the benchmark candidate. The locally converted
  quantised output from step 1 is never staged.
- The subsequent fail-closed gates would not catch it: `verify()` passes on
  the valid bf16 source, and `--expect-bytes <measured>` only WARNS (non-fatal)
  when the measured quant-output byte count differs.
- Provenance is corrupted in two directions: the manifest would assert the Hub
  source identity for an artifact that (a) is the wrong variant if you wanted
  the conversion, or (b) is a mislabelled re-download if you wanted the pinned
  source. Either way the future sequence is non-reproducible: a reader of the
  config/provenance cannot tell what was actually benchmarked.
- Inherited ambiguity: `artifacts/qwen36-scheme-aware-conv-blocker-20260914.md`
  line 94 says the artifact "must be staged with `stage_mlx_checkpoint.py`
  provenance" without a command; the runbook supplied the command, and that
  command is the defective one corrected here.

## 4. Corrected future-machine handoff (staging a LOCAL conversion, with provenance)

On the qualifying machine, after runbook gates 1-4 (disk, RAM, tooling,
source-revision), `--help` capture, and the calibrated conversion:

1. **Convert to the final model root directly** — have the calibrated tool
   write its output INTO `<model-root>` (e.g. DWQ `--mlx-path <out>` per the
   conv-blocker's recorded, not-yet-executed example), or convert to scratch
   and then move the output contents into `<model-root>` so that `config.json`
   sits at the model-root top level. Do NOT invoke the staging script with
   `--repo` for a locally produced artifact — it has no local-input mode and
   will re-download the 65.42 GiB source.
2. **Verify + manifest WITHOUT download** — run
   `python3 /Users/tijs/projects/mei/tools/stage_mlx_checkpoint.py --verify-only
   --revision 04bbe07c3ed2d93cbf832f523fea344bca1d0fcf --target <model-root>`.
   `--verify-only` skips the Hub entirely; `verify()` checks config presence,
   shard set vs index, container format, and byte accounting, then writes
   `<model-root>.provenance.json` (repo=`"(verify-only)"`, revision fields =
   the passed pin). Passing `--revision` explicitly is REQUIRED: in
   verify-only mode an omitted `--revision` records `"main"` in the manifest.
3. **Gate on the verifier output, not on the manifest alone** — succeed only
   when `verify()` returns `ok:true` AND exit code 0, AND the reported
   `file_bytes` exactly equals the byte total measured at conversion time.
   `--expect-bytes` on its own only WARNS on mismatch and leaves the exit code
   0, so the equality check must be made by the operator/script and treated as
   a hard fail on any inequality (it is the one remaining detector for "wrong
   artifact staged").
4. **Preserve source + conversion provenance in a bench-side sidecar** — the
   script's manifest records only `(verify-only)` + the echoed revision and has
   no conversion fields. At conversion time, write a new dated artifact in this
   repo (append-only, mirroring the existing evidence artifacts) containing:
   the pinned source `mlx-community/Qwen3.6-35B-A3B-bf16` @
   `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf`; the full conversion CLI with
   every flag as pinned from the execution-time `mlx_lm.dwq --help` /
   `mlx_lm.dynamic_quant --help` output (never from documentation); calibration
   inputs (dataset, sample count, sequence length, batch); the conversion
   output byte totals; `sha256` of the staged `config.json`; the verifier's
   `file_bytes`/`payload_total`/`quant_bits`/`quant_group_size`/`quant_mode`;
   and the `<model-root>.provenance.json` path. Reference that sidecar from the
   benchmark config's provenance fields (same pattern already used in
   `configs/Ling-3.0-tiny/mei.yaml`).
5. **Continue with runbook steps 3-6 unchanged** — config gate (commit config
   first), candidate gate on the staged quant output, then benchmark, then
   append-only results. Nothing in this correction changes those steps.

Rejected alternative, recorded for completeness: adding a `--source-path` /
local-input mode to `stage_mlx_checkpoint.py` would be the cleanest long-term
fix, but it is a change inside `/Users/tijs/projects/mei` — out of scope for
this branch and NOT performed. The verify-only + sidecar handoff above needs no
mei change.

## 5. Limitations

- Source-inspection, not execution: the staged-tool behavior above is read from
  the script at mei HEAD `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a`; the
  verify-only staging path was not exercised here (no converted artifact exists
  on this Mac, and downloads/conversions are forbidden on this branch). The
  `mlx_lm.dwq` / `mlx_lm.dynamic_quant` option surface remains unexecuted, as
  before.
- Unknown-until-execution items on the future machine: whether the calibrated
  tool's output is a "normal model dir" with root `config.json` and a
  `model.safetensors.index.json`; `verify()` requires root `config.json` and,
  without an index, falls back to discovery mode with `payload_total=None`
  (shard format still checked). If conversion metadata does not land in
  `config["quantization"]`, the manifest's `quant_*` fields will be null and
  the sidecar must carry the quant parameters instead.
- `resolved_commit` in the manifest is an echo of the `--revision` literal, not
  a Hub query; treat it as a pin tag, and keep the read-only Hub revision check
  (runbook gate 4) as the real source-revision authority.
- Downgrade note: staging-as-written would consume an additional full 65.42 GiB
  byte copy under `--target` (the script disables symlinks) that the preflight
  disk accounting never included; the corrected handoff removes that copy
  entirely.

## 6. Status / result — 2026-09-15 (UTC 14:58:34)

- Confirmed: runbook step 2 as written stages the unquantised HF source, not
  the local conversion, and neither the verifier nor `--expect-bytes` would
  fail-closed on it; the future sequence is non-reproducible as documented.
- Corrected handoff in section 4; the runbook itself is left untouched
  (append-only).
- No experiment ran; no downloads, installs, conversions, servers, result rows,
  leaderboard changes, configs, runner/test edits, Kiem changes, or
  `/Users/tijs/projects/mei` mutations. This correction is committed on its
  own.

## Checks

- Before writing: bench repo `git status --porcelain` clean; HEAD
  `5fb50a80ad1867f1c6db5e1dbba100efc686357e` (branch `main`); mei inspected
  read-only at HEAD `950e8c2fdfa13ca6ed1dbfbd7794abc96705553a` (its untracked
  `Casks/` and `tap/` entries pre-existed and were not touched).
- After writing: `git status --porcelain` shows exactly one change
  (`?? artifacts/qwen36-scheme-aware-staging-correction-20260915.md`); only
  that file is committed (`git add` of that path only).
- `git diff --check` (against the staged commit) -> exit 0, no whitespace
  errors.
- Trailing-whitespace scan of this file (`[[:blank:]]$`) -> no matches.
# Qwen3.6-35B-A3B — mlx-lm source/release pin evidence: runbook tooling gate vs live PyPI / upstream main, 2026-09-15

Append-only evidence artifact for the Qwen3.6 future-machine scheme-aware MLX
quantisation branch. Records a provenance gap found by source inspection: the
runbook's tooling gate installs mlx-lm without pinning any version, release, or
source commit, while the live PyPI release (0.31.3, 2026-04-22) and current
upstream `main` (a45a61537c8d2725cf2a8a74b5d9963d0cd4c238, 2026-09-15) carry
later Qwen3.5/Qwen3.6-relevant changes. The gap and the recommended future
machine gate are recorded here.

This file complements (does NOT edit):
- the runbook `artifacts/qwen36-scheme-aware-runbook-20260915.md` (committed
  `bfc941f`; append-only — "do not edit it retroactively"),
- the correction `artifacts/qwen36-scheme-aware-runbook-correction-20260915.md`
  (committed `007160a`; pinned mlx-lm `main` at `d8f7f88` earlier the same
  day), and
- the source-revision check `artifacts/qwen36-future-source-revision-check-20260915.md`
  (committed `5fb50a8`).

No repository file is modified by this artifact: no runbook edit, no
`results/` or `results/LEADERBOARD.md` change, no `configs/`/runner/test edit,
no Kiem change, `/Users/tijs/projects/mei` untouched, no push/publish.

## 1. The finding (source inspection, exact quote)

The runbook's fail-closed **Tooling gate** (`qwen36-scheme-aware-runbook-20260915.md`,
line 42; step 3 of the preflight) says, verbatim:

```
pip install "mlx-lm[train]"
```

That command pins **no** mlx-lm version, no `==` release, no git commit, and no
install source. The gate then verifies import (`python -c 'import mlx_lm'`) and
console-script resolution (`which mlx_lm.dwq`), but it never records WHICH
mlx-lm was installed. Because DWQ / dynamic-quant calibration behavior is
source-version-sensitive (the correction note `007160a` already showed
documentation-vs-parser defaults disagreeing at one pinned commit), an
unpinned, unrecorded mlx-lm install is an unreproducible provenance gap for the
whole conversion→staging→gate→benchmark chain. The installed identity must be
captured before conversion; `--help` output alone is not enough.

The moving-target evidence: the correction note `007160a` (same day, earlier)
inspected mlx-lm `main` at `d8f7f88d8a1f730a761a49f59b2d547ce571f431`; upstream
`main` has since advanced to `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`
(2026-09-15T15:58:34Z, commit url
`https://github.com/ml-explore/mlx-lm/commit/a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`).
Live mlx-lm `main` is a moving target; only an explicit pin makes a future run
reproducible.

## 2. Independently re-queried facts (read-only source inspection; exact commands + timestamps)

All facts below were re-queried by this branch on 2026-09-15 at
`2026-09-15T17:32:27Z` (UTC) and `2026-09-15T17:32:39Z` (UTC). Method: read-only
REST GET requests (PyPI JSON API, GitHub REST API), responses parsed in a
throwaway `python3 -c` process. No mlx-lm package file was downloaded or saved;
metadata JSON only.

### PyPI release facts

Command: `curl -sS https://pypi.org/pypi/mlx-lm/json`

- Latest version: **0.31.3**
- Uploads (both at `https://pypi.org/project/mlx-lm/`): `mlx_lm-0.31.3-py3-none-any.whl`
  uploaded `2026-04-22T07:37:25Z`; `mlx_lm-0.31.3.tar.gz` uploaded
  `2026-04-22T07:37:27Z`.

### GitHub `main` HEAD facts

Command: `curl -sS https://api.github.com/repos/ml-explore/mlx-lm/commits/main`

- `sha`: `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`
- Committer date: `2026-09-15T15:58:34Z`
- Message: `laguna: load the public checkpoint layouts (original poolside + repacks) (#1704)`

### Qwen3.5/Qwen3.6-relevant commits on `main` (each re-queried at URL
`https://api.github.com/repos/ml-explore/mlx-lm/commits/<sha>`, plus an
ancestry check via `https://api.github.com/repos/ml-explore/mlx-lm/compare/a45a61537c8d2725cf2a8a74b5d9963d0cd4c238...<sha>`)

| commit | date (UTC) | message | files touched | in `main`? |
| --- | --- | --- | --- | --- |
| `0fd312649627` | 2026-02-12T15:23:51Z | `[MODEL] support qwen3.5 series w/o vision (#869)` | `mlx_lm/models/qwen3_5.py`, `mlx_lm/models/qwen3_5_moe.py`, `tests/test_models.py` | yes (compare status `behind`, behind_by 191, ahead_by 0) |
| `4eeaf20979bd` | 2026-08-18T02:19:59Z | `Fix Qwen3.6 converted norm sanitization (#1623)` | `mlx_lm/models/qwen3_5.py`, `tests/test_models.py` | yes (compare status `behind`, behind_by 91, ahead_by 0) |
| `1b3594b9c3a2` (full `1b3594b9c3a252b1c5d386424543b4cd6519d47c`) | 2026-09-09T01:31:01Z | `Lint/pyflakes unused code (#1860)` — most recent commit touching `mlx_lm/quant/dwq.py`, per `curl -sS "https://api.github.com/repos/ml-explore/mlx-lm/commits?path=mlx_lm/quant/dwq.py&per_page=1"` | `mlx_lm/quant/dwq.py` (among others in #1860) | yes (compare status `behind`, behind_by 30, ahead_by 0) |

Commit URLs: `https://github.com/ml-explore/mlx-lm/commit/0fd312649627`,
`https://github.com/ml-explore/mlx-lm/commit/4eeaf20979bd`,
`https://github.com/ml-explore/mlx-lm/commit/1b3594b9c3a2`,
`https://github.com/ml-explore/mlx-lm/commit/a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`.

Chronological takeaway (facts only): PyPI 0.31.3 was uploaded 2026-04-22;
upstream `main` contains Qwen3.5-MoE model support added 2026-02-12 (merged into
`main` well before 0.31.3) and a Qwen3.6 converted-norm sanitization fix
committed 2026-08-18 (after 0.31.3's upload), and its `mlx_lm/quant/dwq.py` was
last changed 2026-09-09 (after 0.31.3). Whether any of these differences
matters for this Mac's intended Qwen3.6 run is NOT concluded here — see section
4.

## 3. Source inspection vs execution — explicit separation

- Sections 1-2 are **source inspection only**: read-only metadata/source
  queries against PyPI and GitHub. They are NOT execution-time evidence.
- No `mlx_lm.dwq` or `mlx_lm.dynamic_quant` process ran for this artifact; the
  calibrated tools are not installed on this Mac (recorded in
  `qwen36-future-source-revision-check-20260915.md` and earlier artifacts:
  `uv run --locked python -c 'import mlx_lm'` → `ModuleNotFoundError`), and no
  `--help` output exists anywhere for this branch.
- **Explicit scope statement**: no package, model, or weights were installed or
  downloaded; no conversion or calibration ran; no Mei/llama.cpp server was
  launched or stopped; no `results/log.jsonl` row was appended; no
  `results/LEADERBOARD.md` change occurred; no `configs/`, runner, or test file
  changed; `/Users/tijs/projects/mei`, model roots, caches, and Casks/tap state
  untouched; nothing was pushed to any public remote.
- The recommended gate commands in section 5 are instructions for the future
  qualifying machine; they were NOT executed here.

## 4. Compatibility non-claim (explicit)

This artifact does **NOT** claim that PyPI 0.31.3 is incompatible with Qwen3.6,
nor that it lacks Qwen3.5/3.6 support. No compatibility assessment was
performed: asserting either way would require inspecting the 0.31.3 release
surface (its code or its runtime behavior on a machine with mlx), and package
download/execution is out of scope for this branch. What IS asserted is only
the chronological/provenance facts above (release upload date vs commit dates on
`main`). Whether the pinned install supports the Qwen3.6 source conversion must
be established on the qualifying machine from execution-time evidence
(`--help` output, import, and, if needed, a minimal convert probe) — never
from this file.

## 5. Recommended future-machine gate (before any conversion; runbook not edited here)

On the qualifying machine, after runbook preflight gates 1-4 pass and BEFORE the
calibrated conversion (in addition to the runbook's existing `--help` capture):

1. **Capture help verbatim** (already required by the runbook; re-affirmed):
   ```
   mlx_lm.dwq --help
   mlx_lm.dynamic_quant --help
   ```
   Record full output in a new dated artifact.
2. **Pin and record the exact installed identity BEFORE conversion** — record
   output verbatim in that same new dated artifact:
   ```
   python -m pip show mlx-lm
   python -c 'import mlx_lm; print(getattr(mlx_lm, "__version__", "NO __version__ attr")); print(mlx_lm.__file__)'
   ```
   and, when installed from a source checkout instead of PyPI:
   ```
   git -C <mlx-lm-checkout> rev-parse HEAD
   git -C <mlx-lm-checkout> describe --tags --always
   ```
3. **Install with an explicit pin** — e.g. `pip install "mlx-lm[train]==<exact-version>"`,
   or a source checkout pinned by commit SHA; never leave the runbook's
   unpinned `pip install "mlx-lm[train]"` as the last word on the qualifying
   machine. After install, re-run step 2 and record the RESOLVED version/commit
   so the recorded pin reflects what actually runs (a post-install record is
   the ground truth even if the install line was unpinned).
4. Gate decision on differences: if the `--help` output or the pinned
   version/commit suggests Qwen3.6-relevant behavior (e.g. the 2026-08-18 norm
   sanitization fix) is absent, STOP and record the finding in a new dated
   artifact; do not convert, do not claim an unverified release is
   incompatible — record only observed facts.

These commands were NOT executed on this Mac (no mlx-lm installed here; branch
rules forbid install/download on this machine).

## 6. Result / status — 2026-09-15

- Finding recorded: the runbook tooling gate's `pip install "mlx-lm[train]"`
  is unpinned; live PyPI latest is 0.31.3 (2026-04-22) and upstream `main` is
  a45a61537c8d2725cf2a8a74b5d9963d0cd4c238 (2026-09-15) carrying Qwen3.5-MoE
  support (commit 0fd312649627, 2026-02-12), the Qwen3.6 converted-norm
  sanitization fix (commit 4eeaf20979bd, 2026-08-18), and a later
  `mlx_lm/quant/dwq.py` change (commit 1b3594b9c3a2, 2026-09-09).
- No experiment executed, nothing installed or downloaded, no conversion, no
  server, no results/leaderboard change, no edit to any existing artifact or
  repository file. Branch status on this Mac remains: BLOCKED (disk ~22 GiB
  free, 32 GiB RAM, no mlx_lm in the locked env — per prior artifacts).
- This file is append-only evidence; it will not be edited retroactively.
  Future status changes belong in new, later-dated artifacts.

## Checks

- `git status --porcelain` before writing this file: clean; HEAD =
  `5a58c6acf9d3f1ffb02e9138884319436ef1de1d` (commit message:
  `artifacts: correct scheme-aware runbook staging step (--repo re-downloads source; use --verify-only + provenance sidecar)`),
  branch `main`.
- All external queries were read-only GETs (PyPI JSON API, GitHub REST API);
  response bodies were parsed in memory, nothing saved into the repository or
  the filesystem, no package/model/weights downloaded, nothing executed,
  installed, or converted.
- After writing this file: `git status --porcelain` shows exactly one change,
  `?? artifacts/qwen36-scheme-aware-mlxlm-pin-evidence-20260915.md` — no other
  file created or modified.
- `git diff --check` → exit 0, no whitespace errors.
- Trailing-whitespace scan of this file (`[[:blank:]]$`) → no matches.
- Code-fence balance: even count of ``` fence markers.
- Content spot-checks (grep): contains `pip install "mlx-lm[train]"`, `0.31.3`,
  `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`, `0fd312649627`,
  `4eeaf20979bd`, `1b3594b9c3a2`, the section-3 execution-exclusion statement,
  the section-4 non-claim, and the section-5 gate commands.
- Commit scope: only this artifact was staged and committed; nothing else.
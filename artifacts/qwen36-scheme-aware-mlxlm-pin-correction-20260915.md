# Qwen3.6-35B-A3B — mlx-lm tooling gate: exact source pin correction note, 2026-09-15

Append-only correction/evidence artifact for the Qwen3.6 future-machine
scheme-aware MLX quantisation branch. Closes the provenance gap recorded in
`artifacts/qwen36-scheme-aware-mlxlm-pin-evidence-20260915.md` (committed at
HEAD `660f9c9`): the runbook's fail-closed **Tooling gate** installs mlx-lm
with the unpinned, unreproducible command `pip install "mlx-lm[train]"`. This
note prescribes one concrete, exact source pin (upstream mlx-lm commit
`a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`), gives the exact future-machine
install command, and makes the post-install identity capture and the verbatim
`--help` captures mandatory before any conversion. The prior runbook and all
prior evidence artifacts are preserved unchanged (they are append-only; no
retroactive edit is made to any existing file).

This file complements (does NOT edit):
- the runbook `artifacts/qwen36-scheme-aware-runbook-20260915.md` (committed
  `bfc941f`; append-only — "do not edit it retroactively"),
- the pin evidence `artifacts/qwen36-scheme-aware-mlxlm-pin-evidence-20260915.md`
  (committed `660f9c9`; records the gap: unpinned runbook gate vs PyPI 0.31.3
  vs upstream `main` a45a61537c8d2725cf2a8a74b5d9963d0cd4c238),
- the DWQ defaults correction `artifacts/qwen36-scheme-aware-runbook-correction-20260915.md`
  (committed `007160a`; pinned mlx-lm `main` at `d8f7f88` earlier the same day),
- the source-revision check `artifacts/qwen36-future-source-revision-check-20260915.md`
  (committed `5fb50a8`).

No repository file other than this one is created or modified by this artifact:
no runbook edit, no `results/` or `results/LEADERBOARD.md` change, no
`configs/`/runner/test edit, no Kiem change, `/Users/tijs/projects/mei`
untouched, no publish, no push.

## 1. Pin decision — exact source commit, not a released version

**Chosen pin: upstream mlx-lm commit `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`
(upstream `main` HEAD, committer date `2026-09-15T15:58:34Z`, message
`laguna: load the public checkpoint layouts (original poolside + repacks) (#1704)`).**

Why a source commit and not a released pin: the recorded evidence
(`qwen36-scheme-aware-mlxlm-pin-evidence-20260915.md`, section 2) shows the
latest PyPI release is `0.31.3`, uploaded `2026-04-22T07:37:25Z`, while
upstream `main` carries Qwen3.6-relevant commits dated AFTER that upload:
the Qwen3.6 converted-norm sanitization fix (`4eeaf20979bd`, 2026-08-18) and
the most recent change to `mlx_lm/quant/dwq.py` (`1b3594b9c3a2`, 2026-09-09).
The evidence records no released version newer than 0.31.3, so **no stronger
exact released pin can be established from the existing evidence** — choosing
0.31.3 would pin a release that predates the recorded Qwen3.6 norm fix and the
recorded later `dwq.py` change, and would require a Qwen3.6 compatibility
claim that the evidence artifact explicitly declines to make (its section 4
non-claim). The recorded upstream `main` HEAD commit is therefore the strongest
exact, evidence-backed pin available without downloading or installing
anything. Whether the pinned commit actually supports the Qwen3.6 source
conversion is NOT claimed here — that is established on the qualifying machine
from execution-time evidence only (`--help`, import, `pip show`), exactly as
the evidence artifact's gate requires.

Re-verified read-only for this note (REST GET, response parsed in memory,
nothing downloaded/saved/executed), same session as the checks in section 7:

```
curl -sS https://api.github.com/repos/ml-explore/mlx-lm/commits/a45a61537c8d2725cf2a8a74b5d9963d0cd4c238
```

→ `sha=a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`,
committer date `2026-09-15T15:58:34Z`, first message line
`laguna: load the public checkpoint layouts (original poolside + repacks) (#1704)` —
exact match with the recorded evidence.

## 2. Exact future-machine install command (replaces the runbook's unpinned line)

The runbook's tooling-gate line `pip install "mlx-lm[train]"` is superseded on
the qualifying machine by this exact pinned command (the runbook file itself is
not edited; this correction is recorded here):

```
pip install "mlx-lm[train] @ git+https://github.com/ml-explore/mlx-lm@a45a61537c8d2725cf2a8a74b5d9963d0cd4c238"
```

PEP 508 direct git reference: the `[train]` extras are preserved (required for
the calibrated DWQ / dynamic-quant tools) and the source is pinned to exactly
the commit above. (If the qualifying machine's pip is old enough to reject
extras on a direct reference, the equivalent legacy form is
`pip install "git+https://github.com/ml-explore/mlx-lm@a45a61537c8d2725cf2a8a74b5d9963d0cd4c238#egg=mlx-lm[train]"`.)

Companion checkout variant (used when a local source checkout is desired so the
checkout SHA can be captured directly; keeps the identical commit pin):

```
git clone https://github.com/ml-explore/mlx-lm.git
git -C mlx-lm checkout a45a61537c8d2725cf2a8a74b5d9963d0cd4c238
pip install -e "./mlx-lm[train]"
```

After EITHER form, the post-install captures in section 3 are mandatory, and
the RESOLVED identity they record is the ground truth for what actually runs —
if it differs from the pin, STOP and record the mismatch in a new dated
artifact (do not convert).

## 3. Required post-install identity capture (before any conversion, verbatim into a new dated artifact)

Run all of these after the install and record output verbatim:

```
python -m pip show mlx-lm
python -c 'import mlx_lm; print(getattr(mlx_lm, "__version__", "NO __version__ attr")); print(mlx_lm.__file__)'
```

and, when the checkout variant (section 2) is used — or when `mlx_lm.__file__`
shows the install came from the git reference's build dir:

```
git -C <mlx-lm-checkout> rev-parse HEAD
git -C <mlx-lm-checkout> describe --tags --always
```

Required outcomes: `pip show mlx-lm` resolves to an mlx-lm install whose source
identity is recorded; `mlx_lm.__file__` is recorded verbatim; the version
attribute (`__version__` or its explicit absence) is recorded verbatim; and the
recorded checkout SHA must equal `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`
exactly when a checkout was used. This captures WHICH mlx-lm runs before any
conversion, closing the gap that the evidence artifact documented.

## 4. Required pre-conversion help capture (verbatim, before any conversion)

Already required by the runbook; re-affirmed as mandatory and recorded in the
same new dated artifact, BEFORE any conversion:

```
mlx_lm.dwq --help
mlx_lm.dynamic_quant --help
```

These execution-time outputs are the sole authoritative option surface for the
eventual run (per runbook and correction note `007160a`); never guess flags
from documentation or from this file.

## 5. Explicit scope statement — none of this was executed on this Mac

- No install ran here; no `pip install` command in this note was executed on
  this Mac; no mlx-lm package or weights were downloaded; no `mlx_lm.dwq` /
  `mlx_lm.dynamic_quant` process ran; no `--help` output exists for this
  branch; no conversion or calibration ran; no server launched or stopped; no
  `results/log.jsonl` row appended; no `results/LEADERBOARD.md` change; no
  `configs/`, runner, or test file changed; `/Users/tijs/projects/mei`, model
  roots, and caches untouched; nothing pushed or published.
- Section 2's install commands and sections 3-4's capture commands are
  instructions for the future qualifying machine only.
- The only live checks performed for this note were read-only and
  side-effect-free (see section 7).

## 6. Gate-before-conversion / results boundary (unchanged, re-stated)

Order on the qualifying machine, fail-closed: (1) runbook preflight gates 1-2
pass (disk >= ~105 GiB free; RAM sufficient for ~66 GiB bf16 residency) —
both STILL FAIL on this Mac (section 7); (2) the pinned install from section 2
plus the section 3 identity capture and section 4 `--help` capture, all
recorded verbatim in a new dated artifact; (3) runbook gate 4 source-revision
check; (4) ONLY then the calibrated conversion from the pinned bf16 source;
(5) staging, committed config, candidate gate — and NO `results/log.jsonl` row
and NO leaderboard entry may be written until the candidate gate passes.
Sections 1-5 add a mandatory pinned-tooling gate in front of the existing
staged order; they do not relax any runbook stop condition.

## 7. Current blockers on this Mac (re-measured 2026-09-15)

Measured in the same read-only terminal session as this note's GitHub re-query
(`date -u` → `2026-09-15T18:39:48Z`):

- **Disk** — `df -k /System/Volumes/Data`: available `23040432` KiB
  (≈ 21.97 GiB), far below the runbook floor (>= ~105 GiB free incl. the
  ~65 GiB bf16 source). Gate 1: FAIL.
- **RAM** — `sysctl hw.memsize` = `34359738368` (32 GiB), insufficient for the
  ~66 GiB bf16 source residency. Gate 2: FAIL.
- **Tooling** — `uv run --locked --no-sync python -c 'import mlx_lm'` → exit
  code 1, `ModuleNotFoundError: No module named 'mlx_lm'` (no environment sync,
  no install). Gate 3 as written: FAIL; the pinned install in section 2 does
  not exist on this Mac.

Pinned model source revision (preserved unchanged from the runbook, verbatim):
`mlx-community/Qwen3.6-35B-A3B-bf16` at
`04bbe07c3ed2d93cbf832f523fea344bca1d0fcf` — 14 safetensors shards plus
metadata, total file bytes 70,241,335,712 (65.42 GiB). Reuse the exact
`<repo>@<40-hex>` form verbatim for provenance on the future run.

## 8. Result / status — 2026-09-15

- The provenance gap is now closed on paper: the unpinned runbook tooling-gate
  line is superseded by the exact source pin
  `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238` with mandatory post-install
  identity capture and mandatory verbatim `--help` capture before any
  conversion. The prior runbook and prior evidence artifacts are byte-for-byte
  unchanged.
- This Mac remains BLOCKED (disk ≈ 21.97 GiB free, 32 GiB RAM, no mlx_lm in
  the locked env). None of the prescribed commands were executed here.
- This file is append-only evidence; it will not be edited retroactively.
  Future status changes belong in new, later-dated artifacts.

## Checks

- `git status --porcelain` before writing this file: clean; HEAD =
  `660f9c9dc34d7e20de767237bc91c0fe0eaa0a5b` (commit message: `artifacts:
  record mlx-lm source/release pin evidence for scheme-aware Qwen3.6 gate
  (runbook pip install unpinned; PyPI 0.31.3 vs main a45a615; no execution)`),
  branch `main`.
- External queries were read-only REST GETs (GitHub commits API); response
  parsed in memory, nothing saved into the repository or filesystem; local
  probes were `df -k`, `sysctl hw.memsize`, and the `--no-sync` locked-env
  import probe (no environment sync, no install). Nothing downloaded,
  installed, converted, or executed beyond these read-only checks.
- After writing this file: `git status --porcelain` shows exactly one change,
  `?? artifacts/qwen36-scheme-aware-mlxlm-pin-correction-20260915.md` — no
  other file created or modified.
- `git diff --check` → exit 0, no whitespace errors.
- Trailing-whitespace scan of this file (`[[:blank:]]$`) → no matches.
- Code-fence balance: even count of ``` fence markers.
- Content spot-checks (grep): contains `a45a61537c8d2725cf2a8a74b5d9963d0cd4c238`,
  `pip install "mlx-lm[train] @ git+...`, `python -m pip show mlx-lm`,
  `mlx_lm.dwq --help`, `mlx_lm.dynamic_quant --help`,
  `04bbe07c3ed2d93cbf832f523fea344bca1d0fcf`, the section-5 not-executed
  statement, and the section-6 gate/results boundary.
- Commit scope: only this artifact was staged and committed; nothing else.
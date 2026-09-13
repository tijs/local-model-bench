# Qwen3.6-focused artifact cleanup — 2026-09-13

## Scope

Tijs authorized cleanup of obsolete worktrees and model/cache artifacts after
changing the research direction to Qwen3.6 variants and new model quantisations.
This cleanup removed only the explicit paths below. Historical benchmark rows,
configs, reports, Kiem notes, provenance sidecars, and Git branch refs were
retained.

Timestamp: `2026-09-13T21:06:18Z` (pre/post verification window)

## Pre-delete gate

- No Claude Code, Mei, benchmark runner, llama.cpp, vLLM, oMLX, Swift test/build,
  or Xcode process was active.
- No listener existed on benchmark ports 8012–8029.
- `lsof` reported no open handle for any deletion target.
- Canonical repositories were not modified by this cleanup:
  - `/Users/tijs/projects/mei`: `main` at `50fd9ab`; pre-existing untracked
    `Casks/kiem.rb` and `tap/` were preserved.
  - `/Users/tijs/projects/vmlx-swift`: `main` at `e37d1d5`; clean with both
    submodules intact.
  - `/Users/tijs/projects/local-model-bench`: `main` at `3969328`; clean before
    this evidence file was added.
- Dirty old Mei worktrees were deliberately left in place so their uncommitted
  dependency/tap changes were not destroyed:
  `/private/tmp/mei-fidelity-probe`, `mei-adaptive`, `mei-c2`, `mei-c3`,
  `mei-capture`, `mei-rc`, and `mei-strict`.

Pre-delete filesystem snapshot: `df -h /` reported `16 GiB` used and `19 GiB`
available (`46%`).

## Recoverability checks

The public Hugging Face model API returned `private: false` for every retired
model repository:

- `ornith-ai/Ornith-1.5-35B-A3B-GGUF` — API revision
  `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`. The local cache held the public
  `Q4_K_M` file (`21713463040` bytes) and BF16 mmproj
  (`902822240` bytes); the public tree still exposes both.
- `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit` — API revision
  `19504d912fa8fc7622bf6b1de3db5d5d890b1f02`, with four public safetensor
  shards. The retired local copy was an aligned staged derivative; its
  provenance sidecar remains as historical evidence.
- `mlx-community/Qwen3.5-9B-8bit` — API revision
  `16daa4818c54ce5f5436f929d52542eb65bbed9d`, with two public safetensor
  shards. The local HF entry contained only a small `refs/main` file.
- `mlx-community/Qwen2.5-0.5B-Instruct-4bit` — API revision
  `a5339a4131f135d0fdc6a5c8b5bbed2753bbe0f3`; its public
  `model.safetensors` is `278064920` bytes. The staged local copy was a test
  fixture, not a current research candidate.

## Retained set

### Qwen3.6 staged models

All three staged candidates remained present and passed key-file checks after
cleanup (each has `config.json`, `generation_config.json`,
`model.safetensors.index.json`, and four safetensor shards):

- `~/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit`
  — `20429299712` bytes on disk.
- `~/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit-textonly`
  — `19536060416` bytes on disk.
- `~/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-mixed46-aligned`
  — `20050526208` bytes on disk.

Their Qwen3.6 provenance sidecars were retained. The HF cache entries retained
were the exact Qwen3.6 stock, DWQ, and EigenLabs mixed-4bit repository directories:

- `~/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-4bit`
- `~/.cache/huggingface/hub/models--mlx-community--Qwen3.6-35B-A3B-4bit-DWQ`
- `~/.cache/huggingface/hub/models--EigenLabs--Qwen3.6-35B-A3B-MLX-mixed-4bit`

They were currently refs-only entries (`4096` bytes each); they remain so future
pinned downloads and new quantisation work use the intended research set.

Historical provenance sidecars for Laguna, Ornith, Ternary Bonsai, and Qwen3.6
were retained. They are small evidence files, not active model payloads.

## Exact deleted paths and pre-delete sizes

### Clean Mei worktrees

These worktrees were clean in preflight; their local branch refs remain in the
canonical Mei repository:

- `mei-040` — `550957056` bytes
- `mei-041` — `3317760` bytes
- `mei-050` — `5106118656` bytes
- `mei-align` — `2344480768` bytes
- `mei-bisect` — `3403776` bytes
- `mei-d3` — `3268608` bytes
- `mei-laguna` — `3268608` bytes
- `mei-opt-research` — `3559424` bytes
- `mei-profiles` — `4700442624` bytes
- `mei-release` — `1352998912` bytes
- `mei-seed` — `4536557568` bytes
- `mei-syncwt` — `4682829824` bytes
- `mei-ux` — `3313664` bytes

### Clean vmlx and benchmark worktrees

- `fidelity/vmlx-release` — `35336192` bytes
- `fidelity/vmlx-swift` — `48160768` bytes
- `vmlx-040` — `35057664` bytes
- `vmlx-c3` — `48128000` bytes
- `vmlx-pr-453` — `48128000` bytes
- `vmlx-pr-454` — `48115712` bytes
- `vmlx-pr-laguna` — `310243328` bytes
- `local-model-bench-postfix` — `204951552` bytes

The vmlx worktrees containing submodules required `git worktree remove --force`
after their clean preflight was confirmed. The canonical vmlx checkout and both
submodules were verified afterward.

### Retired model/cache artifacts

- `~/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-35B-A3B-GGUF` —
  `22616293376` bytes
- `~/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-35B-A3B-MLX-4bit` —
  `4096` bytes
- `~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-9B-8bit` — `4096`
  bytes
- `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-0.5B-Instruct-4bit` —
  `4096` bytes
- `~/.local/share/local-model-bench/mei-models/Ornith-1.5-35B-A3B-MLX-4bit-aligned`
  — `19531042816` bytes
- `~/.local/share/local-model-bench/mei-models/Qwen2.5-0.5B-Instruct-4bit` —
  `289681408` bytes

Pre-delete aggregate for the explicit allowlist: `66509668352` bytes
(`61.94 GiB`, using `du -sk` on each absolute path). HF `.locks` data was not
pruned because it was outside the authorized allowlist.

## Post-delete verification

- Every explicit deletion target is absent.
- All three retained staged Qwen3.6 roots exist, with four shards and required
  metadata each.
- No `*.incomplete` file exists under the retained HF hub or Mei model root.
- The HF hub now contains only the three Qwen3.6 model directories listed above.
- Removed worktree branches remain recoverable as local refs, including
  `feat/request-log`, `release/0.5.0`, `research/hybrid-superopt`,
  `sync/0.4.2-plus-upstream`, `fix/issue-454-rotating-cache-boundary`, and
  `fix/laguna-language-model-prefix`.
- No Claude/model/benchmark process or listener was present after cleanup.

Post-delete filesystem snapshot: `df -h /` reported `16 GiB` used and `79 GiB`
available (`17%`). The observed availability increase is consistent with the
`61.94 GiB` explicit deletion aggregate, subject to filesystem accounting and
rounding.

No GitHub or Hugging Face publication was performed.

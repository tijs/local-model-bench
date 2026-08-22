#!/usr/bin/env bash
# Create/update the isolated pinned oMLX runtime used by this repository.
# The benchmark runner itself is always invoked with `uv run`; oMLX remains a
# separate uv-managed environment because its patched MLX stack must not share
# dependencies or caches with the runner/vllm-mlx environment.
set -euo pipefail

ROOT="${LOCAL_MODEL_BENCH_DATA_ROOT:-$HOME/.local/share/local-model-bench}"
SRC="${OMLX_SRC:-$ROOT/omlx-src}"
VENV="${OMLX_VENV:-$ROOT/omlx-venv}"
REPO_URL="${OMLX_REPO_URL:-https://github.com/jundot/omlx.git}"
REF="f2d36f3d25a7e7a2401a92eecafc28b8f8968ec7"
PYTHON="${OMLX_PYTHON:-3.12}"

mkdir -p "$ROOT"

if [[ ! -d "$SRC/.git" ]]; then
  git clone --filter=blob:none "$REPO_URL" "$SRC"
fi

actual="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || true)"
if [[ "$actual" != "$REF" ]]; then
  if [[ -n "$(git -C "$SRC" status --porcelain)" ]]; then
    printf 'Refusing to change dirty oMLX checkout: %s\n' "$SRC" >&2
    exit 1
  fi
  git -C "$SRC" fetch --tags --force origin "$REF"
  git -C "$SRC" checkout --detach "$REF"
fi

uv venv --python "$PYTHON" "$VENV"
uv pip install --python "$VENV/bin/python" --editable "$SRC"
# Keep the benchmark's validated MLX stack explicit even if oMLX's upstream
# dependency ranges become broader later.
uv pip install --python "$VENV/bin/python" \
  "mlx==0.32.0" \
  "mlx-lm==0.31.3"

printf 'oMLX source: %s (%s)\n' "$SRC" "$REF"
printf 'oMLX runtime: %s\n' "$VENV/bin/omlx"
"$VENV/bin/omlx" --version 2>/dev/null || true

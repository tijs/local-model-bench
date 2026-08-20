#!/bin/bash
# Builds llama.cpp from the official ggml-org/llama.cpp mainline at HEAD,
# needed for configs/*/gguf-dspark.yaml (LFM2 DSpark speculative decoding).
#
# Why this exists instead of just using Homebrew's llama.cpp: DSpark's
# generic support merged via PR #25173 (2026-07-28), but LFM2-model-specific
# support merged via PR #27383 only on 2026-08-20 — AFTER the installed
# Homebrew bottle (build 10470, commit 34af94cd9, dated 2026-08-17) was cut.
# `brew upgrade llama.cpp` found no newer bottle yet (Homebrew bottles lag
# mainline merges by hours to days). Unlike DFlash2, this is real, merged,
# official upstream code — just not yet bottled — so a plain mainline clone
# at HEAD is all that's needed, no third-party fork.
#
# Usage: runner/setup_dspark_head.sh [output-dir]
# Default output-dir: runner/.dspark-head (gitignored, not committed — a
# full llama.cpp checkout + build, too large/volatile for git).
set -euo pipefail

OUT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/runner/.dspark-head}"

if [ -x "$OUT_DIR/build/bin/llama-server" ]; then
  echo "Already built: $OUT_DIR/build/bin/llama-server"
  exit 0
fi

command -v cmake >/dev/null || { echo "Installing cmake + ninja via brew..."; brew install cmake ninja; }

rm -rf "$OUT_DIR"
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$OUT_DIR"
cmake -B "$OUT_DIR/build" -S "$OUT_DIR" -G Ninja -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build "$OUT_DIR/build" --target llama-server

echo "Built: $OUT_DIR/build/bin/llama-server"
echo "Use this binary in place of Homebrew's llama-server for gguf-dspark.yaml's benchmark_launch_command."

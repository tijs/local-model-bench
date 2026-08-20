#!/bin/bash
# Builds the llama.cpp fork with real DFlash2 support (z-lab/llama.cpp-fork,
# branch dflash2), needed for configs/Qwen3.8-27B/gguf-dflash2.yaml.
#
# Why this exists instead of just using Homebrew's llama.cpp: DFlash2's
# actual tensor-loading/decode logic lives only in ggml-org/llama.cpp PR
# #27342 (open/unmerged at time of writing). Homebrew's build has the
# --spec-type draft-dflash CLI flag but not the PR's implementation, which
# produces a misleading "wrong number of tensors; expected 81, got 58"
# error that looks like a checkpoint problem but isn't — see AGENTS.md's
# DFlash 2 section for the full story.
#
# Usage: runner/setup_dflash2_fork.sh [output-dir]
# Default output-dir: runner/.dflash2-fork (gitignored, not committed —
# it's a full llama.cpp checkout + build, too large/volatile for git).
set -euo pipefail

OUT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/runner/.dflash2-fork}"

if [ -x "$OUT_DIR/build/bin/llama-server" ]; then
  echo "Already built: $OUT_DIR/build/bin/llama-server"
  exit 0
fi

command -v cmake >/dev/null || { echo "Installing cmake + ninja via brew..."; brew install cmake ninja; }

rm -rf "$OUT_DIR"
git clone --depth 1 --branch dflash2 https://github.com/z-lab/llama.cpp-fork.git "$OUT_DIR"
cmake -B "$OUT_DIR/build" -S "$OUT_DIR" -G Ninja -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build "$OUT_DIR/build" --target llama-server

echo "Built: $OUT_DIR/build/bin/llama-server"
echo "Use this binary in place of Homebrew's llama-server for gguf-dflash2.yaml's benchmark_launch_command."

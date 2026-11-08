#!/bin/bash
# Materialize exact local git objects without changing either dependency checkout.
set -euo pipefail
case "${1:-}" in
  /Volumes/Expansion/local-model-bench/*) destination=$1 ;;
  *) echo "Provide a new absolute output directory on Expansion" >&2; exit 2 ;;
esac
test "$#" = 1
test "$(dirname "$destination")" = /Volumes/Expansion/local-model-bench
test -d /Volumes/Expansion/local-model-bench
here=$(cd "$(dirname "$0")" && pwd)
projects=/Users/tijs/projects
release="$projects/vmlx-mei-upstream-sync-20261106"
candidate="$projects/vmlx-mei-apple-core-main-20261107"
release_lock="$release/Package.resolved"
mei_lock="$projects/mei-apple-core-main-20261107/Package.resolved"
release_vmlx=3cb7240a39d92475345c6c1d0c9057da31a2f289
candidate_vmlx=19379503d289cd72f51f958df9c027f3c517829a
pin_list() {
  jq -er '[.pins[] | select(.identity != "vmlx-swift") |
    {identity, location, state}] | sort_by(.identity) | select(length > 0)' "$1"
}
release_pins=$(pin_list "$release_lock")
candidate_pins=$(pin_list "$mei_lock")
test "$release_pins" = "$candidate_pins"
jq -e --arg revision "$candidate_vmlx" '
  any(.pins[]; .identity == "vmlx-swift" and .state.revision == $revision)
' "$mei_lock" >/dev/null

mkdir "$destination"
printf '%s\n' "$release_pins" > "$destination/external-pins.json"
stage() {
  local repo=$1 revision=$2 core=$3 bridge=$4 output=$5 module
  test "$(git -C "$repo" rev-parse "$revision:Source/Cmlx/mlx")" = "$core"
  test "$(git -C "$repo" rev-parse "$revision:Source/Cmlx/mlx-c")" = "$bridge"
  mkdir "$output"
  git -C "$repo" archive "$revision" | tar -xf - -C "$output"
  for module in mlx mlx-c; do
    local pin="$core"
    if test "$module" = mlx-c; then pin="$bridge"; fi
    mkdir -p "$output/Source/Cmlx/$module"
    git -C "$repo/Source/Cmlx/$module" archive "$pin" |
      tar -xf - -C "$output/Source/Cmlx/$module"
  done
  cp "$release_lock" "$output/Package.resolved"
  test ! -e "$output/Tests/MLXLMTests/QwenDecodeCaptureTests.swift"
  cp "$here/QwenDecodeCaptureTests.swift" "$output/Tests/MLXLMTests/"
  jq -n --arg vmlx "$revision" --arg core "$core" --arg bridge "$bridge" \
    '{vmlx:$vmlx,core:$core,mlx_c:$bridge}' > "$output/trace-source.json"
  shasum -a 256 "$output/Package.resolved" "$output/Tests/MLXLMTests/QwenDecodeCaptureTests.swift" \
    > "$output/trace-inputs.sha256"
}
stage "$release" "$release_vmlx" 49631e976f01ba148abf4b041ca61ff2f1d5bfdd \
  a69a7c5c08691025d38325b200d1cccdeff9236e "$destination/control"
stage "$candidate" "$candidate_vmlx" b06cc4dc5af50e281b1b6309b2f7b79719fa9427 \
  1169bf6796e05e5857f8d40af5a66b361df3ae5b "$destination/candidate"

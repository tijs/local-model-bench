#!/bin/bash
# Reuse the diagnostic scratch after the Cmlx-only build exits. Never load that binary.
set -euo pipefail
test "$#" -eq 1
build=$1
root=/Volumes/Expansion/local-model-bench
test "$(dirname "$build")" = "$root"
test -d "$build"
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
source=/Users/tijs/projects/mei-apple-core-main-20261107
receipt="$here/build-receipt.json"
old_product="$root/mei-apple-core-main-20261107.zXe1uE/out/Products/Release"
product="$build/out/Products/Release"
compiler=/Applications/Xcode.app/Contents/Developer
vmlx="$build/checkouts/vmlx-swift"
hash() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{ print $1 }'; }
check() { test "$(git -C "$1" rev-parse HEAD)" = "$(jq -er "$2" "$receipt")"; }

test "$(sysctl -n kern.memorystatus_vm_pressure_level)" = 1
if lsof -nP -iTCP:8017 -iTCP:8024 -sTCP:LISTEN; then
  echo 'Benchmark port is occupied' >&2
  exit 1
fi
for volume in "$here" "$root"; do
  test "$(df -k "$volume" | awk 'END {print $4}')" -ge 24117248
done
check "$source" .mei
check "$vmlx" .vmlx
check "$vmlx/Source/Cmlx/mlx" .core
check "$vmlx/Source/Cmlx/mlx-c" .mlx_c
test "$(hash "$old_product/mlx.metallib")" = "$(jq -er .release.metallib_sha256 "$receipt")"

archived="$build/cmlx-only-unqualified"
mkdir "$archived"
for artifact in build.log manifest-change.diff built-assets.sha256 metal-eval-disassembly.txt; do
  if test -f "$build/$artifact"; then cp "$build/$artifact" "$archived/"; fi
done
for artifact in mei mlx.metallib; do
  if test -f "$product/$artifact"; then cp -c "$product/$artifact" "$archived/"; fi
done
if test -f "$archived/mei"; then shasum -a 256 "$archived/mei" > "$archived/mei.sha256"; fi
uv run --project "$repo" --locked python "$here/patch_release_ndebug.py" "$vmlx"
git -C "$vmlx" diff --check
test "$(git -C "$vmlx" diff --numstat)" = "$(printf '2\t0\tPackage.swift')"
git -C "$vmlx" diff -- Package.swift > "$build/aligned-manifest.diff"

export DEVELOPER_DIR=$compiler
lock_sha=$(hash "$source/Package.resolved")
env -i HOME="$HOME" PATH=/usr/bin:/bin:/usr/sbin:/sbin DEVELOPER_DIR="$compiler" \
  xcrun swift build --package-path "$source" --scratch-path "$build" \
  --build-system swiftbuild --configuration release --jobs 3 \
  --disable-automatic-resolution --product mei > "$build/aligned-build.log" 2>&1
test "$lock_sha" = "$(hash "$source/Package.resolved")"
git -C "$vmlx" diff -- Package.swift | cmp - "$build/aligned-manifest.diff"
check "$vmlx/Source/Cmlx/mlx" .core
check "$vmlx/Source/Cmlx/mlx-c" .mlx_c

for target in Cmlx CmlxGraphShim; do
  args_dir="$build/out/Intermediates.noindex/mlx-swift.build/Release/$target-t.build/Objects-normal/arm64"
  for args in "$args_dir/"*common-args.resp; do
    grep -Eq '(^|[[:space:]])-DNDEBUG(=1)?([[:space:]]|$)' "$args"
    shasum -a 256 "$args"
  done
done > "$build/aligned-cxx-flags.sha256"
bundle_metal="$product/mlx-swift_Cmlx.bundle/Contents/Resources/default.metallib"
test -s "$bundle_metal"
shasum -a 256 "$bundle_metal" > "$build/aligned-generated-metal.sha256"
cp -f "$old_product/mlx.metallib" "$bundle_metal"
cp -f "$old_product/mlx.metallib" "$product/mlx.metallib"
cmp "$bundle_metal" "$product/mlx.metallib"
xcrun llvm-objdump --disassemble-symbols=__ZN3mlx4core3gpu4evalERNS0_5arrayE "$product/mei" \
  > "$build/aligned-metal-eval.txt"
grep -q 'needs_commit' "$build/aligned-metal-eval.txt"
nm "$product/mei" > "$build/aligned-symbols.txt"
if grep -Eq 'verify_graph|has_invalid_memory|[0-9](track_allocation|untrack_allocation|swap_allocation)' \
  "$build/aligned-metal-eval.txt" "$build/aligned-symbols.txt"; then
  echo 'Unexpected debug graph or allocation tracking in the Release binary' >&2
  exit 1
fi
shasum -a 256 "$product/mei" "$product/mlx.metallib" "$source/Package.resolved" \
  "$build/aligned-manifest.diff" "$build/aligned-cxx-flags.sha256" \
  "$build/aligned-metal-eval.txt" > "$build/aligned-assets.sha256"
echo "ABI-consistent diagnostic artifact ready: $product/mei"

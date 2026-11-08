#!/bin/bash
# Build a separate diagnostic artifact. Run only when the benchmark is idle.
set -euo pipefail

test "$#" -eq 1
new=$1
root=/Volumes/Expansion/local-model-bench
test "$(dirname "$new")" = "$root"
test ! -e "$new"
original="$root/mei-apple-core-main-20261107.zXe1uE"
source=/Users/tijs/projects/mei-apple-core-main-20261107
here=$(cd "$(dirname "$0")" && pwd)
receipt="$here/build-receipt.json"
compiler=/Applications/Xcode.app/Contents/Developer
original_product="$original/out/Products/Release"
original_metal="$original_product/mlx.metallib"
hash() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{ print $1 }'; }
check() {
  test "$(git -C "$1" rev-parse HEAD)" = "$(jq -er "$2" "$receipt")"
  test -z "$(git -C "$1" status --porcelain --untracked-files=no)"
}
test "$(sysctl -n kern.memorystatus_vm_pressure_level)" = 1
if lsof -nP -iTCP:8017 -iTCP:8024 -sTCP:LISTEN; then
  echo 'Benchmark port is occupied' >&2
  exit 1
fi
for volume in "$here" "$root"; do
  test "$(df -k "$volume" | awk 'END {print $4}')" -ge 24117248
done
check "$source" .mei
test "$(hash "$original_product/mei")" = "$(jq -er .release.sha256 "$receipt")"
test "$(hash "$original_metal")" = "$(jq -er .release.metallib_sha256 "$receipt")"

mkdir "$new"
for item in checkouts repositories artifacts prebuilts workspace-state.json; do
  /bin/cp -cR "$original/$item" "$new/"
done
vmlx="$new/checkouts/vmlx-swift"
check "$vmlx" .vmlx
check "$vmlx/Source/Cmlx/mlx" .core
check "$vmlx/Source/Cmlx/mlx-c" .mlx_c
key='    cxxSettings: cxxSettings + ['
test "$(grep -Fxc "$key" "$vmlx/Package.swift")" = 1
chmod u+w "$vmlx/Package.swift"
sed -i '' '/^    cxxSettings: cxxSettings + \[$/a\
        .define("NDEBUG", .when(configuration: .release)),
' "$vmlx/Package.swift"
git -C "$vmlx" diff --check
git -C "$vmlx" diff -- Package.swift > "$new/manifest-change.diff"
test "$(git -C "$vmlx" diff --numstat)" = "$(printf '1\t0\tPackage.swift')"

export DEVELOPER_DIR=$compiler
lock_sha=$(hash "$source/Package.resolved")
env -i HOME="$HOME" PATH=/usr/bin:/bin:/usr/sbin:/sbin DEVELOPER_DIR="$compiler" \
  xcrun swift build --package-path "$source" --scratch-path "$new" \
  --build-system swiftbuild --configuration release --jobs 3 \
  --disable-automatic-resolution --product mei > "$new/build.log" 2>&1
test "$lock_sha" = "$(hash "$source/Package.resolved")"
git -C "$vmlx" diff -- Package.swift | cmp - "$new/manifest-change.diff"
check "$vmlx/Source/Cmlx/mlx" .core
check "$vmlx/Source/Cmlx/mlx-c" .mlx_c

product="$new/out/Products/Release"
bundle_metal="$product/mlx-swift_Cmlx.bundle/Contents/Resources/default.metallib"
test -s "$bundle_metal"
shasum -a 256 "$bundle_metal" > "$new/generated-metal.sha256"
# Use the exact original Metal bytes so the comparison isolates host C++.
cp -f "$original_metal" "$bundle_metal"
cp -f "$original_metal" "$product/mlx.metallib"
cmp "$bundle_metal" "$product/mlx.metallib"
test "$(hash "$product/mlx.metallib")" = "$(jq -er .release.metallib_sha256 "$receipt")"

xcrun llvm-objdump --disassemble-symbols=__ZN3mlx4core3gpu4evalERNS0_5arrayE "$product/mei" \
  > "$new/metal-eval-disassembly.txt"
grep -q 'needs_commit' "$new/metal-eval-disassembly.txt"
/usr/bin/nm "$product/mei" > "$new/symbols.txt"
if grep -Eq 'verify_graph|has_invalid_memory|[0-9](track_allocation|untrack_allocation|swap_allocation)' \
  "$new/metal-eval-disassembly.txt" "$new/symbols.txt"; then
  echo 'Unexpected debug graph or allocation tracking in the Release binary' >&2
  exit 1
fi
shasum -a 256 "$product/mei" "$product/mlx.metallib" "$source/Package.resolved" \
  "$new/manifest-change.diff" > "$new/built-assets.sha256"
echo "Diagnostic artifact ready: $product/mei"

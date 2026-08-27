// swift-tools-version:5.9
import PackageDescription

// platforms explicitly set 2026-08-27 (methodology fix): with no platforms:
// key, SwiftPM defaults to a conservative old minimum deployment target,
// so any model-written code using a macOS-13+-only API (e.g. String's
// split(separator:maxSplits:omittingEmptySubsequences:) overload) gets a
// hard compile error -- "only available in macOS 13.0 or newer" -- even
// though the actual build machine's toolchain trivially supports it
// (confirmed live: this Mac's installed Swift defaults its own target to
// arm64-apple-macosx26.0 when no platforms: override exists). Confirmed
// this was uniformly failing kiem_mini-parse-note across nearly every
// model tested (Ornith, Qwen3.6-Uncensored, Qwen3-Coder, Qwen3.5-9B, and
// others) for writing perfectly idiomatic modern Swift, not a real
// capability gap -- a shared fixture bug, not model-quality signal. .v13
// is comfortably below any realistic build machine's actual OS, so this
// makes the fixture toolchain-agnostic rather than pinning to one exact
// Swift version.
let package = Package(
    name: "NoteKit",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "NoteKit", targets: ["NoteKit"])
    ],
    targets: [
        .target(name: "NoteKit"),
        .testTarget(name: "NoteKitTests", dependencies: ["NoteKit"]),
    ]
)

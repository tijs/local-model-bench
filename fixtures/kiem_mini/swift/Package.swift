// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "NoteKit",
    products: [
        .library(name: "NoteKit", targets: ["NoteKit"])
    ],
    targets: [
        .target(name: "NoteKit"),
        .testTarget(name: "NoteKitTests", dependencies: ["NoteKit"]),
    ]
)

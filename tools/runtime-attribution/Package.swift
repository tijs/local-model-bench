// swift-tools-version: 6.1
import PackageDescription
let package = Package(
    name: "RuntimeAttribution",
    platforms: [.macOS(.v15)],
    products: [.executable(name: "runtime-attribution", targets: ["RuntimeAttribution"])],
    dependencies: [
        .package(url: "https://github.com/tijs/mei.git", revision: "ffb5dbbc78c763a56a6d8f335ee46edff8573b8e"),
        .package(url: "https://github.com/tijs/vmlx-swift.git", revision: "f6510fc384bcddb5db9efc96e1dd5ab3afc49346"),
    ],
    targets: [.executableTarget(name: "RuntimeAttribution", dependencies: [
        .product(name: "MeiCore", package: "mei"),
        .product(name: "MLX", package: "vmlx-swift"),
        .product(name: "MLXNN", package: "vmlx-swift"),
        .product(name: "MLXLMCommon", package: "vmlx-swift"),
        .product(name: "MLXLLM", package: "vmlx-swift"),
        .product(name: "MLXHuggingFace", package: "vmlx-swift"),
        .product(name: "VMLXTokenizers", package: "vmlx-swift"),
    ])]
)

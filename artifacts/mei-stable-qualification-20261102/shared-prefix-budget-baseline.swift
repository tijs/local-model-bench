import Foundation
import Metal
import MLX
@testable import MLXLMCommon
import XCTest

/// Real-Metal, model-free checks of the dependency consumed by Mei.
final class SharedPrefixCacheBudgetTests: XCTestCase {
    override func setUpWithError() throws {
        guard MTLCreateSystemDefaultDevice() != nil else {
            throw XCTSkip("A real Metal allocator is required")
        }
    }

    func testDistinctSSMPrefixesRespectCoordinatorRetainedBudget() {
        let cap = 128 * 1024
        let coordinator = CacheCoordinator(config: CacheCoordinatorConfig(
            usePagedCache: true, enableDiskCache: false,
            pagedBlockSize: 4, maxCacheBlocks: 32, maxCacheBytes: cap,
            ssmMaxEntries: 50, modelKey: "shared-retained-budget"))
        for token in 0..<20 {
            let state = MLXArray(Array(repeating: Float(token), count: 16_384))
            coordinator.ssmStateCache.store(ssmStates: [state], tokens: [token], boundary: 1)
        }
        var retainedLogicalBytes = 0
        for token in 0..<20 {
            if let states = coordinator.ssmStateCache.fetch(tokens: [token], boundary: 1) {
                retainedLogicalBytes += states.reduce(0) { $0 + $1.nbytes }
            }
        }
        XCTAssertLessThanOrEqual(retainedLogicalBytes, cap,
            "The coordinator cap must include separate SSM snapshots, not just paged KV")
        coordinator.releaseVolatile()
    }
}

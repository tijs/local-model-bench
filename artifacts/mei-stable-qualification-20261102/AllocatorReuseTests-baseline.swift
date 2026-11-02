import Foundation
import XCTest
import MLX
#if canImport(Metal)
import Metal
#endif

/// Exercise the real allocator with eager, host-populated arrays: no model or
/// timing assertion, and no shader intermediates that could mask the cache size.
final class AllocatorReuseTests: XCTestCase {
    @inline(never)
    private func allocateAndRelease(bytes: Int) {
        let payload = MLXArray(Array(repeating: Float(1), count: bytes / MemoryLayout<Float>.size))
        eval(payload)
        withExtendedLifetime(payload) {}
    }

    private func withCacheLimit(_ limit: Int, _ body: () -> Void) throws {
        #if canImport(Metal)
        guard MTLCreateSystemDefaultDevice() != nil else {
            throw XCTSkip("This regression requires a real Metal allocator")
        }
        #else
        throw XCTSkip("This regression requires a real Metal allocator")
        #endif
        let previous = Memory.cacheLimit
        try Device.withDefaultDevice(.gpu) {
            Stream.gpu.synchronize()
            Memory.clearCache()
            Memory.cacheLimit = limit
            defer {
                Stream.gpu.synchronize()
                Memory.clearCache()
                Memory.cacheLimit = previous
            }
            body()
        }
    }

    func testFullPrefillPoolAdaptsToDecodeShape() throws {
        let prefillBytes = 8 * 1024 * 1024
        let decodeBytes = 64 * 1024
        try withCacheLimit(prefillBytes) {
            allocateAndRelease(bytes: prefillBytes)
            XCTAssertEqual(Memory.cacheMemory, prefillBytes)
            for _ in 0..<4 {
                allocateAndRelease(bytes: decodeBytes)
                XCTAssertEqual(Memory.cacheMemory, decodeBytes,
                    "The current decode buffer should displace unused prefill buffers")
            }
        }
    }

    func testOversizedReturnPreservesUsefulBoundedPool() throws {
        let limit = 128 * 1024
        let hotBytes = 64 * 1024
        try withCacheLimit(limit) {
            allocateAndRelease(bytes: hotBytes)
            XCTAssertEqual(Memory.cacheMemory, hotBytes)
            allocateAndRelease(bytes: 8 * 1024 * 1024)
            XCTAssertLessThanOrEqual(Memory.cacheMemory, limit)
            XCTAssertEqual(Memory.cacheMemory, hotBytes,
                "A buffer larger than the allowance must not displace the useful pool")
        }
    }

    func testZeroAllowanceRetainsNoReturnedBuffer() throws {
        try withCacheLimit(0) {
            allocateAndRelease(bytes: 64 * 1024)
            XCTAssertEqual(Memory.cacheMemory, 0)
        }
    }
}

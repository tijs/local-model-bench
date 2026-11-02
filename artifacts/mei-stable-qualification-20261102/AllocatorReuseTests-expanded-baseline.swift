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

    @inline(never)
    private func cacheOlderThenNewer(olderBytes: Int, newerBytes: Int) {
        var older: MLXArray? = MLXArray(Array(repeating: Float(1), count: olderBytes / 4))
        var newer: MLXArray? = MLXArray(Array(repeating: Float(1), count: newerBytes / 4))
        eval(older!, newer!)
        withExtendedLifetime(older) {}
        older = nil
        withExtendedLifetime(newer) {
            XCTAssertEqual(Memory.cacheMemory, olderBytes)
        }
        newer = nil
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
        Device.withDefaultDevice(.gpu) {
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

    func testAdmissionEvictsOldestBuffersWithoutClearingUsefulEntries() throws {
        try withCacheLimit(512 * 1024) {
            cacheOlderThenNewer(olderBytes: 256 * 1024, newerBytes: 128 * 1024)
            XCTAssertEqual(Memory.cacheMemory, 384 * 1024)
            allocateAndRelease(bytes: 384 * 1024)
            XCTAssertEqual(Memory.cacheMemory, 512 * 1024,
                "Evict the older 256 KiB buffer while retaining the newer 128 KiB buffer")
        }
    }

    func testZeroAllowanceRetainsNoReturnedBuffer() throws {
        try withCacheLimit(0) {
            allocateAndRelease(bytes: 64 * 1024)
            XCTAssertEqual(Memory.cacheMemory, 0)
        }
    }
}

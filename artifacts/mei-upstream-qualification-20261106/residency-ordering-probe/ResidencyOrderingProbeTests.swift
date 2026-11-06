import Foundation
import MLX
@testable import MLXLMCommon
import XCTest

final class ResidencyOrderingProbeTests: XCTestCase {
    func testSyntheticOwnedReadOrdering() throws {
        let chunk = 256 * 1024
        let count = 256
        let wire = 2 * 1024 * 1024 * 1024
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("mei-residency-order-\(UUID()).bin")
        XCTAssertTrue(FileManager.default.createFile(atPath: url.path, contents: Data()))
        defer { try? FileManager.default.removeItem(at: url) }
        let writer = try FileHandle(forWritingTo: url)
        let seed = Data((0..<65_536).map { UInt8(truncatingIfNeeded: $0 &* 17 &+ 3) })
        for _ in 0..<(chunk * count / seed.count) { try writer.write(contentsOf: seed) }
        try writer.close()
        let file = try FileHandle(forReadingFrom: url)
        defer { try? file.close() }
        let priorCache = Memory.cacheLimit
        Memory.cacheLimit = 0
        defer {
            _ = setModelResidencyWiredLimit(0)
            Memory.clearCache()
            Memory.cacheLimit = priorCache
        }
        let modes = ["before", "after", "before", "after", "after", "before", "before", "after"]
        for (index, mode) in modes.enumerated() {
            XCTAssertTrue(setModelResidencyWiredLimit(0))
            Memory.clearCache()
            var arrays: [MLXArray] = []
            let started = ProcessInfo.processInfo.systemUptime
            if mode == "before" { XCTAssertTrue(setModelResidencyWiredLimit(wire)) }
            for i in 0..<count {
                arrays.append(try ResidentSafetensorsReader.loadRegion(file: file,
                    offset: UInt64(i * chunk), length: chunk, shape: [chunk], dtype: .uint8))
            }
            let readDone = ProcessInfo.processInfo.systemUptime
            if mode == "after" { XCTAssertTrue(setModelResidencyWiredLimit(wire)) }
            let finished = ProcessInfo.processInfo.systemUptime
            XCTAssertEqual(arrays.count, count)
            XCTAssertEqual(arrays.reduce(0) { $0 + $1.nbytes }, chunk * count)
            XCTAssertEqual(Array(arrays.first!.asArray(UInt8.self).prefix(4)), Array(seed.prefix(4)))
            XCTAssertEqual(Array(arrays.last!.asArray(UInt8.self).prefix(4)), Array(seed.prefix(4)))
            let snapshot = Memory.snapshot()
            let row: [String: Any] = ["mode": mode, "round": index,
                "warmup": index < 2, "bytes": chunk * count, "buffers": count,
                "read_ms": (readDone - started) * 1000,
                "total_api_ms": (finished - started) * 1000,
                "active_bytes": snapshot.activeMemory, "cache_bytes": snapshot.cacheMemory]
            let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
            print("RESIDENCY_ORDER_PROBE " + String(decoding: data, as: UTF8.self))
            XCTAssertTrue(setModelResidencyWiredLimit(0))
            arrays.removeAll()
            Memory.clearCache()
        }
    }
}

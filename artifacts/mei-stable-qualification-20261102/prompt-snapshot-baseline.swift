import Foundation
import Metal
import MLX
import MLXNN
@testable import MLXLMCommon
import XCTest

/// Weightless fixture: the same bounded cache + SDPA helper used by Qwen35
/// after its projections. No tokenizer, model bundle, server or learned weights.
private final class SnapshotProbeAttention: Module, LanguageModel {
    var kvHeads: [Int] { [2] }

    func newCache(parameters: GenerateParameters?) -> [KVCache] {
        [RotatingKVCache(maxSize: parameters?.maxKVSize ?? 65_536, keep: 4)]
    }

    func prepare(_ input: LMInput, cache: [KVCache], windowSize: Int?) throws -> PrepareResult {
        let count = input.text.tokens.size
        let remainder = min(count, windowSize ?? 128)
        let shape = [1, 2, count - remainder, 256]
        _ = cache[0].update(keys: MLXArray.zeros(shape, dtype: .bfloat16),
                            values: MLXArray.ones(shape, dtype: .bfloat16))
        eval(cache)
        return .tokens(.init(tokens: input.text.tokens.reshaped(-1)[(count - remainder)...]))
    }

    func callAsFunction(_ inputs: MLXArray, cache: [KVCache]?) -> MLXArray {
        let shape = [1, 2, inputs.size, 256]
        // Qwen35 builds the prefill mask before attention appends this chunk.
        let mask = cache?.first?.makeMask(n: inputs.size, windowSize: nil,
                                          returnArray: true) ?? .none
        let output = attentionWithCacheUpdate(
            queries: MLXArray.zeros(shape, dtype: .bfloat16),
            keys: MLXArray.full(shape, values: MLXArray(Float(2)), dtype: .bfloat16),
            values: MLXArray.full(shape, values: MLXArray(Float(3)), dtype: .bfloat16),
            cache: cache?.first, scale: 1 / 16, mask: mask)
        let value = sum(output).asType(.float32)
        return stacked([value, value + 1]).reshaped(1, 1, 2)
    }
}

/// One bounded diagnostic of the published source, not a model-performance test.
final class CacheSnapshotDiagnosticTests: XCTestCase {
    private func bytes(_ caches: [KVCache]?) -> Int {
        caches?.reduce(0) { total, cache in
            total + cache.innerState().reduce(0) { $0 + $1.nbytes }
        } ?? 0
    }

    private func record(_ stage: String, cache: any KVCache, iterator: TokenIterator?,
                        baseline: Int, includeAddresses: Bool = false) {
        let snapshot = iterator?.promptCacheSnapshot
        var row: [String: Any] = [
            "stage": stage,
            "active_bytes": Memory.activeMemory,
            "active_delta_bytes": Memory.activeMemory - baseline,
            "allocator_cache_bytes": Memory.cacheMemory,
            "peak_bytes": Memory.peakMemory,
            "live_cache_offset": cache.offset,
            "live_cache_type": String(describing: type(of: cache)),
            "live_cache_capacity_bytes": bytes([cache]),
            "live_cache_dtypes": cache.innerState().map { String(describing: $0.dtype) },
            "live_cache_shapes": cache.innerState().map(\.shape),
            "snapshot_capacity_bytes": bytes(snapshot),
            "snapshot_dtypes": snapshot?.flatMap { $0.innerState().map { String(describing: $0.dtype) } } ?? [],
            "snapshot_shapes": snapshot?.flatMap { $0.innerState().map(\.shape) } ?? [],
            "coordinator_present": iterator?.cacheCoordinator != nil,
        ]
        if includeAddresses {
            func addresses(_ arrays: [MLXArray]) -> [String] {
                arrays.map { array in
                    array.asData(access: .noCopy).data.withUnsafeBytes { buffer in
                        String(UInt(bitPattern: buffer.baseAddress!), radix: 16)
                    }
                }
            }
            row["live_backing_addresses"] = addresses(cache.innerState())
            row["snapshot_backing_addresses"] = addresses(snapshot?.flatMap { $0.innerState() } ?? [])
        }
        let data = try! JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
        print("CACHE_SNAPSHOT_DIAGNOSTIC " + String(decoding: data, as: UTF8.self))
    }

    func testPublishedCacheOffIteratorSnapshotAndDrainAccounting() throws {
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Real Metal required") }
        let previousPoolLimit = Memory.cacheLimit
        Memory.cacheLimit = 0
        defer {
            Stream.gpu.synchronize()
            Memory.clearCache()
            Memory.cacheLimit = previousPoolLimit
        }
        Stream.gpu.synchronize()
        Memory.clearCache()
        Memory.peakMemory = 0
        let baseline = Memory.activeMemory
        let count = 8192
        let cache = RotatingKVCache(maxSize: 65_536, keep: 4)
        let model = SnapshotProbeAttention()
        let input = LMInput(tokens: MLXArray(Array(repeating: Int32(1), count: count)).reshaped(1, count))
        var parameters = GenerateParameters(maxTokens: 2, maxKVSize: 65_536,
                                            temperature: 0, prefillStepSize: 128)
        parameters.enableCompiledDecode = false
        var iterator: TokenIterator? = try TokenIterator(input: input, model: model,
            cache: [cache], parameters: parameters, cacheCoordinator: nil)
        record("after_iterator_init", cache: cache, iterator: iterator, baseline: baseline)

        eval(iterator!.y.tokens)
        record("after_eval_token", cache: cache, iterator: iterator, baseline: baseline)
        eval(iterator!.cache)
        Stream.gpu.synchronize()
        Memory.clearCache()
        record("after_explicit_cache_eval_and_drain", cache: cache, iterator: iterator,
               baseline: baseline, includeAddresses: true)
        XCTAssertNil(iterator!.cacheCoordinator)
        let snapshotBytes = bytes(iterator!.promptCacheSnapshot)
        XCTAssertEqual(snapshotBytes, count * 2 * 256 * 2 * 2)
        XCTAssertTrue(cache.innerState().allSatisfy { $0.dtype == .bfloat16 })

        XCTAssertEqual(iterator!.next(), 1)
        record("after_async_next", cache: cache, iterator: iterator, baseline: baseline)
        eval(iterator!.y.tokens)
        record("after_next_eval_token", cache: cache, iterator: iterator, baseline: baseline)
        Stream.gpu.synchronize()
        record("after_next_token_stream_drain_only", cache: cache, iterator: iterator, baseline: baseline)
        eval(iterator!.cache)
        Stream.gpu.synchronize()
        Memory.clearCache()
        record("after_next_cache_eval_and_drain", cache: cache, iterator: iterator, baseline: baseline)

        let beforeDroppingSnapshot = Memory.activeMemory
        iterator!.promptCacheSnapshot = nil // Diagnostic only; no runtime source change.
        Stream.gpu.synchronize()
        Memory.clearCache()
        record("after_dropping_unused_prompt_snapshot", cache: cache, iterator: iterator, baseline: baseline)
        let released = beforeDroppingSnapshot - Memory.activeMemory
        print("CACHE_SNAPSHOT_DIAGNOSTIC_RELEASE snapshot_logical_bytes=\(snapshotBytes) released_active_bytes=\(released)")
        XCTAssertGreaterThanOrEqual(released, snapshotBytes)
        XCTAssertLessThan(Memory.peakMemory - baseline, 256 * 1024 * 1024)
        iterator = nil
        Stream.gpu.synchronize()
        Memory.clearCache()
        record("after_iterator_release_live_cache_retained", cache: cache, iterator: nil, baseline: baseline)
    }
}

// Diagnostic adapter for the pinned upstream SDPA vector benchmark.
// Reference: benchmarks/python/sdpa_vector_bench.py; see UPSTREAM-LICENSE.txt.
// Prepared only. Not part of Mei's shipped test target.
import Foundation
import MLX
import XCTest

final class QwenSDPAProbeTests: XCTestCase {
    func testVectorProbe() throws {
        let environment = ProcessInfo.processInfo.environment
        guard environment["MEI_RUN_SDPA_PROBE"] == "1" else {
            throw XCTSkip("Explicit, guarded operator diagnostic only")
        }
        let output = try XCTUnwrap(environment["MEI_SDPA_PROBE_OUTPUT"])
        let library = try XCTUnwrap(environment["MEI_SDPA_PROBE_METALLIB"])
        guard output.hasPrefix("/"), library.hasPrefix("/"),
              !FileManager.default.fileExists(atPath: output),
              FileManager.default.fileExists(atPath: library) else {
            XCTFail("Require fresh absolute output and an existing verified Metal library")
            return
        }
        let context = Int(environment["MEI_SDPA_PROBE_CONTEXT"] ?? "30000") ?? 0
        let capacity = Int(environment["MEI_SDPA_PROBE_CAPACITY"] ?? String(context)) ?? 0
        let dtypeName = environment["MEI_SDPA_PROBE_DTYPE"] ?? "bfloat16"
        let dtypes: [String: DType] = ["bfloat16": .bfloat16, "float16": .float16, "float32": .float32]
        guard (30000...30128).contains(context), (context...65536).contains(capacity),
              let dtype = dtypes[dtypeName] else {
            XCTFail("Require bounded Qwen decode fixture and an explicit supported dtype")
            return
        }
        GPU.metallib = URL(fileURLWithPath: library)
        Memory.memoryLimit = 4 << 30
        Memory.cacheLimit = 512 << 20
        MLXRandom.seed(0)

        let q = MLXRandom.normal([1, 16, 1, 256]).asType(dtype)
        let kStorage = MLXRandom.normal([1, 2, capacity, 256]).asType(dtype)
        let vStorage = MLXRandom.normal([1, 2, capacity, 256]).asType(dtype)
        let k = kStorage[.ellipsis, ..<context, 0...]
        let v = vStorage[.ellipsis, ..<context, 0...]
        eval(q, k, v)
        let scale: Float = 1 / Float(256).squareRoot()
        func attend(_ query: MLXArray) -> MLXArray {
            MLXFast.scaledDotProductAttention(
                queries: query, keys: k, values: v, scale: scale,
                mask: MLXFast.ScaledDotProductAttentionMaskMode.none)
        }
        // Same reference operations as the upstream Python benchmark.
        let expandedK = repeated(k, count: 8, axis: 1)
        let expandedV = repeated(v, count: 8, axis: 1)
        let scores = matmul(q, expandedK.transposed(0, 1, 3, 2)) * scale
        let probabilities = softmax(scores.asType(.float32), axis: -1).asType(dtype)
        let expected = matmul(probabilities, expandedV)
        let actual = attend(q)
        eval(actual, expected)
        let referenceF32 = expected.asType(.float32)
        let error = abs(actual.asType(.float32) - referenceF32)
        let maxAbsError = error.max().item(Float.self)
        let relativeError = maxAbsError / Swift.max(abs(referenceF32).max().item(Float.self), 1e-9)
        // Pinned test_fast_sdpa.py's dtype-specific absolute + relative tolerance.
        let tolerance: Float = dtype == .bfloat16 ? 5e-3 : (dtype == .float16 ? 3e-4 : 1e-5)
        let excess = (error - tolerance * abs(referenceF32)).max().item(Float.self)
        XCTAssertTrue(maxAbsError.isFinite && relativeError.isFinite && excess.isFinite)
        XCTAssertLessThanOrEqual(excess, tolerance)
        guard maxAbsError.isFinite, relativeError.isFinite, excess.isFinite,
              excess <= tolerance else { return }

        func runChain() {
            var result = q
            for _ in 0..<8 {
                result = attend(result)
            }
            eval(result)
        }
        for _ in 0..<10 { runChain() }
        var rounds = [[Double]]()
        for _ in 0..<5 {
            var samples = [Double]()
            for _ in 0..<30 {
                let start = DispatchTime.now().uptimeNanoseconds
                runChain()
                let elapsed = DispatchTime.now().uptimeNanoseconds - start
                samples.append(Double(elapsed) * 1e-9 / 8)
            }
            rounds.append(samples)
        }
        let values = rounds.flatMap { $0 }
        let report: [String: Any] = [
            "diagnostic_only": true,
            "scope": "Swift Debug host-inclusive chained operator probe; not model TPS, task scores or release qualification. Synthetic KV fixture with declared capacity; actual model dtype/layout/dispatch still needs tracing.",
            "shape_qh_kvh_context_dim": [16, 2, context, 256],
            "kv_storage_capacity": capacity,
            "query_length": 1,
            "dtype": dtypeName,
            "seed": 0,
            "architecture": GPU.deviceInfo().architecture,
            "metallib_override": GPU.metallib?.path ?? "",
            "force_tk1": environment["MLX_SDPA_PROBE_FORCE_TK1"] ?? "",
            "chain": 8, "warmup": 10, "iterations": 30, "rounds": 5,
            "samples_seconds_per_operator_by_round": rounds,
            "mean_seconds_per_operator": values.reduce(0, +) / Double(values.count),
            "max_abs_error": maxAbsError,
            "relative_linf_error": relativeError,
            "upstream_dtype_tolerance": tolerance,
            "numerical_check_passed": excess.isFinite && excess <= tolerance,
            "allocator_peak_bytes": Memory.peakMemory
        ]
        let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: URL(fileURLWithPath: output), options: .withoutOverwriting)
    }
}

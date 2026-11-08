import CryptoKit
import Foundation
import Metal
import MLX
@preconcurrency import VMLXTokenizers
import XCTest

@testable import MLXHuggingFace
@testable import MLXLLM
@testable import MLXLMCommon

/// Copy into an isolated vMLX MLXLMTests target for either pinned revision.
/// This diagnostic captures one teacher-forced model step, outside any timer.
final class QwenDecodeCaptureTests: XCTestCase {
    private enum Failure: Error { case invalid(String) }

    private func sha(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private func tokenHash(_ ids: [Int]) -> String {
        var bytes = Data()
        for id in ids {
            var word = Int32(id).littleEndian
            withUnsafeBytes(of: &word) { bytes.append(contentsOf: $0) }
        }
        return sha(bytes)
    }

    private func capture(
        model: any LanguageModel, ids: [Int], trace: URL, receipt: URL
    ) throws {
        try MLXMetalTestLock.withLock {
            try MLX.Stream.withNewDefaultStream(device: .gpu) {
                let manager = MTLCaptureManager.shared()
                guard !manager.isCapturing, manager.supportsDestination(.gpuTraceDocument),
                    let device = MTLCreateSystemDefaultDevice()
                else { throw Failure.invalid("Metal trace documents unavailable") }
                let stream = MLX.Stream()
                let cache = model.newCache(parameters: nil)
                let input = LMInput.Text(
                    tokens: MLXArray(ids.map(Int32.init), [1, ids.count]), tokenIds: ids)
                let (prefill, teacherToken) = try withError { error in
                    let prefill: LMOutput
                    switch try model.prepare(LMInput(text: input), cache: cache, windowSize: 256) {
                    case .tokens(let remainder):
                        // Match TokenIterator.forwardUncompiled's batch-axis normalization.
                        let step = remainder.tokens.ndim == 1 ? remainder[text: .newAxis] : remainder
                        prefill = model(step, cache: cache, state: nil)
                    case .logits(let output):
                        prefill = output
                    }
                    try error.check()
                    let next = argMax(prefill.logits[0..., -1, 0...], axis: -1)
                    eval([next] + cache.flatMap { $0.state })
                    stream.synchronize()
                    try error.check()
                    let teacherToken = next.item(Int32.self)
                    try error.check()
                    return (prefill, teacherToken)
                }
                let cacheState = cache.map { layer in
                    [
                        "type": String(reflecting: type(of: layer)),
                        "offset": layer.offset,
                        "state": layer.state.map {
                            ["shape": $0.shape, "dtype": String(describing: $0.dtype)] as [String: Any]
                        },
                    ] as [String: Any]
                }

                let descriptor = MTLCaptureDescriptor()
                descriptor.captureObject = device
                descriptor.destination = .gpuTraceDocument
                descriptor.outputURL = trace
                let decodeInput = LMInput.Text(tokens: MLXArray([teacherToken], [1, 1]))
                eval(decodeInput.tokens)
                stream.synchronize()
                let decodedToken = try withError { error in
                    try manager.startCapture(with: descriptor)
                    defer { manager.stopCapture() }
                    let decoded = model(decodeInput, cache: cache, state: prefill.state)
                    try error.check()
                    let next = argMax(decoded.logits[0..., -1, 0...], axis: -1)
                    // Follow the ordinary decode dependency chain. Forcing every
                    // cache array here could add diagnostic-only GPU work.
                    eval(next)
                    stream.synchronize()
                    try error.check()
                    return next
                }
                let decodedTokenID = try withError { error in
                    let token = decodedToken.item(Int32.self)
                    try error.check()
                    return token
                }
                let evidence: [String: Any] = [
                    "prompt_tokens": ids.count,
                    "token_ids_sha256": tokenHash(ids),
                    "teacher_token_id": teacherToken,
                    "decoded_token_id": decodedTokenID,
                    "prefill_cache": cacheState,
                    "trace": trace.path,
                ]
                try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
                    .write(to: receipt, options: .withoutOverwriting)
            }
        }
    }

    func testOptInQwenDecodeCapture() async throws {
        let env = ProcessInfo.processInfo.environment
        guard env["VMLX_QWEN_DECODE_CAPTURE"] == "1" else {
            throw XCTSkip("Explicit Qwen dispatch capture required")
        }
        func required(_ key: String) throws -> String {
            guard let value = env[key], !value.isEmpty else { throw Failure.invalid(key) }
            return value
        }
        let context = try required("VMLX_QWEN_TRACE_CONTEXT")
        let count: Int
        let expectedSHA: String
        switch context {
        case "short":
            count = 26
            expectedSHA = "b827d167aee54089e52b41236c7987380da3bd1ccfa2d7397f852871a70ccbe3"
        case "loaded":
            count = 30009
            expectedSHA = "55e88c2ec8c2b82c2cc6595d1beb5543b34255b1acf9d9911cc418f018c7c099"
        default:
            throw Failure.invalid("Unexpected capture context")
        }
        let prompts = URL(fileURLWithPath: try required("VMLX_QWEN_TRACE_PROMPTS"))
        let trace = URL(fileURLWithPath: try required("VMLX_QWEN_TRACE_OUTPUT"))
        let receipt = trace.appendingPathExtension("json")
        guard trace.pathExtension == "gputrace",
            !FileManager.default.fileExists(atPath: trace.path),
            !FileManager.default.fileExists(atPath: receipt.path)
        else { throw Failure.invalid("A fresh .gputrace path is required") }
        let prompt = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: prompts))
        guard let text = prompt[context], sha(Data(text.utf8)) == expectedSHA
        else { throw Failure.invalid("Prompt differs from the audited timing request") }
        let directory = URL(fileURLWithPath: try required("VMLX_QWEN_TRACE_MODEL"))
        let loaded = try await MLXLMCommon.loadModel(
            from: directory, using: #huggingFaceTokenizerLoader())
        guard let model = loaded.model as? Qwen35MoEModel
        else { throw Failure.invalid("Unexpected loaded Qwen architecture") }
        let ids = try loaded.tokenizer.applyChatTemplate(
            messages: [["role": "user", "content": text]], tools: nil, additionalContext: nil)
        guard ids.count == count, ids.allSatisfy({ (0...Int(Int32.max)).contains($0) })
        else { throw Failure.invalid("Rendered token IDs differ from the declared shape") }
        try capture(model: model, ids: ids, trace: trace, receipt: receipt)
    }
}

import Foundation
import CryptoKit
import MLX
import MLXNN
import MLXLMCommon
import MLXLLM
import MLXHuggingFace
import VMLXTokenizers
@testable import MeiCore

// Diagnostic only: build all dependencies with -Xswiftc -enable-testing.
// This permits the same default-off Flint registration used by production Mei.
private final class PreparationTrace {
    var active = true
    var segments: [[Int]] = []
    func reset() { active = true; segments = [] }
}
private final class TracedModel: Module, LanguageModel {
    let base: any LanguageModel
    let trace: PreparationTrace
    init(_ base: any LanguageModel, _ trace: PreparationTrace) { self.base = base; self.trace = trace }
    var preservesCheckpointParameterDTypes: Bool { base.preservesCheckpointParameterDTypes }
    var supportsWholeForwardCompilation: Bool { base.supportsWholeForwardCompilation }
    var maximumSupportedDecodeBatchSize: Int? { base.maximumSupportedDecodeBatchSize }
    func prepare(_ input: LMInput, cache: [KVCache], windowSize: Int?) throws -> PrepareResult {
        if trace.active { trace.segments.append(input.text.tokenIds ?? input.text.tokens.reshaped(-1).asArray(Int.self)) }
        return try base.prepare(input, cache: cache, windowSize: windowSize)
    }
    func callAsFunction(_ input: LMInput.Text, cache: [KVCache]?, state: LMOutput.State?) -> LMOutput {
        base(input, cache: cache, state: state)
    }
    func callAsFunction(_ input: MLXArray, cache: [KVCache]?) -> MLXArray { base(input, cache: cache) }
    func replayForward(_ input: MLXArray, cache: [KVCache]?) throws -> MLXArray { try base.replayForward(input, cache: cache) }
    func newCache(parameters: GenerateParameters?) -> [KVCache] { base.newCache(parameters: parameters) }
}
private final class ForcedRows {
    let tokens: [Int]
    let tail: Int
    let trace: PreparationTrace
    var index = 0
    var rows: [[Float]] = []
    init(_ tokens: [Int], tail: Int, trace: PreparationTrace) { self.tokens = tokens; self.tail = tail; self.trace = trace }
}
private struct ForceAndRecord: LogitProcessor {
    let record: ForcedRows
    mutating func prompt(_ prompt: MLXArray) {}
    func process(logits: MLXArray) -> MLXArray {
        record.trace.active = false
        if record.index >= record.tokens.count - record.tail && record.index < record.tokens.count {
            record.rows.append(logits.reshaped(-1).asArray(Float.self))
        }
        let next = record.tokens[min(record.index, record.tokens.count - 1)]
        record.index += 1
        var mask = [Float](repeating: -.infinity, count: logits.size)
        mask[next] = 0
        return MLXArray(mask).reshaped(logits.shape)
    }
    mutating func didSample(token: MLXArray) {}
}
private final class RestoreCount: @unchecked Sendable {
    let lock = NSLock()
    var value = 0
    func observe(_ p: PrefillProgress) {
        lock.lock(); defer { lock.unlock() }
        if p.stage == .cacheRestore { value = p.completedUnitCount }
    }
}
private func writeJSON(_ object: Any, _ url: URL) throws {
    try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]).write(to: url)
}
private func digest(_ values: [Float]) -> String {
    values.withUnsafeBytes { SHA256.hash(data: Data($0)).map { String(format: "%02x", $0) }.joined() }
}

@main struct RuntimeAttribution {
    @MainActor static func main() async throws {
        let argv = Array(CommandLine.arguments.dropFirst())
        func value(_ name: String) -> String {
            guard let i = argv.firstIndex(of: name), i + 1 < argv.count else { fatalError("Required: \(name)") }
            return argv[i + 1]
        }
        let modelDir = URL(fileURLWithPath: value("--model"))
        let inputURL = URL(fileURLWithPath: value("--input"))
        let output = URL(fileURLWithPath: value("--out"))
        let prefill = Int(value("--prefill"))!
        let tail = Int(value("--tail"))!
        precondition(prefill > 0 && (1...128).contains(tail))
        precondition(!FileManager.default.fileExists(atPath: output.path), "Use a new output directory")
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let cases = try JSONSerialization.jsonObject(with: Data(contentsOf: inputURL)) as! [[String: Any]]
        precondition(!cases.isEmpty)
        let loader = #huggingFaceTokenizerLoader()
        let tokenizer = try await loader.load(from: modelDir)
        var inputs: [[String: Any]] = []
        for item in cases {
            let request = try ChatRequest(json: JSONSerialization.data(withJSONObject: item["request"]!))
            let ids = try tokenizer.applyChatTemplate(
                messages: request.messages.map { MessageMapping.templateDictionary(from: $0) },
                tools: MessageMapping.templateTools(request.tools),
                additionalContext: MessageMapping.additionalContext(enableThinking: nil,
                    reasoningEffort: request.reasoningEffort, toolChoice: request.toolChoice))
            guard let controllable = tokenizer as? any GenerationPromptControllableTokenizer else { fatalError("Native tokenizer cannot render complete turns") }
            var completedBody = item["request"] as! [String: Any]
            var completedMessages = completedBody["messages"] as! [[String: Any]]
            completedMessages.append(item["assistant"] as! [String: Any])
            completedBody["messages"] = completedMessages
            let completed = try ChatRequest(json: JSONSerialization.data(withJSONObject: completedBody))
            let full = try controllable.applyChatTemplate(
                messages: completed.messages.map { MessageMapping.templateDictionary(from: $0) },
                tools: MessageMapping.templateTools(completed.tools),
                additionalContext: MessageMapping.additionalContext(enableThinking: nil,
                    reasoningEffort: request.reasoningEffort, toolChoice: request.toolChoice), addGenerationPrompt: false)
            precondition(full.count > ids.count && Array(full.prefix(ids.count)) == ids,
                         "Canonical completed turn must extend the exact native request")
            let forced = Array(full.dropFirst(ids.count))
            precondition(!forced.isEmpty && ids.count < 65536)
            inputs.append(["name": item["name"]!, "tokens": ids, "forced_tokens": forced,
                           "native_prompt": tokenizer.decode(tokenIds: ids), "request": item["request"]!,
                           "source_sha256": item["source_sha256"]!, "canonicalized_continuation": true])
        }
        try writeJSON(inputs, output.appendingPathComponent("native-inputs.json"))
        if argv.contains("--render-only") { return }
        precondition(ProcessInfo.processInfo.environment["VMLX_ENABLE_UNSAFE_COMPILE"] == "0")
        Memory.cacheLimit = 134217728
        Memory.memoryLimit = 24051816857
        let configuration = try await FlintSupport.prepare(directory: modelDir, enabled: true, janghEnabled: true)
        let context = try await LLMModelFactory.shared.load(from: modelDir, using: loader, configuration: configuration)
        Memory.cacheLimit = 134217728
        let trace = PreparationTrace()
        let model = TracedModel(context.model, trace)
        var parameters = GenerateParameters(maxTokens: 1, maxKVSize: 65536, temperature: 0,
            topP: 1, topK: 0, randomSeed: 173, prefillStepSize: prefill)
        parameters.enableCompiledDecode = false
        for item in inputs {
            let name = item["name"] as! String
            let request = try ChatRequest(json: JSONSerialization.data(withJSONObject: item["request"]!))
            let ids = item["tokens"] as! [Int]
            let forced = item["forced_tokens"] as! [Int]
            parameters.maxTokens = forced.count
            let folder = output.appendingPathComponent(name)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let coordinator = CacheCoordinator(config: CacheCoordinatorConfig(
                usePagedCache: true, enableDiskCache: true, pagedBlockSize: 16,
                maxCacheBlocks: 8192, maxCacheBytes: 536870912,
                diskCacheDir: folder.appendingPathComponent("kv"), enableSSMReDerive: true,
                modelKey: modelDir.path))
            if let gp = tokenizer as? any GenerationPromptControllableTokenizer {
                let dummy: [[String: any Sendable]] = [["role": "user", "content": "x"]]
                let a = try gp.applyChatTemplate(messages: dummy, tools: nil, additionalContext: nil, addGenerationPrompt: true)
                let b = try gp.applyChatTemplate(messages: dummy, tools: nil, additionalContext: nil, addGenerationPrompt: false)
                var n = 0
                while n < min(a.count, b.count), a[n] == b[n] { n += 1 }
                coordinator.setGenPromptSuffixTokens(Array(a[n...]))
            }
            var matrices: [String: [[Float]]] = [:]
            var restored: [String: Int] = [:]
            var schedules: [String: [Int]] = [:]
            var coldSegments: [[Int]] = []
            func run(_ label: String, _ coord: CacheCoordinator?, split: Bool = false, unwrapped: Bool = false) throws {
                let activeModel: any LanguageModel = unwrapped ? context.model : model
                trace.reset()
                let record = ForcedRows(forced, tail: min(tail, forced.count), trace: trace)
                let cache = activeModel.newCache(parameters: parameters)
                var tokenIDs = ids
                if split {
                    precondition(coldSegments.flatMap { $0 } == ids, "Recorded prefill segments must partition the exact prompt")
                    for segment in coldSegments.dropLast() {
                        let input = LMInput(tokens: MLXArray(segment.map(Int32.init)).reshaped(1, -1), tokenIds: segment)
                        switch try activeModel.prepare(input, cache: cache, windowSize: prefill) {
                        case .tokens(let rest): eval(activeModel(rest.tokens.reshaped(1, -1), cache: cache))
                        case .logits: break
                        }
                        eval(cache)
                    }
                    tokenIDs = coldSegments.last!
                }
                let progress = RestoreCount()
                var iterator = try TokenIterator(
                    input: LMInput(tokens: MLXArray(tokenIDs.map(Int32.init)).reshaped(1, -1), tokenIds: tokenIDs, toolSchemas: MessageMapping.templateTools(request.tools)),
                    model: activeModel, cache: cache, parameters: parameters, cacheCoordinator: coord,
                    prefillProgressHandler: { progress.observe($0) }, additionalProcessor: ForceAndRecord(record: record))
                var generated: [Int] = []
                while let token = iterator.next() { generated.append(token) }
                precondition(generated == forced, "Teacher forcing must consume the same history")
                precondition(record.rows.allSatisfy { $0.allSatisfy(\.isFinite) })
                precondition(record.rows.count == min(tail, forced.count))
                schedules[label] = trace.segments.map(\.count)
                if label == "cold_coordinator" { coldSegments = trace.segments }
                if split { precondition(trace.segments == coldSegments, "Matching control must replay every actual segment") }
                matrices[label] = record.rows
                restored[label] = progress.value
                if coord != nil { iterator.storeCacheAfterGeneration(generatedTokenIds: generated, includeGeneratedBoundary: false) }
                var raw = Data()
                for row in record.rows { row.withUnsafeBytes { raw.append(contentsOf: $0) } }
                try raw.write(to: folder.appendingPathComponent(label + ".f32"))
                print("attribution \(name) \(label) prompt=\(ids.count) forced=\(forced.count) restored=\(progress.value)")
                fflush(stdout)
            }
            try run("cache_off", nil)
            try run("cache_off_unwrapped", nil, unwrapped: true)
            precondition(matrices["cache_off"]! == matrices["cache_off_unwrapped"]!, "Tracing must preserve unwrapped logits before attribution")
            try run("cold_coordinator", coordinator)
            try run("warm_restore", coordinator)
            try run("cache_off_matching_split", nil, split: true)
            var comparisons: [String: Any] = [:]
            for (a, b) in [("cache_off", "cache_off_unwrapped"), ("cache_off", "cold_coordinator"), ("cold_coordinator", "warm_restore"), ("cold_coordinator", "cache_off_matching_split")] {
                comparisons[a + "__" + b] = zip(matrices[a]!, matrices[b]!).enumerated().map { i, pair in
                    let (x, y) = pair
                    let tx = x.indices.max { x[$0] < x[$1] }!
                    let ty = y.indices.max { y[$0] < y[$1] }!
                    return ["step": forced.count - matrices[a]!.count + i, "exact": x == y,
                            "max_abs": Double(zip(x, y).map { abs($0 - $1) }.max()!),
                            "argmax_a": tx, "argmax_b": ty] as [String: Any]
                }
            }
            try writeJSON(["name": name, "prompt_tokens": ids.count, "forced_count": forced.count,
                           "tail_rows": matrices["cache_off"]!.count, "vocab": matrices["cache_off"]!.first!.count,
                           "restored": restored, "prefill_segments": schedules, "row_sha256": matrices.mapValues { $0.map(digest) },
                           "comparisons": comparisons, "mlx_peak_bytes": Memory.snapshot().peakMemory],
                          folder.appendingPathComponent("report.json"))
            precondition(restored["warm_restore"]! > 0, "Warm control must exercise reuse")
        }
    }
}

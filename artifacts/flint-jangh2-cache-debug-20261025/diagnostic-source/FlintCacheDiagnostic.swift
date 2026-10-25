// Temporary, opt-in state tracing for the repeated-prefix regression.
import Foundation
import CryptoKit
import MLX
import MLXLMCommon

enum FlintCacheDiagnostic {
    static func capture(_ phase: String, _ tokens: MLXArray, _ cache: [KVCache]?) {
        guard let path = ProcessInfo.processInfo.environment["MEI_FLINT_CACHE_TRACE"],
              let cache, let offset = cache.first?.offset,
              (650...655).contains(offset), tokens.size < 4 else { return }
        let layers: [[String: Any]] = cache.enumerated().map { index, layer in
            let arrays: [[String: Any]] = layer.state.map { value in
                let floats = value.asType(.float32).asArray(Float.self)
                let digest = floats.withUnsafeBytes { SHA256.hash(data: Data($0)).map { String(format: "%02x", $0) }.joined() }
                return ["shape": value.shape, "dtype": String(describing: value.dtype), "sha256_f32": digest]
            }
            return ["layer": index, "offset": layer.offset, "metadata": layer.metaState, "state": arrays]
        }
        let row: [String: Any] = ["phase": phase, "tokens": tokens.asType(.int32).asArray(Int32.self), "layers": layers]
        guard var data = try? JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]) else { return }
        data.append(10)
        if !FileManager.default.fileExists(atPath: path) { FileManager.default.createFile(atPath: path, contents: nil) }
        if let handle = try? FileHandle(forWritingTo: URL(fileURLWithPath: path)) {
            defer { try? handle.close() }
            try? handle.seekToEnd(); try? handle.write(contentsOf: data)
        }
    }
}

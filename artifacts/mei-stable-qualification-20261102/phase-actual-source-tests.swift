import Foundation
public struct NativeMTPPhaseSnapshot: Sendable, Equatable {
    public let calls: [String: Int]
    public let seconds: [String: Double]

    public init(calls: [String: Int], seconds: [String: Double]) {
        self.calls = calls
        self.seconds = seconds
    }
}

public enum NativeMTPPhaseDiagnostics {
    private final class Storage: @unchecked Sendable {
        let lock = NSLock()
        var calls: [String: Int] = [:]
        var seconds: [String: Double] = [:]
    }

    private static let storage = Storage()

    public static var enabled: Bool {
        // Qwen checks this twice per decoder layer even during ordinary AR
        // generation. Read only these variables instead of rebuilding the
        // entire process environment on every check. Preserve the original
        // OR contract: a legacy "1" still enables diagnostics when the
        // current spelling is present with another value. Values stay live.
        RuntimeEnvironment.value("VMLX_NATIVE_MTP_PHASE_DIAG") == "1"
            || RuntimeEnvironment.value("VMLINUX_NATIVE_MTP_PHASE_DIAG") == "1"
    }

    public static func reset() {
        storage.lock.lock()
        defer { storage.lock.unlock() }
        storage.calls.removeAll(keepingCapacity: true)
        storage.seconds.removeAll(keepingCapacity: true)
    }

    public static func record(_ phase: String, seconds elapsed: Double) {
        guard enabled else { return }
        storage.lock.lock()
        storage.calls[phase, default: 0] += 1
        storage.seconds[phase, default: 0] += elapsed
        storage.lock.unlock()
    }

    public static func snapshot(reset: Bool = false) -> NativeMTPPhaseSnapshot {
        storage.lock.lock()
        let result = NativeMTPPhaseSnapshot(calls: storage.calls, seconds: storage.seconds)
        if reset {
            storage.calls.removeAll(keepingCapacity: true)
            storage.seconds.removeAll(keepingCapacity: true)
        }
        storage.lock.unlock()
        return result
    }

    public static func summary(limit: Int = 8) -> String {
        let snap = snapshot()
        let rows = snap.seconds
            .sorted { lhs, rhs in lhs.value == rhs.value ? lhs.key < rhs.key : lhs.value > rhs.value }
            .prefix(limit)
            .map { key, seconds in
                let calls = snap.calls[key, default: 0]
                return String(format: "%@:%d/%.3f", key, calls, seconds)
            }
        return rows.isEmpty ? "none" : rows.joined(separator: ",")
    }
}


@main struct TestFlags {
 static func main() {
 let current="VMLX_NATIVE_MTP_PHASE_DIAG",legacy="VMLINUX_NATIVE_MTP_PHASE_DIAG"
 func assign(_ key:String,_ value:String?) {if let value {setenv(key,value,1)} else {unsetenv(key)}}
 let values:[String?]=[nil,"","0","1","true","yes","01"]
 var cases=0
 for primary in values {for fallback in values {
 assign(current,primary);assign(legacy,fallback)
 precondition(NativeMTPPhaseDiagnostics.enabled == (primary == "1" || fallback == "1"));cases += 1
 }}
 NativeMTPPhaseDiagnostics.reset();assign(current,"1");assign(legacy,nil)
 NativeMTPPhaseDiagnostics.record("fixture",seconds:0.25)
 assign(current,"0");NativeMTPPhaseDiagnostics.record("fixture",seconds:9)
 let snapshot=NativeMTPPhaseDiagnostics.snapshot()
 precondition(snapshot.calls == ["fixture":1]);precondition(snapshot.seconds == ["fixture":0.25])
 print("PASS: \(cases) live environment combinations, enabled recording, disabled no-op")
 }
}

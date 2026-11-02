import Foundation
@inline(never) func original() -> Bool {
    let env = ProcessInfo.processInfo.environment
    return env["VMLX_NATIVE_MTP_PHASE_DIAG"] == "1" || env["VMLINUX_NATIVE_MTP_PHASE_DIAG"] == "1"
}
@inline(never) func candidate() -> Bool {
    RuntimeEnvironment.value("VMLX_NATIVE_MTP_PHASE_DIAG") == "1" || RuntimeEnvironment.value("VMLINUX_NATIVE_MTP_PHASE_DIAG") == "1"
}
@main struct Benchmark {
    static func main() {
        unsetenv("VMLX_NATIVE_MTP_PHASE_DIAG")
        unsetenv("VMLINUX_NATIVE_MTP_PHASE_DIAG")
        for (label, body) in [("original", original), ("candidate", candidate), ("candidate", candidate), ("original", original)] {
            let start = ContinuousClock.now
            var count = 0
            for _ in 0..<100000 { if body() { count += 1 } }
            print(label, start.duration(to: .now), count)
        }
    }
}

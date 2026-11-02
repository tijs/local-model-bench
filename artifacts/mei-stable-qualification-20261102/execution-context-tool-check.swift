// Model-free fixture for checking read-only Swift task and thread inspection.
import Foundation

let worker = Task.detached(priority: .userInitiated) {
    try? await Task.sleep(for: .seconds(20))
}
RunLoop.main.run(until: Date(timeIntervalSinceNow: 20))
worker.cancel()

import Foundation
import Darwin

    private func currentHostMemoryPressureLevel() -> Int? {
        var level: Int32 = 0
        var size = MemoryLayout<Int32>.size
        guard sysctlbyname("kern.memorystatus_vm_pressure_level", &level, &size, nil, 0) == 0,
            size == MemoryLayout<Int32>.size,
            level == 1 || level == 2 || level == 4
        else { return nil }
        return Int(level)
    }


print(currentHostMemoryPressureLevel().map(String.init) ?? "unavailable")

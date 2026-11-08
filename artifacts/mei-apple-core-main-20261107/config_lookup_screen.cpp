// Measure host lookup cost in isolation. No Metal device or model is loaded.
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <utility>

#include "mlx/config.h"

namespace config = mlx::core::config;

int main() {
  constexpr int iterations = 500'000;
  constexpr std::array labels{
      "cached_commit_limits", "dynamic_commit_limits",
      "cached_retain_flag", "dynamic_retain_flag",
  };
  // Identical values for the cached and dynamic arms. Warm the default map
  // before collecting the steady-state observations.
  constexpr char ops_key[] = "MLX_MAX_OPS_PER_BUFFER";
  constexpr char mb_key[] = "MLX_MAX_MB_PER_BUFFER";
  constexpr char retain_key[] = "MLX_METAL_RETAIN_BOUND_BUFFERS";
  config::update(ops_key, 100);
  config::update(mb_key, 32);
  config::update(retain_key, 1);
  const volatile int cached_ops = 100, cached_mb = 32, cached_retain = 1;
  auto measure = [&](auto read) {
    auto start = std::chrono::steady_clock::now();
    std::int64_t checksum = 0;
    for (int i = 0; i < iterations; ++i) {
      checksum += read();
    }
    auto elapsed = std::chrono::steady_clock::now() - start;
    return std::pair{
        std::chrono::duration<double, std::nano>(elapsed).count() / iterations,
        checksum,
    };
  };
  for (int repeat = 0; repeat < 8; ++repeat) {
    for (int pos = 0; pos < 4; ++pos) {
      // Each arm is in each position twice.
      int arm = (repeat + pos) % 4;
      const auto [ns, checksum] = [&] {
        switch (arm) {
          case 0:
            return measure([&] { return cached_ops + cached_mb; });
          case 1:
            return measure([&] {
              return config::get(ops_key, 100) + config::get(mb_key, 32);
            });
          case 2:
            return measure([&] { return cached_retain; });
          default:
            return measure([&] { return config::get(retain_key, 1); });
        }
      }();
      if (checksum != std::int64_t{iterations} * (arm < 2 ? 132 : 1)) {
        std::cerr << "cached and dynamic values differ\n";
        return 1;
      }
      std::cout << "{\"arm\":\"" << labels[arm] << "\",\"repeat\":" << repeat
                << ",\"iterations\":" << iterations
                << ",\"ns_per_iteration\":" << ns << "}\n";
    }
  }
}

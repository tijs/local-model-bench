// Synthetic Gemma local-attention prefill screen; it does not load weights.
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>

#include "mlx/backend/metal/metal.h"
#include "mlx/fast.h"
#include "mlx/mlx.h"

namespace mx = mlx::core;

int main(int argc, char* argv[]) {
  if (argc != 2) {
    std::cerr << "Usage: gemma_window_screen /path/to/mlx.metallib\n";
    return 2;
  }
  mx::metal::set_metallib_path(argv[1]);
  if (!mx::is_available(mx::Device::gpu)) {
    throw std::runtime_error("Metal GPU required");
  }
  mx::set_default_device(mx::Device::gpu);
  mx::random::seed(20261107);
  std::cout << std::unitbuf;
  constexpr int q_len = 256, dim = 256, window = 1024;
  constexpr float scale = 1.0f; // Gemma4Text attention scale.
  constexpr std::array names{"current_policy", "native_window", "fused_window"};
  for (int k_len : {q_len, window + q_len - 1}) {
    auto q = mx::astype(mx::random::normal({1, 16, q_len, dim}), mx::bfloat16);
    auto k = mx::astype(mx::random::normal({1, 8, k_len, dim}), mx::bfloat16);
    auto v = mx::astype(mx::random::normal({1, 8, k_len, dim}), mx::bfloat16);
    auto qi = mx::reshape(mx::arange(k_len - q_len, k_len), {q_len, 1});
    auto ki = mx::arange(k_len);
    auto mask = mx::logical_and(mx::less_equal(ki, qi), mx::greater(ki, qi - window));
    mx::eval(q, k, v, mask);

    auto run = [&](int arm) {
      if (arm == 0) {
        if (k_len == q_len) {
          return mx::fast::scaled_dot_product_attention(q, k, v, scale, -1, "causal");
        }
        return mx::fast::scaled_dot_product_attention(q, k, v, scale, -1, "array", mask);
      }
      return mx::fast::scaled_dot_product_attention(
          q, k, v, scale, window, "causal", {}, {}, arm == 2);
    };
    auto reference = mx::astype(run(0), mx::float32);
    for (int arm = 1; arm < 3; ++arm) {
      auto diff = mx::astype(run(arm), mx::float32) - reference;
      float relative_rms = mx::sqrt(
          mx::sum(mx::square(diff)) / mx::sum(mx::square(reference))).item<float>();
      std::cout << "{\"event\":\"parity\",\"keys\":" << k_len << ",\"arm\":\""
                << names[arm] << "\",\"relative_rms\":" << relative_rms << "}\n";
      if (!std::isfinite(relative_rms) || relative_rms > 0.007f) {
        throw std::runtime_error("window result differs from Gemma's current mask policy");
      }
    }

    // Keep every mode equally represented in each position of the order.
    for (int repeat = 0; repeat < 18; ++repeat) {
      for (int index = 0; index < 3; ++index) {
        int arm = (repeat + (repeat < 9 ? index : 2 - index)) % 3;
        auto begin = std::chrono::steady_clock::now();
        mx::eval(run(arm));
        double ms = std::chrono::duration<double, std::milli>(
                        std::chrono::steady_clock::now() - begin).count();
        std::cout << "{\"event\":\"sample\",\"queries\":" << q_len
                  << ",\"keys\":" << k_len << ",\"arm\":\"" << names[arm]
                  << "\",\"repeat\":" << repeat << ",\"elapsed_ms\":" << ms << "}\n";
      }
    }
  }
  mx::clear_streams();
}

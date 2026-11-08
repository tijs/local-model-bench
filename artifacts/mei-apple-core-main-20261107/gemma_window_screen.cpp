// Synthetic Gemma local-attention prefill screen; it does not load weights.
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "mlx/backend/metal/metal.h"
#include "mlx/fast.h"
#include "mlx/mlx.h"

namespace mx = mlx::core;

int main(int argc, char* argv[]) {
  const auto mode = argc == 3 ? std::string_view(argv[2]) : std::string_view{};
  const bool diagnostics = mode == "--diagnostics";
  const bool native_only = mode == "--native-only";
  if (argc != 2 && !diagnostics && !native_only) {
    std::cerr << "Usage: gemma_window_screen /path/to/mlx.metallib "
                 "[--diagnostics | --native-only]\n";
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
  const int arm_count = native_only ? 2 : 3;
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
    auto relative_rms_to = [](const mx::array& value, const mx::array& base) {
      auto diff = mx::astype(value, mx::float32) - base;
      return mx::sqrt(mx::sum(mx::square(diff)) / mx::sum(mx::square(base)))
          .item<float>();
    };
    if (diagnostics) {
      // Use the exact same boolean mask with and without fusion. The FP32
      // reference starts from the BF16 inputs, so only arithmetic differs.
      auto fp32 = mx::fast::scaled_dot_product_attention(
          mx::astype(q, mx::float32), mx::astype(k, mx::float32),
          mx::astype(v, mx::float32), scale, -1, "array", mask);
      auto fused_mask = mx::astype(mx::fast::scaled_dot_product_attention(
          q, k, v, scale, -1, "array", mask, {}, true), mx::float32);
      auto native = run(1);
      auto fused_window = run(2);
      const std::array measurements{
          relative_rms_to(reference, fp32),
          relative_rms_to(native, fp32),
          relative_rms_to(fused_mask, fp32),
          relative_rms_to(fused_window, fp32),
          relative_rms_to(fused_window, fused_mask),
          relative_rms_to(native, reference),
          relative_rms_to(fused_window, reference),
      };
      for (float error : measurements) {
        if (!std::isfinite(error)) {
          throw std::runtime_error("non-finite diagnostic error");
        }
      }
      constexpr std::array diagnostic_names{
          "current_to_fp32", "native_to_fp32", "fused_mask_to_fp32",
          "fused_window_to_fp32", "fused_window_to_fused_mask",
          "native_to_current", "fused_window_to_current",
      };
      for (std::size_t i = 0; i < measurements.size(); ++i) {
        std::cout << "{\"event\":\"precision_diagnostic\",\"keys\":" << k_len
                  << ",\"comparison\":\"" << diagnostic_names[i]
                  << "\",\"relative_rms\":" << measurements[i] << "}\n";
      }
      continue;
    }
    for (int arm = 1; arm < arm_count; ++arm) {
      float relative_rms = relative_rms_to(run(arm), reference);
      std::cout << "{\"event\":\"parity\",\"keys\":" << k_len << ",\"arm\":\""
                << names[arm] << "\",\"relative_rms\":" << relative_rms << "}\n";
      if (!std::isfinite(relative_rms) || relative_rms > 0.007f) {
        throw std::runtime_error("window result differs from Gemma's current mask policy");
      }
    }

    // Keep every mode equally represented in each position of the order.
    for (int repeat = 0; repeat < 18; ++repeat) {
      for (int index = 0; index < arm_count; ++index) {
        const int arm = native_only
            ? (repeat + index) % arm_count
            : (repeat + (repeat < 9 ? index : 2 - index)) % arm_count;
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

#include "model/clover.h"
#include "hub/hub.h"
#include "model/dflash2.h"
#include "model/kparams.h"
#include "util/bf16.h"
#include "util/log.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <unordered_map>

namespace ni {

using json = nlohmann::json;

namespace {

Pipeline pipe(const std::string& n) {
  static std::unordered_map<std::string, Pipeline> cache;
  auto it = cache.find(n);
  if (it == cache.end()) it = cache.emplace(n, Gpu::get().pipeline(n)).first;
  return it->second;
}

json read_json(const std::string& path, bool required) {
  std::ifstream f(path);
  if (!f) {
    if (required) fatal("cannot read %s", path.c_str());
    return json::object();
  }
  json j = json::parse(f, nullptr, false);
  if (j.is_discarded() || !j.is_object()) {
    if (required) fatal("%s: not a JSON object", path.c_str());
    return json::object();
  }
  return j;
}

// src/kernels/clover.metal's parameter blocks
struct CloverPrep {
  uint32_t T, Hk, Hv, C;
};
struct CloverMem {
  uint32_t T, Hk, Hv;
  float lr;
};
struct CloverCoreset {
  uint32_t T, E, k;
  float top_p;
};
struct CloverPick {
  uint32_t V, ld;
  uint32_t mask_id;
  uint32_t nbias;
  float frequency, presence, repetition, temperature;
  uint32_t seed, step;
  uint32_t skip, ncand, sample_out;
};
static_assert(sizeof(CloverRow) == 32, "clover.metal's CloverRow");

float ramp(int pos, int start, int window, float strength) {
  return std::clamp(float(pos - start) / float(window), 0.0f, 1.0f) * strength;
}

}  // namespace

bool Clover::is_model(const std::string& dir) {
  std::ifstream f(dir + "/config.json");
  if (!f) return false;
  const json r = json::parse(f, nullptr, false);
  return r.is_object() && r.value("model_type", std::string()) == "clover_moe";
}

std::string Clover::decode_mode() {
  const char* v = getenv("NI_CLOVER_DECODE");
  const std::string m = v && *v ? v : "auto";
  if (m != "auto" && m != "dflash" && m != "spec" && m != "diffusion")
    fatal("NI_CLOVER_DECODE=%s: auto, dflash, spec or diffusion", m.c_str());
  return m;
}

std::string Clover::find_drafter(const std::string& model_dir) {
  const Qwen35Config c = read_config(model_dir);
  if (std::string d = DFlash2::find(model_dir, c); !d.empty()) return d;
  namespace fs = std::filesystem;
  std::error_code ec;
  std::vector<std::string> packs;
  for (const auto& ent : fs::directory_iterator(hub::models_dir(), ec))
    if (ent.is_directory(ec) && fs::path(model_dir).filename() != ent.path().filename()) packs.push_back(ent.path());
  std::sort(packs.begin(), packs.end());  // (a fixed order: the same drafter every start)
  for (const std::string& p : packs) {
    std::ifstream f(p + "/config.json");
    const json j = f ? json::parse(f, nullptr, false) : json();
    const json t = j.is_object() && j.contains("text_config") ? j["text_config"] : j;
    if (!t.is_object() || t.value("model_type", std::string()).rfind("qwen3_5_moe", 0) != 0) continue;
    if (std::string d = DFlash2::find(p, c); !d.empty() && fs::path(d).parent_path() == fs::path(p)) return d;
  }
  return "";
}

Clover::Clover(const std::string& dir, int prefill_chunk) : Qwen35(dir, prefill_chunk) {
  const json c = read_json(dir + "/config.json", true);
  cfg_block_ = c.value("block_size", 32);
  mask_id_ = c.value("mask_token_id", -1);
  coreset_ = c.value("moe_block_coreset_enabled", true);
  coreset_top_p_ = c.value("moe_block_coreset_top_p", 0.9f);
  if (c.contains("denoising_config") && c["denoising_config"].is_object()) {
    const json& d = c["denoising_config"];
    if (d.value("algorithm", std::string("low_confidence")) != "low_confidence")
      fatal("%s: Clover denoising \"%s\": only low_confidence is supported", dir.c_str(),
            d.value("algorithm", std::string()).c_str());
    threshold_ = d.value("threshold", threshold_);
  }
  if (mask_id_ < 0 || mask_id_ >= cfg_.vocab) fatal("%s: mask_token_id %d is not a token", dir.c_str(), mask_id_);
  if (cfg_block_ < 1 || cfg_block_ > 32) fatal("%s: block_size %d (the kernels take 1 to 32 rows)", dir.c_str(), cfg_block_);
  if (!cfg_.moe || cfg_.experts != 256 || cfg_.top_k > 8)
    fatal("%s: Clover's kernels take 256 experts, at most 8 a token (clover_coreset)", dir.c_str());
  block_ = cfg_block_;
  if (const char* v = getenv("NI_CLOVER_BLOCK"); v && *v) {
    block_ = atoi(v);
    if (block_ < 1 || cfg_block_ % block_) fatal("NI_CLOVER_BLOCK=%s: a divisor of the model's block size %d", v, cfg_block_);
  }
  if (const char* v = getenv("NI_CLOVER_THRESHOLD"); v && *v) {
    threshold_ = float(atof(v));
    if (!(threshold_ >= 0.0f && threshold_ <= 1.0f)) fatal("NI_CLOVER_THRESHOLD=%s: a probability in [0, 1]", v);
  }
  if (const char* v = getenv("NI_CLOVER_CORESET"); v && *v) coreset_ = atoi(v) != 0;
  spec_ = decode_mode() != "diffusion";
  if (const char* v = getenv("NI_CLOVER_DRAFT"); v && *v) {
    draft_ = atoi(v);
    if (draft_ < 2 || draft_ > kMaxVerify || cfg_block_ % draft_)
      fatal("NI_CLOVER_DRAFT=%s: 2 to %d rows, a divisor of the model's block size %d", v, kMaxVerify, cfg_block_);
  }
  if (cfg_block_ % draft_) draft_ = std::min(cfg_block_, 2);
  if (const char* v = getenv("NI_CLOVER_ACCEPT"); v && *v) {
    if (!strcmp(v, "exact")) exact_ = true;
    else if (strcmp(v, "threshold")) fatal("NI_CLOVER_ACCEPT=%s: threshold or exact", v);
  }
  if (const char* v = getenv("NI_CLOVER_ACCEPT_RATIO"); v && *v) accept_ratio_ = float(atof(v));
  if (const char* v = getenv("NI_CLOVER_ACCEPT_DELTA"); v && *v) accept_delta_ = float(atof(v));
  if (!(accept_ratio_ >= 0.0f && accept_ratio_ <= 1.0f) || !(accept_delta_ >= 0.0f))
    fatal("NI_CLOVER_ACCEPT_RATIO / NI_CLOVER_ACCEPT_DELTA: a ratio in [0, 1] and a delta >= 0");

  const json g = read_json(dir + "/generation_config.json", false);
  if (g.empty())
    logi("Clover: no generation_config.json in %s: no generation controls (penalties, ramps), greedy unless a request "
         "sets a temperature", dir.c_str());
  auto num = [&](const char* k, float def) { return g.contains(k) && g[k].is_number() ? g[k].get<float>() : def; };
  auto inum = [&](const char* k, int def) { return g.contains(k) && g[k].is_number_integer() ? g[k].get<int>() : def; };
  ctl_.presence = num("presence_penalty", 0.0f);
  ctl_.frequency = num("frequency_penalty", 0.0f);
  ctl_.repetition = num("repetition_penalty", 1.0f);
  ctl_.length_penalty = num("dllm_length_penalty", 0.0f);
  ctl_.length_start = inum("dllm_length_penalty_start", 8192);
  ctl_.length_window = std::max(1, inum("dllm_length_penalty_window", 8192));
  ctl_.think_bias = num("dllm_think_end_bias", 0.0f);
  ctl_.think_start = inum("dllm_think_end_start", 4096);
  ctl_.think_window = std::max(1, inum("dllm_think_end_window", 4096));
  ctl_.think_close = inum("dllm_think_end_token_id", -1);
  if (!(ctl_.repetition > 0.0f)) fatal("%s: repetition_penalty %g", dir.c_str(), ctl_.repetition);
  if (ctl_.think_bias > 0.0f && (ctl_.think_close < 0 || ctl_.think_close >= cfg_.vocab))
    fatal("%s: dllm_think_end_bias needs dllm_think_end_token_id", dir.c_str());

  // the denoising pass's own weights: per GDN layer the right convolution and the softmax's three scalars per head
  const int Hv = cfg_.lin_hv;
  const size_t C = 2 * size_t(cfg_.lin_hk) * cfg_.lin_dk + size_t(Hv) * cfg_.lin_dv;
  conv_r_.assign(size_t(cfg_.layers), nullptr);
  sc_ = Gpu::get().alloc(size_t(cfg_.layers) * 3 * Hv * 4 + 16, "clover_scalars", false);
  float* sc = sc_.as<float>();
  for (int i = 0; i < cfg_.layers; ++i) {
    if (!cfg_.is_linear[i]) continue;
    const std::string a = "model.layers." + std::to_string(i) + ".linear_attn.";
    const Tensor* r = ws_.find(tname(a + "conv_right_weight"));
    if (!r || r->dtype != DType::BF16 || size_t(r->numel()) != C * 3)
      fatal("%s: %s is not bf16 [%zu, 1, 3]", dir.c_str(), tname(a + "conv_right_weight").c_str(), C);
    conv_r_[size_t(i)] = r;
    const char* names[3] = {"bd_softmax_logit_scale", "bd_softmax_history_bias", "bd_softmax_history_c"};
    for (int j = 0; j < 3; ++j) {
      const Tensor* t = ws_.find(tname(a + names[j]));
      if (!t || t->numel() != Hv) fatal("%s: %s missing or not [%d]", dir.c_str(), tname(a + names[j]).c_str(), Hv);
      for (int h = 0; h < Hv; ++h) {
        const float v = t->dtype == DType::BF16  ? bf16_to_f32(t->buf.as<uint16_t>()[h])
                        : t->dtype == DType::F32 ? t->buf.as<float>()[h]
                        : t->dtype == DType::F16 ? float(t->buf.as<_Float16>()[h])
                                                 : (fatal("%s: %s of an unsupported dtype", dir.c_str(), names[j]), 0.0f);
        sc[(size_t(i) * 3 + j) * Hv + h] = v;
      }
    }
  }
  const size_t V = size_t(cfg_.vocab);
  Gpu& g_ = Gpu::get();
  lg_ = g_.alloc(32 * V * 4, "clover_logits");
  counts_ = g_.alloc(V * 4, "clover_counts");
  bias_ids_ = g_.alloc(64, "clover_bias_ids");
  bias_ = g_.alloc(32 * 4 * 4, "clover_bias");
  ptok_ = g_.alloc(32 * 4, "clover_tokens");
  rows_ = g_.alloc(32 * sizeof(CloverRow), "clover_rows");
  Gpu::get().make_resident({sc_, lg_, counts_, bias_ids_, bias_, ptok_, rows_});
  for (const char* n : {"clover_gdn_prep", "clover_gdn_mem", "clover_coreset", "clover_pick", "attn_prefill11gs_bidi",
                        "attn11_reduce", "attn_prep", "gdn_gnorm"})
    pipe(n);
  char how[160];
  if (block_drafter_ok())
    snprintf(how, sizeof how, "the DFlash2 drafter's loop when one is found (else self-speculative, %d-row cycles)",
             draft_);
  else if (spec_)
    snprintf(how, sizeof how, "self-speculative, %d-row cycles, %s acceptance", draft_,
             exact_ ? "exact" : "threshold");
  else
    snprintf(how, sizeof how, "block diffusion, %d-row blocks, threshold %.2f", block_, threshold_);
  logi("Clover: %s, mask token %d, expert coreset %s; controls: presence %.2f, frequency %.2f, repetition %.2f, "
       "end-of-reply ramp %.1f from %d, </think> ramp %.1f from %d",
       how, mask_id_, coreset_ ? "on" : "off", ctl_.presence, ctl_.frequency, ctl_.repetition, ctl_.length_penalty,
       ctl_.length_start, ctl_.think_bias, ctl_.think_start);
}

std::string Clover::disk_format() const { return "clover " + Qwen35::disk_format(); }

void Clover::enc_coreset(Encoder& e, int T) {
  const uint32_t E = uint32_t(cfg_.experts);
  const CloverCoreset cp{uint32_t(T), E, uint32_t(cfg_.top_k), coreset_top_p_};
  e.use(pipe("clover_coreset"));
  e.buf(0, rlog_);
  e.val(1, cp);
  e.dispatch(1, 1, 1, E);
}

void Clover::enc_topk_rows(Encoder& e, uint32_t E, uint32_t k, bool norm, int T) {
  if (preview_ && coreset_) enc_coreset(e, T);
  Qwen35::enc_topk_rows(e, E, k, norm, T);
}

void Clover::enc_router_hook(Encoder& e, int R) {
  if (preview_ && coreset_) enc_coreset(e, R);
}

void Clover::enc_gdn_mix(Encoder& e, Seq& s, int li, const Layer& L, int T) {
  const uint32_t C = 2 * cfg_.lin_hk * cfg_.lin_dk + cfg_.lin_hv * cfg_.lin_dv, Hv = uint32_t(cfg_.lin_hv);
  const CloverPrep pp{uint32_t(T), uint32_t(cfg_.lin_hk), Hv, C};
  e.use(pipe("clover_gdn_prep"));
  e.buf(0, qkv_); e.buf(1, ab_); e.buf(2, s.conv[li]); e.buf(3, L.conv_w->buf); e.buf(4, conv_r_[size_t(li)]->buf);
  e.buf(5, L.A_log->buf); e.buf(6, L.dt_bias->buf);
  e.buf(7, gq_); e.buf(8, gk_); e.buf(9, gv_); e.buf(10, gg_);
  e.val(11, pp);
  e.dispatch(C / 128 + 1, 1, 1, 128);
  const CloverMem mp{uint32_t(T), uint32_t(cfg_.lin_hk), Hv, std::log(float(T) / float(cfg_block_))};
  e.use(pipe("clover_gdn_mem"));
  e.buf(0, gq_); e.buf(1, gk_); e.buf(2, gv_); e.buf(3, gg_); e.buf(4, s.rec[li]);
  e.buf(5, sc_, size_t(li) * 3 * Hv * 4); e.buf(6, gout_);
  e.val(7, mp);
  e.dispatch(Hv, 4, 1, 128);
}

void Clover::enc_attn_bidi(Encoder& e, Seq& s, int li, const Layer& L, int pos0, int T) {
  // the block's K / V go to the cache rows pos0 .. pos0 + T (the next causal pass rewrites them)
  const kp::AttnPrep ap{uint32_t(T), uint32_t(cfg_.hq), uint32_t(cfg_.hkv), uint32_t(cfg_.head_dim),
                        uint32_t(cfg_.rot_dims), uint32_t(pos0), uint32_t(s.cap), cfg_.eps, cfg_.theta};
  e.use(pipe("attn_prep"));
  e.buf(0, qg_); e.buf(1, kr_); e.buf(2, vr_); e.buf(3, L.q_norm->buf); e.buf(4, L.k_norm->buf);
  e.buf(5, qo_); e.buf(6, s.kc[li]); e.buf(7, s.vc[li]);
  e.val(8, ap);
  e.dispatch(cfg_.hq + 2 * cfg_.hkv, T, 1, cfg_.head_dim);
  // every row sees keys [0, pos0 + T): (query, head) rows of a KV head in 32-row blocks, the keys split over grid.z
  // (about 8 key tiles of 32 each, at most 16 splits), combined by attn11_reduce
  const kp::AttnPref fp{uint32_t(T), uint32_t(cfg_.hq), uint32_t(cfg_.hkv), uint32_t(pos0), uint32_t(s.cap),
                        1.0f / std::sqrt(float(cfg_.head_dim))};
  const uint32_t G = uint32_t(cfg_.hq / cfg_.hkv), tiles = (uint32_t(pos0 + T) + 31) / 32;
  const uint32_t ns = std::clamp(tiles / 8, 1u, std::min(16u, 1024u / uint32_t(T))), zero = 0;
  e.use(pipe("attn_prefill11gs_bidi"));
  e.buf(0, qo_); e.buf(1, s.kc[li]); e.buf(2, s.vc[li]); e.buf(3, qg_); e.buf(4, attn_out_);
  e.val(5, fp);
  e.buf(6, part_o_); e.buf(7, part_ml_);
  e.val(8, ns);
  e.dispatch((uint32_t(T) * G + 31) / 32, uint32_t(cfg_.hkv), ns, 256);
  e.use(pipe("attn11_reduce"));
  e.buf(0, part_o_); e.buf(1, part_ml_); e.buf(2, qg_); e.buf(3, attn_out_);
  e.val(4, fp);
  e.val(5, ns);
  e.val(6, zero);
  e.dispatch(uint32_t(T), uint32_t(cfg_.hq), 1, uint32_t(cfg_.head_dim));
}

void Clover::enc_denoise(Encoder& e, Seq& s, int pos0, int T) {
  if (T < 1 || T > 32 || T > tmax_) fatal("Clover: a denoising pass of %d rows", T);
  if (pos0 + T >= s.cap) fatal("context full (%d)", s.cap);
  const int D = cfg_.hidden;
  const uint32_t Hv = uint32_t(cfg_.lin_hv);
  enc_embed(e, s.tok, pos0, T, x_);
  preview_ = true;
  for (int i = 0; i < cfg_.layers; ++i) {
    const Layer& L = layers_[i];
    enc_rows_half(e, x_, L.in_norm, xh_, T, D);
    if (L.linear) {
      enc_proj(e, {{&L.qkv, qkv_, false}, {&L.z, zb_, false}, {&L.b, bb_, false}, {&L.a, ab_, false}}, xh_, T);
      enc_gdn_mix(e, s, i, L, T);
      const kp::GdnStep sp{uint32_t(T), uint32_t(cfg_.lin_hk), Hv, cfg_.eps};
      e.use(pipe("gdn_gnorm"));
      e.buf(0, gout_); e.buf(1, zb_); e.buf(2, L.gnorm->buf); e.buf(3, hh_);
      e.val(4, sp);
      e.dispatch((uint32_t(T) * Hv + 7) / 8, 1, 1, 256);
      enc_qmm(e, L.out, hh_, x_, T, true);
    } else {
      enc_proj(e, {{&L.q, qg_, false}, {&L.k, kr_, false}, {&L.v, vr_, false}}, xh_, T);
      enc_attn_bidi(e, s, i, L, pos0, T);
      enc_rows_half(e, attn_out_, nullptr, hh_, T, cfg_.hq * cfg_.head_dim);
      enc_qmm(e, L.o, hh_, x_, T, true);
    }
    enc_moe_prefill(e, L, T, x_);
  }
  preview_ = false;
  encode_logits_rows(e, T, lg_);
}

void Clover::enc_denoise8(Encoder& e, Seq& s, int pos0, int R) {
  if (R < 1 || R > kMaxVerify) fatal("Clover: an 8-row denoising pass of %d rows", R);
  if (pos0 + R >= s.cap) fatal("context full (%d)", s.cap);
  v8_alloc();
  const int D = cfg_.hidden, VD = cfg_.lin_hv * cfg_.lin_dv, HD = cfg_.hq * cfg_.head_dim;
  const uint32_t C = 2 * cfg_.lin_hk * cfg_.lin_dk + cfg_.lin_hv * cfg_.lin_dv;
  const kp::GdnVerify gv{uint32_t(R), 0u, uint32_t(cfg_.lin_hk), uint32_t(cfg_.lin_hv), C, cfg_.eps, 0u, 0u, 0u};
  enc_embed(e, s.tok, pos0, R, x_);
  preview_ = true;
  bool table_ready = false;  // the previous layer's MoE combine wrote this layer's input-norm table
  for (int i = 0; i < cfg_.layers; ++i) {
    const Layer& L = layers_[i];
    const bool ti = table_ready ? v8_tw() : enc_x8(e, x_, R, D, L.in_norm, false, 0, nullptr, true);
    if (L.linear) {
      enc_qmm8(e, {{&L.qkv, qkv_}, {&L.z, zb_}, {&L.b, bb_}, {&L.a, ab_}}, R, v8t_, v8s_, false, ti ? &v8tt_ : nullptr);
      enc_gdn_mix(e, s, i, L, R);
      // the gated norm straight into the out projection's tables
      const bool tgn = v8_tw() && size_t(VD) * 16 <= v8tt_.size;
      e.use(pipe(tgn ? "gdn_gnorm_x8t" : "gdn_gnorm_x8"));
      e.buf(0, gout_); e.buf(1, zb_); e.buf(2, L.gnorm->buf); e.buf(3, v8t_); e.buf(4, v8s_);
      e.val(5, gv);
      if (tgn) e.buf(6, v8tt_);
      e.dispatch(uint32_t(cfg_.lin_hv), 1, 1, 256);
      enc_qmm8(e, {{&L.out, x_, uint32_t(D), true}}, R, v8t_, v8s_, false, tgn ? &v8tt_ : nullptr);
    } else {
      enc_qmm8(e, {{&L.q, qg_}, {&L.k, kr_}, {&L.v, vr_}}, R, v8t_, v8s_, false, ti ? &v8tt_ : nullptr);
      enc_attn_bidi(e, s, i, L, pos0, R);
      const bool to = enc_x8(e, attn_out_, R, HD, nullptr, false, 0, nullptr, true);
      enc_qmm8(e, {{&L.o, x_, uint32_t(D), true}}, R, v8t_, v8s_, false, to ? &v8tt_ : nullptr);
    }
    table_ready = enc_moe8(e, L, R, i, i + 1 < cfg_.layers ? layers_[i + 1].in_norm : final_norm_);
    if (i == 1) e.split();  // the GPU starts on the first layers while the host encodes the rest
  }
  preview_ = false;
  const bool tl = table_ready ? v8_tw() : enc_x8(e, x_, R, D, final_norm_, false, 0, nullptr, true);
  enc_qmm8(e, {{&lm_head_, lg_}}, R, v8t_, v8s_, false, tl ? &v8tt_ : nullptr);
}

void Clover::set_controls(const CloverReply& reply, const std::vector<int>& stops, int T, int first, bool think_all,
                          int think_min, bool close_seen) {
  if (reply.counts.size() != size_t(cfg_.vocab)) fatal("Clover: the reply's counts are not the vocabulary's");
  memcpy(counts_.as<uint32_t>(), reply.counts.data(), reply.counts.size() * 4);
  uint32_t* ids = bias_ids_.as<uint32_t>();
  float* bias = bias_.as<float>();
  uint32_t nb = 0;
  if (ctl_.length_penalty > 0.0f)
    for (int id : stops)
      if (nb < 3 && id >= 0 && id < cfg_.vocab && std::find(ids, ids + nb, uint32_t(id)) == ids + nb) ids[nb++] = uint32_t(id);
  const uint32_t n_stop = nb;
  // the thinking control: until a </think> is in the reply (or shows in the rows); every row (Hugging Face), or the
  // first row past its start alone (SGLang)
  const bool think = ctl_.think_bias > 0.0f && ctl_.think_close >= 0 && reply.counts[size_t(ctl_.think_close)] == 0 &&
                     !close_seen;
  const int think_row = think_all ? -1 : std::max(think_min, ctl_.think_start + 1 - first);
  if (ctl_.think_bias > 0.0f && ctl_.think_close >= 0) ids[nb++] = uint32_t(ctl_.think_close);
  for (int r = 0; r < T; ++r) {
    const int pos = first + r;
    for (uint32_t i = 0; i < 4; ++i) bias[r * 4 + i] = 0.0f;
    for (uint32_t i = 0; i < n_stop; ++i) bias[r * 4 + i] = ramp(pos, ctl_.length_start, ctl_.length_window, ctl_.length_penalty);
    if (nb > n_stop && think && (think_all || r == think_row))
      bias[r * 4 + n_stop] = ramp(pos, ctl_.think_start, ctl_.think_window, ctl_.think_bias);
  }
  nbias_ = nb;
}

void Clover::enc_pick(Encoder& e, const Buffer& logits, uint32_t ld, int T, const SamplingParams& sp, uint32_t step,
                      const Buffer& tok_out, size_t tok_off, uint32_t skip, bool sample_out, const Buffer& cand,
                      size_t cand_off, uint32_t ncand) {
  const CloverPick pk{uint32_t(cfg_.vocab), ld, uint32_t(mask_id_), nbias_, ctl_.frequency,
                      ctl_.presence, ctl_.repetition, sp.temperature > 0.0f ? sp.temperature : 0.0f, sp.seed, step,
                      skip, ncand, sample_out ? 1u : 0u};
  e.use(pipe("clover_pick"));
  e.buf(0, logits); e.buf(1, counts_); e.buf(2, bias_ids_); e.buf(3, bias_);
  e.buf(4, tok_out, tok_off); e.buf(5, rows_);
  e.val(6, pk);
  e.buf(7, cand, cand_off);
  e.dispatch(uint32_t(T), 1, 1, 1024);
}

void Clover::encode_preview(Encoder& e, Seq& s, int pos0, int T, const CloverReply& reply, const std::vector<int>& stops,
                            const SamplingParams& sp, uint32_t step) {
  enc_denoise(e, s, pos0, T);
  // row r is reply position length + r + 1, every row under the thinking control until a </think> shows in the block
  bool seen = false;
  for (int r = 0; r < T && !seen; ++r) seen = ctl_.think_close >= 0 && s.tokens()[pos0 + r] == ctl_.think_close;
  set_controls(reply, stops, T, reply.length + 1, true, 0, seen);
  enc_pick(e, lg_, uint32_t(cfg_.vocab), T, sp, step, ptok_, 0, 0, sp.temperature > 0.0f, ptok_, 0, 0);
}

void Clover::encode_draft(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                          const SamplingParams& sp, uint32_t step) {
  if (W < 2 || W > kMaxVerify) fatal("Clover: a cycle of %d rows", W);
  if (P + W + 1 >= s.cap) fatal("context full (%d)", s.cap);
  encode_flush(e, s);  // the rows the last cycle kept, into the state the denoising pass reads
  int* tk = s.tokens();
  for (int r = 1; r < W; ++r) tk[P + r] = mask_id_;
  // row 0 is the pending token (reply position length), row r drafts position length + r; the argmaxes go to
  // tokens[P + 1 ..]
  enc_denoise8(e, s, P, W);
  set_controls(reply, stops, W, reply.length, false, 1, ctl_.think_close >= 0 && tk[P] == ctl_.think_close);
  enc_pick(e, lg_, uint32_t(cfg_.vocab), W, sp, step, s.tok, size_t(P) * 4, 1, false, ptok_, 0, 0);
}

void Clover::encode_check(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                          const SamplingParams& sp, uint32_t step) {
  // row r predicts position length + r + 1 and checks the draft tokens[P + r + 1]
  encode_verify(e, s, P, W, sp, step, /*v8=*/true);
  set_controls(reply, stops, W, reply.length + 1, false, 0, false);
  enc_pick(e, logits_, uint32_t(cfg_.vocab), W, sp, step + 1, ptok_, 0, uint32_t(W), false, s.tok, size_t(P + 1) * 4,
           uint32_t(W - 1));
}

void Clover::encode_cycle(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                          const SamplingParams& sp, uint32_t step) {
  encode_draft(e, s, P, W, reply, stops, sp, step);
  encode_check(e, s, P, W, reply, stops, sp, step);
}

bool Clover::accept_draft(const CloverRow& r, int draft, bool exact, float ratio, float delta) {
  if (exact) return draft == r.tok;
  return r.pc > 0.0f && r.pc >= std::min(ratio, delta * std::exp(-r.ent));
}

}  // namespace ni

#include "common.h"

// Clover-35B-A3B (src/model/clover.h): the denoising pass of a block of T <= 32 rows, which reads the committed
// state and changes none of it. Its Gated DeltaNet layers replace the recurrence with a softmax over the block's rows
// and one "history" bucket (the committed state's readout), and their convolution also looks right, at the next three
// rows of the block. The routed experts of a block come from a shared set (the coreset), and the pick reduces each
// row's logits to the most likely token and its probability.

// ---- GDN preview: convolution (3 committed rows on the left, 3 block rows on the right) + SiLU + q/k L2 norm ----
// As gdn_prep (one threadgroup of 128 threads per 128-channel head chunk; the last threadgroup writes the decay), with
// conv_state only read and no beta: q_out = l2norm(q) / sqrt(128), k_out = l2norm(k), v_out = v, g_out = exp(g).
// conv_r: the right weights, bf16 [C, 3] (distance 1, 2, 3).
struct CloverPrepParams {
  uint T;
  uint Hk;
  uint Hv;
  uint C;
};

[[kernel]] void clover_gdn_prep(const device float* qkv [[buffer(0)]], const device float* a [[buffer(1)]],
                                const device float* conv_state [[buffer(2)]], const device bfloat* conv_w [[buffer(3)]],
                                const device bfloat* conv_r [[buffer(4)]], const device bfloat* A_log [[buffer(5)]],
                                const device bfloat* dt_bias [[buffer(6)]], device float* q_out [[buffer(7)]],
                                device float* k_out [[buffer(8)]], device float* v_out [[buffer(9)]],
                                device float* g_out [[buffer(10)]], constant CloverPrepParams& p [[buffer(11)]],
                                uint tg [[threadgroup_position_in_grid]], uint tid [[thread_position_in_threadgroup]]) {
  threadgroup float scratch[32];
  constexpr uint D = 128;
  const uint C = p.C;
  if (tg == C / D) {
    if (tid < p.Hv) {
      const float A = metal::precise::exp(float(A_log[tid]));
      const float dtb = float(dt_bias[tid]);
      for (uint t = 0; t < p.T; ++t) g_out[t * p.Hv + tid] = metal::precise::exp(-A * softplus(a[t * p.Hv + tid] + dtb));
    }
    return;
  }
  const uint c = tg * D + tid;
  const uint qk = p.Hk * D;
  const bool is_q = c < qk, is_k = c >= qk && c < 2 * qk;
  const float w0 = conv_w[c * 4 + 0], w1 = conv_w[c * 4 + 1], w2 = conv_w[c * 4 + 2], w3 = conv_w[c * 4 + 3];
  const float r1 = conv_r[c * 3 + 0], r2 = conv_r[c * 3 + 1], r3 = conv_r[c * 3 + 2];
  for (uint t = 0; t < p.T; ++t) {
    // concat = [state0, state1, state2, qkv[0], qkv[1], ...]: the left taps read concat[t..t+3]
    const float in0 = t + 0 < 3 ? conv_state[(t + 0) * C + c] : qkv[(t + 0 - 3) * C + c];
    const float in1 = t + 1 < 3 ? conv_state[(t + 1) * C + c] : qkv[(t + 1 - 3) * C + c];
    const float in2 = t + 2 < 3 ? conv_state[(t + 2) * C + c] : qkv[(t + 2 - 3) * C + c];
    float acc = w0 * in0 + w1 * in1 + w2 * in2 + w3 * qkv[t * C + c];
    if (t + 1 < p.T) acc += r1 * qkv[(t + 1) * C + c];
    if (t + 2 < p.T) acc += r2 * qkv[(t + 2) * C + c];
    if (t + 3 < p.T) acc += r3 * qkv[(t + 3) * C + c];
    float o = silu(acc);
    if (is_q || is_k) {  // (uniform over the threadgroup: a chunk is all q, all k or all v)
      const float ss = tg_sum(o * o, scratch, tid, D);
      o *= metal::precise::rsqrt(ss + 1e-6f);
      if (is_q) q_out[t * qk + c] = o * metal::precise::rsqrt(float(D));
      else k_out[t * qk + (c - qk)] = o;
    } else {
      v_out[t * (C - 2 * qk) + (c - 2 * qk)] = o;
    }
  }
}

// ---- GDN preview: the block's softmax memory ----
// Per value head h and row l (q, k of key head h / (Hv / Hk), l2-normalized):
//   logits[l, s] = scale[h] * (q_l . k_s)  over the block's rows s, and the history bucket's logit bias[h] + c[h] * lr
//   (lr = log(T / 32)); w = softmax over those T + 1 entries;
//   out[l] = sum_s w[l, s] v_s + w[l, T] * exp(g_l) * (S q_l / sqrt(128))   (S: the committed state, [Dv][Dk])
// grid: (Hv, 4) threadgroups of 128 threads; a threadgroup computes its head's weights and 32 value rows (8 per
// simdgroup, the lanes along a state row: coalesced reads). q holds q / sqrt(128) (clover_gdn_prep). sc: fp32 [3][Hv]
// (logit scale, history bias, history c). out: fp32 [T, Hv, 128] (gdn_gnorm's input).
struct CloverMemParams {
  uint T;
  uint Hk;
  uint Hv;
  float lr;
};

[[kernel]] void clover_gdn_mem(const device float* q [[buffer(0)]], const device float* k [[buffer(1)]],
                               const device float* v [[buffer(2)]], const device float* g [[buffer(3)]],
                               const device float* state [[buffer(4)]], const device float* sc [[buffer(5)]],
                               device float* out [[buffer(6)]], constant CloverMemParams& p [[buffer(7)]],
                               uint2 tg [[threadgroup_position_in_grid]], uint tid [[thread_index_in_threadgroup]],
                               uint nsg [[simdgroups_per_threadgroup]], uint sg [[simdgroup_index_in_threadgroup]],
                               uint lane [[thread_index_in_simdgroup]]) {
  constexpr uint D = 128, TM = 32, RS = 8;  // rows per simdgroup
  const uint ntg = nsg * 32;
  threadgroup float w[TM][TM + 1];
  const uint T = min(p.T, TM), h = tg.x;
  const uint hk = h / (p.Hv / p.Hk);
  // the block's weights: (l, s) dots spread over the threadgroup; q . k * sqrt(128) = the unit vectors' dot
  const float ls = sc[h] * metal::precise::sqrt(float(D));
  for (uint pr = tid; pr < T * T; pr += ntg) {
    const uint l = pr / T, s = pr % T;
    const device float4* q4 = (const device float4*)(q + (l * p.Hk + hk) * D);
    const device float4* k4 = (const device float4*)(k + (s * p.Hk + hk) * D);
    float d = 0.0f;
    for (uint j = 0; j < D / 4; ++j) d += dot(q4[j], k4[j]);
    w[l][s] = d * ls;
  }
  if (tid < T) w[tid][T] = sc[p.Hv + h] + sc[2 * p.Hv + h] * p.lr;
  threadgroup_barrier(mem_flags::mem_threadgroup);
  if (tid < T) {
    float m = -INFINITY;
    for (uint s = 0; s <= T; ++s) m = max(m, w[tid][s]);
    float z = 0.0f;
    for (uint s = 0; s <= T; ++s) {
      const float e = metal::precise::exp(w[tid][s] - m);
      w[tid][s] = e;
      z += e;
    }
    const float inv = 1.0f / z;
    for (uint s = 0; s <= T; ++s) w[tid][s] *= inv;
  }
  threadgroup_barrier(mem_flags::mem_threadgroup);
  // value rows: the history readout (S q_l)[dv] summed over the lanes, then lane l writes row l's output
  const uint dv0 = (tg.y * nsg + sg) * RS;
  const float gl = lane < T ? g[lane * p.Hv + h] : 0.0f;
  for (uint r = 0; r < RS; ++r) {
    const uint dv = dv0 + r;
    const float4 s4 = *(const device float4*)(state + (h * D + dv) * D + lane * 4);
    float hist = 0.0f;
    for (uint l = 0; l < T; ++l) {
      const float x = simd_sum(dot(s4, *(const device float4*)(q + (l * p.Hk + hk) * D + lane * 4)));
      if (lane == l) hist = x;
    }
    if (lane < T) {
      float o = w[lane][T] * hist * gl;
      for (uint s = 0; s < T; ++s) o += w[lane][s] * v[(s * p.Hv + h) * D + dv];
      out[(lane * p.Hv + h) * D + dv] = o;
    }
  }
}

// ---- MoE preview: the block's expert coreset ----
// Every row's top-k experts by router logit (ties: the lower index) add their softmax probability to the expert's
// total; the experts ranked by total (normalized), highest first, are kept while the mass ranked before them is below
// top_p (the first always), and the others' logits are set to -1e30 for every row, so the routing (moe_topk_rows*,
// moe8_plan) picks the row's top-k among the kept ones. One threadgroup of 256 threads or more (a thread per expert:
// E = 256, which the host checks, p.E is not read; k <= 8, T <= 32): a simdgroup takes a row's top-k at a time (each
// lane 8 experts in registers, as moe_topk_rows8).
#define NI_UNROLL_CLOVER _Pragma("clang loop unroll(full)")
struct CloverCoresetParams {
  uint T;
  uint E;
  uint k;
  float top_p;
};

[[kernel]] void clover_coreset(device float* logits [[buffer(0)]], constant CloverCoresetParams& p [[buffer(1)]],
                               uint e [[thread_position_in_threadgroup]], uint ntg [[threads_per_threadgroup]],
                               uint sg [[simdgroup_index_in_threadgroup]], uint lane [[thread_index_in_simdgroup]]) {
  constexpr uint per = 8;
  threadgroup float sel_w[32 * 8];
  threadgroup uint sel_i[32 * 8];
  threadgroup float prob[256];
  threadgroup float scratch[32];
  const uint nsg = ntg / 32;
  for (uint t = sg; t < p.T; t += nsg) {
    float x[per];
    float mx = -INFINITY;
    NI_UNROLL_CLOVER for (uint i = 0; i < per; ++i) mx = max(mx, x[i] = logits[t * 256 + lane * per + i]);
    mx = simd_max(mx);
    float z = 0.0f;
    NI_UNROLL_CLOVER for (uint i = 0; i < per; ++i) z += metal::precise::exp(x[i] - mx);
    z = simd_sum(z);
    uint taken = 0;
    for (uint r = 0; r < p.k; ++r) {
      float best = -INFINITY;
      uint bi = 0xffffffffu;
      NI_UNROLL_CLOVER for (uint i = 0; i < per; ++i)
        if (!(taken & (1u << i)) && x[i] > best) best = x[i], bi = lane * per + i;
      const float gbest = simd_max(best);
      const uint win = simd_min(best == gbest ? bi : 0xffffffffu);
      if (win / per == lane) taken |= 1u << (win % per);
      if (lane == 0) {
        sel_i[t * 8 + r] = win;
        sel_w[t * 8 + r] = metal::precise::exp(gbest - mx) / z;
      }
    }
  }
  threadgroup_barrier(mem_flags::mem_threadgroup);
  const bool live = e < 256;
  float total = 0.0f;
  for (uint j = 0; j < p.T * 8; ++j)
    if (j % 8 < p.k && sel_i[j] == e) total += sel_w[j];
  const float sum = tg_sum(total, scratch, e, ntg);
  const float pr = total / max(sum, 1e-9f);
  if (live) prob[e] = pr;
  threadgroup_barrier(mem_flags::mem_threadgroup);
  if (!live) return;
  float before = 0.0f;
  uint rank = 0;
  for (uint j = 0; j < 256; ++j) {
    const float o = prob[j];
    if (o > pr || (o == pr && j < e)) {
      before += o;
      ++rank;
    }
  }
  if (rank == 0 || before < p.top_p) return;
  for (uint t = 0; t < p.T; ++t) logits[t * 256 + e] = -1e30f;
}

// ---- the pick: each row's most likely token, its probability, and what the self-speculative acceptance reads ----
// Row t's logits (fp32, ld floats apart, V of them) with the generation controls applied in SGLang's order: the mask
// token removed, then for every id the committed reply holds (counts[id] > 0) l -= frequency * count, l -= presence,
// then the repetition penalty (l * rep below zero, l / rep above), then the additive biases of up to 4 ids
// (bias[t * 4 + i] for ids[i]: the length and thinking controls). Per row (rows[t]): the argmax (ties: the lower id)
// and its probability; with temperature > 0 a draw from softmax(l / temperature) (Gumbel-max, an id-hashed uniform per
// element; top-k / top-p not applied) and its temperature-1 probability, else the argmax again; for t < ncand the
// probability of the candidate cand[t]; and the entropy of softmax(l). tok_out[t] (t >= skip) gets the draw (sample_out)
// or the argmax: a draft writes its rows' picks into the sequence's tokens there. grid: T threadgroups x 1024 threads.
struct CloverPickParams {
  uint V, ld;
  uint mask_id;
  uint nbias;
  float frequency, presence, repetition, temperature;
  uint seed, step;
  uint skip, ncand, sample_out;
};

struct CloverRow {
  int tok, smp;
  float conf, conf_smp, pc, ent;
  float pad0, pad1;
};

NI_INLINE uint clover_hash(uint v) {
  uint state = v * 747796405u + 2891336453u;
  uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
  return (word >> 22u) ^ word;
}

// (m, z, s1): running max, sum of exp(l - m) and sum of exp(l - m) (l - m), merged with another such triple
NI_INLINE void clover_merge(thread float& m, thread float& z, thread float& s1, float m2, float z2, float s2) {
  if (m2 == -INFINITY) return;
  if (m == -INFINITY) {
    m = m2, z = z2, s1 = s2;
    return;
  }
  const float M = max(m, m2);
  const float a = metal::precise::exp(m - M), b = metal::precise::exp(m2 - M);
  s1 = a * (s1 + (m - M) * z) + b * (s2 + (m2 - M) * z2);
  z = a * z + b * z2;
  m = M;
}

[[kernel]] void clover_pick(const device float* logits [[buffer(0)]], const device uint* counts [[buffer(1)]],
                            const device uint* ids [[buffer(2)]], const device float* bias [[buffer(3)]],
                            device int* tok_out [[buffer(4)]], device CloverRow* rows [[buffer(5)]],
                            constant CloverPickParams& p [[buffer(6)]], const device int* cand [[buffer(7)]],
                            uint t [[threadgroup_position_in_grid]], uint tid [[thread_position_in_threadgroup]],
                            uint ntg [[threads_per_threadgroup]], uint sg [[simdgroup_index_in_threadgroup]],
                            uint lane [[thread_index_in_simdgroup]]) {
  threadgroup float tm[32], tz[32], ts1[32], tka[32], tks[32], tla[32], tls[32], tlc[32];
  threadgroup uint tia[32], tis[32];
  const device float* row = logits + size_t(t) * p.ld;
  const uint cid = t < p.ncand ? uint(cand[t]) : 0xffffffffu;
  float m = -INFINITY, z = 0.0f, s1 = 0.0f;   // softmax(l): max, sum of exp(l - m), sum of exp(l - m) (l - m)
  float ka = -INFINITY, ks = -INFINITY;       // best l (argmax) and best key (the draw)
  float ls = -INFINITY, lc = -INFINITY;       // the draw's l, the candidate's l
  uint ia = 0xffffffffu, is = 0xffffffffu;
  const uint salt = clover_hash(p.seed ^ clover_hash(p.step * 64u + t));
  for (uint v = tid; v < p.V; v += ntg) {
    if (v == p.mask_id) continue;
    float l = row[v];
    const uint c = counts[v];
    if (c) {
      l -= p.frequency * float(c);
      l -= p.presence;
      l = l < 0.0f ? l * p.repetition : l / p.repetition;
    }
    for (uint i = 0; i < p.nbias; ++i)
      if (v == ids[i]) l += bias[t * 4 + i];
    if (l > m) {
      clover_merge(m, z, s1, l, 1.0f, 0.0f);
    } else {
      const float e = metal::precise::exp(l - m);
      z += e;
      s1 += e * (l - m);
    }
    if (v == cid) lc = l;
    if (l > ka || (l == ka && v < ia)) ka = l, ia = v;
    if (p.temperature > 0.0f) {
      const float u = (float(clover_hash(salt ^ (v * 2654435761u)) >> 8) + 0.5f) * (1.0f / 16777216.0f);
      const float key = l / p.temperature - metal::precise::log(-metal::precise::log(u));
      if (key > ks || (key == ks && v < is)) ks = key, ls = l, is = v;
    }
  }
  // the simdgroup's, then the threadgroup's
  for (ushort o = 16; o > 0; o /= 2) {
    clover_merge(m, z, s1, simd_shuffle_xor(m, o), simd_shuffle_xor(z, o), simd_shuffle_xor(s1, o));
    lc = max(lc, simd_shuffle_xor(lc, o));
    const float ka2 = simd_shuffle_xor(ka, o), ks2 = simd_shuffle_xor(ks, o), ls2 = simd_shuffle_xor(ls, o);
    const uint ia2 = simd_shuffle_xor(ia, o), is2 = simd_shuffle_xor(is, o);
    if (ka2 > ka || (ka2 == ka && ia2 < ia)) ka = ka2, ia = ia2;
    if (ks2 > ks || (ks2 == ks && is2 < is)) ks = ks2, ls = ls2, is = is2;
  }
  if (lane == 0) {
    tm[sg] = m, tz[sg] = z, ts1[sg] = s1, tlc[sg] = lc;
    tka[sg] = ka, tia[sg] = ia, tks[sg] = ks, tls[sg] = ls, tis[sg] = is;
  }
  threadgroup_barrier(mem_flags::mem_threadgroup);
  if (tid != 0) return;
  const uint nsg = (ntg + 31) / 32;
  for (uint g = 1; g < nsg; ++g) {
    clover_merge(m, z, s1, tm[g], tz[g], ts1[g]);
    lc = max(lc, tlc[g]);
    if (tka[g] > ka || (tka[g] == ka && tia[g] < ia)) ka = tka[g], ia = tia[g];
    if (tks[g] > ks || (tks[g] == ks && tis[g] < is)) ks = tks[g], ls = tls[g], is = tis[g];
  }
  if (p.temperature <= 0.0f) is = ia, ls = ka;
  CloverRow r;
  r.tok = int(ia);
  r.smp = int(is);
  r.conf = metal::precise::exp(ka - m) / z;
  r.conf_smp = metal::precise::exp(ls - m) / z;
  r.pc = lc == -INFINITY ? 0.0f : metal::precise::exp(lc - m) / z;
  r.ent = metal::precise::log(z) - s1 / z;
  r.pad0 = r.pad1 = 0.0f;
  rows[t] = r;
  if (t >= p.skip) tok_out[t] = p.sample_out ? int(is) : int(ia);
}

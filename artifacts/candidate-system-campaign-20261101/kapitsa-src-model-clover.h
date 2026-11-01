// Clover-35B-A3B (DiffuSpace; Hugging Face model_type clover_moe): Qwen3.6-35B-A3B tuned into a block-diffusion model.
// Its weights hold two pathways over one committed state (Qwen3.6's, so prefill, prefix reuse, checkpoints and the SSD
// cache are Qwen35's):
//  - the causal one, an autoregressive model as Qwen3.6 is (a row's logits predict the next token);
//  - the denoising one (encode_preview's passes), which reads the committed prefix and a whole block of rows at once,
//    mask tokens where nothing was chosen yet, and gives each row's own token (a row's logits predict the row itself).
//    It changes none of the committed state (its block's K / V rows go to the cache's positions after the prefix,
//    which the next causal pass rewrites) and differs from a causal pass in three places:
//     - Gated DeltaNet layers: the convolution also reads the next three rows of the block (right weights, bf16
//       [C, 1, 3]), and the recurrence is replaced by a softmax over the block's rows (l2-normalized q . k times a
//       per-head scale) and a history bucket (logit bias + c * log(T / 32)) whose value is the committed state's
//       readout decayed by the row's gate (src/kernels/clover.metal);
//     - attention: every row of the block sees the prefix and every row of the block;
//     - MoE: the rows route among a shared set of experts (the coreset: the experts holding 90% of the block's top-8
//       routing mass).
// Three ways to decode with them (NI_CLOVER_DECODE; decode_mode()):
//  - with Qwen3.6-35B-A3B's DFlash2 drafter (auto, when one is found: next to the pack, or an installed 35B-A3B pack's;
//    find_drafter()): the causal pathway is the 35B's shape, so the engine's DFlash2 / KFlash loop drafts and verifies
//    it as it does the 35B, and the reply is plain decoding's of that pathway (KFlash's guarantee). The fastest; the
//    generation controls below are not applied there (the request's sampling is, as for the 35B);
//  - self-speculative (auto without a drafter; DiffuSpace's SGLang implementation, sgl-project/sglang#46927): a cycle drafts the
//    W - 1 tokens after the pending one with one denoising pass over [pending, mask x (W - 1)], verifies them with one
//    causal pass over [pending, drafts] (Qwen35's 8-row verify, its rows on the tape), and keeps the drafts the verify
//    accepts and one more token from the first row it did not (encode_cycle). Acceptance (SGLang's rules): `threshold`
//    takes a draft whose verify probability is at least min(ratio 1.0, delta 0.6 * exp(-entropy)), `exact` only the
//    verify's own argmax (every token the causal pathway's argmax, the penalties counting the reply as it stood at the
//    cycle's start, as SGLang's; with the penalties off, greedy decoding's reply);
//  - block diffusion (NI_CLOVER_DECODE=diffusion; the Hugging Face implementation's LowConfidence): a block of 32
//    positions starts as mask tokens; each denoising pass gives every row its likeliest token and its probability, the
//    rows above the threshold (0.95; at least the most confident one) take theirs, until every row has one; the block
//    is then committed by a causal pass, as a prompt chunk is (encode_preview).
// The generation controls of the model's generation_config.json (presence and repetition penalties on the reply's
// tokens, biases toward ending the reply and the thinking) are applied to every pass's logits, greedy or not, as each
// implementation applies them.
#pragma once
#include "model/qwen35.h"

#include <string>
#include <vector>

namespace ni {

// generation_config.json's controls (the Hugging Face sampling_clover_moe.py's defaults where it names none)
struct CloverControls {
  float presence = 0.0f, frequency = 0.0f, repetition = 1.0f;
  float length_penalty = 0.0f;              // the end-of-reply ids' bias, ramped from length_start over length_window
  int length_start = 8192, length_window = 8192;
  float think_bias = 0.0f;                  // </think>'s, ramped likewise while no </think> was written
  int think_start = 4096, think_window = 4096;
  int think_close = -1;
};

// One request's reply so far, as the controls read it: its tokens by id and how many there are
struct CloverReply {
  std::vector<uint32_t> counts;
  int length = 0;
  void commit(const int* tok, int n) {
    for (int i = 0; i < n; ++i) ++counts[size_t(tok[i])];
    length += n;
  }
};

// One row of a pick (src/kernels/clover.metal's CloverRow): under the controls, the argmax and its probability, the
// draw (with a temperature; else the argmax) and its probability, the probability of the row's candidate (a verify row:
// the draft after it) and the entropy
struct CloverRow {
  int tok, smp;
  float conf, conf_smp, pc, ent;
  float pad0, pad1;
};

class Clover : public Qwen35 {
 public:
  explicit Clover(const std::string& model_dir, int prefill_chunk = 2048);
  // config.json's model_type is clover_moe
  static bool is_model(const std::string& model_dir);
  // NI_CLOVER_DECODE: "auto" (the default: the DFlash2 drafter when one is found, else self-speculative), "dflash",
  // "spec" or "diffusion"; fatal on anything else
  static std::string decode_mode();
  // A DFlash2 drafter for Clover's causal pathway (the 35B-A3B's): DFlash2::find's (next to the pack), else the drafter
  // of a pack in the model store whose config the drafter fits (the catalog's qwen3.6-35b-a3b packs carry one); ""
  static std::string find_drafter(const std::string& model_dir);

  // ---- self-speculative decoding (the default) ----
  bool self_spec() const { return spec_; }
  int draft_rows() const { return draft_; }  // W: the pending row and W - 1 drafts (NI_CLOVER_DRAFT, 2 to 8)
  // One cycle at P (tokens[P]: the pending token, not yet in the state; the rows a previous cycle kept are folded
  // first): the denoising pass over [tokens[P], mask x (W - 1)] writes its drafts to tokens[P + 1 .. P + W), then the
  // causal verify of tokens[P .. P + W) (its rows on the tape: commit_rows() keeps the accepted ones) and its pick:
  // rows()[r] verifies the draft tokens[P + r + 1] (pc) and gives the token after it (tok, or smp with a temperature).
  void encode_cycle(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                    const SamplingParams& sp, uint32_t step);
  // its two halves: the fold and the draft, then the verify and its pick (tools time them apart)
  void encode_draft(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                    const SamplingParams& sp, uint32_t step);
  void encode_check(Encoder& e, Seq& s, int P, int W, const CloverReply& reply, const std::vector<int>& stops,
                    const SamplingParams& sp, uint32_t step);
  // whether a verify row accepts its draft (the token after the row's): accept_draft with this model's rule
  bool accept(const CloverRow& r, int draft) const { return accept_draft(r, draft, exact_, accept_ratio_, accept_delta_); }
  // exact: the draft is the row's argmax; else (threshold) its probability is above zero and at least
  // min(ratio, delta * exp(-entropy))
  static bool accept_draft(const CloverRow& r, int draft, bool exact, float ratio, float delta);

  // ---- block diffusion (NI_CLOVER_DECODE=diffusion) ----
  int block_size() const { return block_; }    // rows per block (the config's 32, NI_CLOVER_BLOCK: a divisor of it)
  float threshold() const { return threshold_; }  // a row takes its token above this probability (NI_CLOVER_THRESHOLD)
  // A denoising pass over tokens[pos0 .. pos0 + T) (T <= 32, the block: mask_id where no token was chosen yet), the
  // committed state read, not changed. rows()[r]: row r's token and probability (tok / conf; with a temperature smp /
  // conf_smp: a draw from softmax(l / temperature), Gumbel-max, top-k / top-p not applied, the probability the
  // temperature-1 one). RNG step `step`.
  void encode_preview(Encoder& e, Seq& s, int pos0, int T, const CloverReply& reply, const std::vector<int>& stops,
                      const SamplingParams& sp, uint32_t step);

  const CloverRow* rows() { return rows_.as<CloverRow>(); }
  int mask_id() const { return mask_id_; }
  const CloverControls& controls() const { return ctl_; }

  std::string disk_format() const override;
  // the engine's DFlash2 loop decodes the causal pathway (auto and dflash); spec and diffusion keep Clover's own
  bool block_drafter_ok() const override { return decode_mode() == "auto" || decode_mode() == "dflash"; }
  int default_spec_depth() const override { return 0; }

 protected:
  // routing of a denoising pass: the block's coreset first (the prefill MoE paths; the 8-row one)
  void enc_topk_rows(Encoder& e, uint32_t E, uint32_t k, bool norm, int T) override;
  void enc_router_hook(Encoder& e, int R) override;

 private:
  // the denoising pass's trunk over tokens[pos0 .. pos0 + T) and its logits into lg_: on the prefill kernels (a
  // block of up to 32 rows), or on the 8-row verify's (a draft of up to 8)
  void enc_denoise(Encoder& e, Seq& s, int pos0, int T);
  void enc_denoise8(Encoder& e, Seq& s, int pos0, int R);
  // its token mixers from the projections' outputs: the GDN layers' convolution and softmax memory (qkv_, ab_ ->
  // gout_), the attention layers' prep and bidirectional attention (qg_, kr_, vr_ -> attn_out_)
  void enc_gdn_mix(Encoder& e, Seq& s, int li, const Layer& L, int T);
  void enc_attn_bidi(Encoder& e, Seq& s, int li, const Layer& L, int pos0, int T);
  void enc_coreset(Encoder& e, int T);  // rlog_'s T rows
  // the controls' state for a pick of T rows: the reply's counts, and per row the biases; row 0 predicts reply position
  // first (1-based). think_all: the thinking control raises every row (Hugging Face), else only the first row past
  // its start, and not before row think_min (SGLang: a draft's row 0 is the pending token); close_seen: a </think>
  // shows in the rows already (disables it)
  void set_controls(const CloverReply& reply, const std::vector<int>& stops, int T, int first, bool think_all,
                    int think_min, bool close_seen);
  // the pick of T logits rows (ld floats apart) into rows_; tok_out (from row skip on): the draws or the argmaxes;
  // cand: rows [0, ncand)'s candidates
  void enc_pick(Encoder& e, const Buffer& logits, uint32_t ld, int T, const SamplingParams& sp, uint32_t step,
                const Buffer& tok_out, size_t tok_off, uint32_t skip, bool sample_out, const Buffer& cand,
                size_t cand_off, uint32_t ncand);

  int block_ = 32, cfg_block_ = 32, mask_id_ = -1;
  float threshold_ = 0.95f;
  bool coreset_ = true;
  float coreset_top_p_ = 0.9f;
  bool spec_ = true;
  int draft_ = 8;
  bool exact_ = false;                       // NI_CLOVER_ACCEPT=exact
  float accept_ratio_ = 1.0f, accept_delta_ = 0.6f;
  CloverControls ctl_;
  bool preview_ = false;                     // a denoising pass is being encoded (enc_topk_rows)
  std::vector<const Tensor*> conv_r_;        // per layer (GDN layers): the right convolution weights
  Buffer sc_;                                // fp32 [layers][3][Hv]: logit scale, history bias, history c
  Buffer lg_, counts_, bias_ids_, bias_, ptok_, rows_;
  uint32_t nbias_ = 0;                       // ids with a bias in bias_ids_ (set_controls)
};

}  // namespace ni

#include "api/chat_completions.h"

#include <cmath>

namespace ni::api {

ojson chat_usage(const ChatResult& res) {
  ojson u{{"prompt_tokens", res.prompt_tokens},
          {"completion_tokens", res.completion_tokens},
          {"total_tokens", res.prompt_tokens + res.completion_tokens},
          {"prompt_tokens_details", {{"cached_tokens", res.cached_tokens}}}};
  if (res.loops > 0) u["kapitsa"] = kapitsa_usage(res);  // looped models: the loop count the request ran
  // the time the engine took to read the uncached part of the prompt (a client's prefill tok/s is
  // (prompt_tokens - cached_tokens) / prefill_ms; its own time to first token also holds the network and the queue).
  // Left out when the prompt had images (encoded before the clock starts) or the request gave up its turn to another
  // one while prefilling: the time is then not the time to read those tokens
  if (res.prefill_exact && res.prefill_ms > 0 && res.finish_reason != "cancelled" && res.finish_reason != "error")
    u["kapitsa"]["prefill_ms"] = std::round(res.prefill_ms * 10) / 10;
  // KFlash around the decode: the proposal source and the cycles the request ran
  if (!res.kflash_source.empty() && res.kflash_cycles > 0)
    u["kapitsa"]["kflash"] = {{"source", res.kflash_source}, {"cycles", res.kflash_cycles}};
  return u;
}

ojson chat_tool_calls(const std::vector<ToolCall>& tcs, size_t index0, bool with_index) {
  ojson a = ojson::array();
  for (size_t i = 0; i < tcs.size(); ++i) {
    ojson t{{"id", tcs[i].id}, {"type", "function"}, {"function", {{"name", tcs[i].name}, {"arguments", tcs[i].arguments}}}};
    if (with_index) t["index"] = index0 + i;
    a.push_back(t);
  }
  return a;
}

ojson chat_error(const std::string& message, const std::string& type, const std::string& code, const std::string& param) {
  return {{"error",
           {{"message", message}, {"type", type}, {"param", param.empty() ? ojson() : ojson(param)},
            {"code", code.empty() ? ojson() : ojson(code)}}}};
}

std::pair<int, ojson> chat_failure(const ChatResult& res) {
  if (res.busy) return {503, chat_error(res.error, "server_error")};
  if (res.engine_down) return {503, chat_error(res.error, "server_error", "engine_unavailable")};
  if (res.prompt_limit > 0)
    return {400, chat_error("This model's maximum context length is " + std::to_string(res.prompt_limit) +
                                " tokens. However, your messages resulted in " + std::to_string(res.prompt_tokens) +
                                " tokens. Please reduce the length of the messages.",
                            "invalid_request_error", "context_length_exceeded", "messages")};
  return {400, chat_error(res.error.empty() ? "the request failed" : res.error)};
}

int chat_max_tokens(const ojson& body) {
  for (const char* k : {"max_completion_tokens", "max_tokens"})
    if (body.contains(k) && !body[k].is_null()) return body[k].get<int>();
  return 16384;
}

std::shared_ptr<const Grammar> chat_grammar(const ojson& body, const ojson& tools) {
  auto bad = [](const std::string& m, const std::string& param) {
    throw ApiError(400, "invalid_request_error", m, "", param);
  };
  auto str = [](const ojson& j, const char* k) {
    return j.is_object() && j.contains(k) && j[k].is_string() ? j[k].get<std::string>() : std::string();
  };
  OutputSpec spec;
  if (body.contains("response_format") && !body["response_format"].is_null()) {
    const ojson& rf = body["response_format"];
    if (!rf.is_object()) bad("response_format must be an object", "response_format");
    const std::string type = str(rf, "type");
    if (type == "json_object") {
      spec.format = OutputSpec::Format::kJsonObject;
    } else if (type == "json_schema") {
      if (!rf.contains("json_schema") || !rf["json_schema"].is_object())
        bad("response_format.json_schema must be an object with the schema", "response_format.json_schema");
      schema_format(rf["json_schema"], spec, "response_format.json_schema");
    } else if (type != "text") {
      bad("response_format.type must be \"text\", \"json_object\" or \"json_schema\"", "response_format.type");
    }
  }
  if (body.contains("tool_choice") && !body["tool_choice"].is_null()) {
    const ojson& tc = body["tool_choice"];
    if (tc.is_string()) {
      const std::string v = tc.get<std::string>();
      if (v == "required") spec.tools = OutputSpec::Tools::kRequired;
      else if (v != "auto" && v != "none") bad("tool_choice must be \"none\", \"auto\", \"required\" or a function", "tool_choice");
    } else if (tc.is_object() && str(tc, "type") == "function" && tc.contains("function") &&
               !str(tc["function"], "name").empty()) {
      spec.tools = OutputSpec::Tools::kNamed;
      spec.tool = str(tc["function"], "name");
    } else {
      bad("tool_choice must be \"none\", \"auto\", \"required\" or {\"type\": \"function\", \"function\": {\"name\": ...}}",
          "tool_choice");
    }
  }
  if (body.contains("parallel_tool_calls") && body["parallel_tool_calls"].is_boolean())
    spec.parallel = body["parallel_tool_calls"].get<bool>();
  if (tools.is_array())
    for (const ojson& t : tools) {
      const ojson& f = t.is_object() && t.contains("function") ? t["function"] : t;
      if (f.is_object() && f.contains("strict") && f["strict"].is_boolean() && f["strict"].get<bool>() &&
          !str(f, "name").empty())
        spec.strict_tools.push_back(str(f, "name"));
    }
  return request_grammar(spec, tools);
}

std::string ChatCompletionsStream::chunk(const ojson& delta, const ojson& finish, const ojson* usage) const {
  ojson c{{"id", id_},
          {"object", "chat.completion.chunk"},
          {"created", created_},
          {"model", model_},
          {"choices", ojson::array({ojson{{"index", 0}, {"delta", delta}, {"finish_reason", finish}}})}};
  if (usage) c["usage"] = *usage;
  return "data: " + dump(c) + "\n\n";
}

std::string ChatCompletionsStream::begin(const ChatResult&) {
  return chunk(ojson{{"role", "assistant"}, {"content", ""}}, nullptr);
}

std::string ChatCompletionsStream::delta(const ChatDelta& d) {
  std::string s;
  if (!d.reasoning.empty()) s += chunk(ojson{{"reasoning_content", d.reasoning}}, nullptr);
  if (!d.content.empty()) s += chunk(ojson{{"content", d.content}}, nullptr);
  if (!d.tool_calls.empty()) {
    s += chunk(ojson{{"tool_calls", chat_tool_calls(d.tool_calls, tools_, true)}}, nullptr);
    tools_ += d.tool_calls.size();
  }
  return s;
}

std::string ChatCompletionsStream::keepalive() {
  // A chunk with an empty delta, not an SSE comment. The idle timers that drop a stream during a long prefill count
  // either the body's bytes (Node's fetch: undici's 300 s bodyTimeout, which Cline hit on local models; Bun's 300 s
  // socket timer; opencode's chunkTimeout: 300 s in 1.x, 900 s in 2.x's own OpenAI-compatible client) or its parsed
  // SSE events, which leave comments out (opencode 2's AI SDK path moves its deadline only on an event). A chunk
  // resets both kinds, a comment only the first, and parsers that read every line as "data: " JSON fail on a comment.
  // The delta carries nothing, not even empty content, so no client takes it for the start of text, wherever it lands
  // (a reply also goes quiet mid-reasoning while the parser holds back a tool call, or while it waits for memory).
  return chunk(ojson::object(), nullptr);
}

std::string ChatCompletionsStream::end(const ChatResult& res) {
  if (res.finish_reason == "error") return "data: " + dump(chat_failure(res).second) + "\n\ndata: [DONE]\n\n";
  const ojson u = chat_usage(res);
  return chunk(ojson::object(), res.finish_reason, &u) + "data: [DONE]\n\n";
}

}  // namespace ni::api

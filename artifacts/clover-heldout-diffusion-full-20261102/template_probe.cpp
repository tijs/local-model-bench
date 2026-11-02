// CPU-only metadata audit. No Engine or model/GPU object is constructed.
// Links the measured Kapitsa library's actual prompt renderer and tokenizer.
#include "engine/engine.h"
#include "engine/tool_args.h"
#include "tokenizer/tokenizer.h"
#include "minja/chat-template.hpp"
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
  if (argc != 3) return 2;
  const std::string model = argv[1];
  std::ifstream input(argv[2]);
  ni::ojson body;
  input >> body;
  ni::ChatRequest request;
  request.messages = body.at("messages");
  request.tools = body.at("tools");
  // The same OpenAI normalization as server/main.cpp::normalize_messages.
  for (auto& message : request.messages) {
    if (message.value("role", "") == "developer") message["role"] = "system";
    if (message.contains("tool_calls")) for (auto& call : message["tool_calls"]) {
      auto& function = call["function"];
      if (function["arguments"].is_string()) {
        std::string raw = function["arguments"].get<std::string>();
        function["arguments"] = ni::ojson::parse(raw);
        ni::tool_args::note_raw(function, raw);
      }
    }
    if (message.contains("content") && message["content"].is_null()) message["content"] = "";
  }
  const std::string source = ni::chat_template_source(model);
  ni::default_preserve_thinking(request, ni::preserve_thinking_template(source));
  minja::chat_template templ(source, "", "<|im_end|>");
  const std::string prompt = ni::render_chat(templ, request, true);
  ni::Tokenizer tokenizer;
  tokenizer.load(model + "/tokenizer.json");
  std::cout << ni::ojson{{"prompt", prompt}, {"tokens", tokenizer.encode(prompt)}}.dump() << '\n';
}

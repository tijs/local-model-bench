"""CPU-only comparison of saved request prefixes with publisher template/tokenizer."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runner"))
from run_automation_suite import TOOLS as PYTHON_TOOLS
from standin_domain import TOOLS as HOUSE_TOOLS

OUT = Path(__file__).resolve().parent
MODEL = Path(
    "/Users/tijs/.local/share/local-model-bench/mei-models/Clover-35B-A3B-Preview-MLX-4bit"
)
BINARY = Path(
    "/Users/tijs/.local/share/local-model-bench/kapitsa-template-probe-211b2b4"
)
tokenizer = AutoTokenizer.from_pretrained(
    MODEL, trust_remote_code=False, local_files_only=True, fix_mistral_regex=True
)
report = {
    "scope": "CPU renderer/tokenizer comparison of saved request prefixes reconstructed from the measured runner, resetting HTTP history on simulated reconnects. Not numerical decoder/weight parity.",
    "probe_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
    "requests": [],
}
for directory, tools in (
    (ROOT / "results/standin/runs/20261102T002104Z-f4119f15", HOUSE_TOOLS),
    (ROOT / "results/automation/runs/20261102T003215Z-e3f5500d", PYTHON_TOOLS),
):
    for path in sorted(directory.glob("*-trial1.json")):
        trace = json.loads(path.read_text())
        indices = [
            i for i, m in enumerate(trace["messages"]) if m["role"] == "assistant"
        ]
        assert len(indices) == len(trace["responses"]), path
        for turn, index in enumerate(indices):
            # The trace is append-only across simulated reconnects, while the
            # actual HTTP history restarts at the new system message (run_task).
            system_indices = [
                i
                for i, m in enumerate(trace["messages"][:index])
                if m["role"] == "system"
            ]
            start = system_indices[-1] if system_indices else 0
            messages = trace["messages"][start:index]
            request = {"messages": messages, "tools": tools}
            request_path = OUT / "template-request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False))
            result = subprocess.run(
                [str(BINARY), str(MODEL), str(request_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            actual = json.loads(result.stdout)
            # Same OpenAI argument normalization as native HTTP entry point.
            for m in messages:
                if m.get("content") is None:
                    m["content"] = ""
                for call in m.get("tool_calls", []):
                    fn = call["function"]
                    if isinstance(fn["arguments"], str):
                        fn["arguments"] = json.loads(fn["arguments"])
            later = []
            for index, message in enumerate(messages):
                if index and message["role"] == "system":
                    marker = f"\x02kapitsa-system-turn-{len(later)}\x02"
                    later.append((marker, message["content"]))
                    messages[index] = {
                        "role": "user",
                        "content": "<tool_response>" + marker + "</tool_response>",
                    }
            expected = tokenizer.apply_chat_template(
                messages,
                tools=tools,
                tokenize=False,
                add_generation_prompt=True,
                preserve_thinking=True,
            )
            for marker, content in later:
                expected = expected.replace(
                    "<|im_start|>user\n<tool_response>"
                    + marker
                    + "</tool_response><|im_end|>\n",
                    "<|im_start|>system\n" + content + "<|im_end|>\n",
                )
            expected_tokens = tokenizer.encode(expected, add_special_tokens=False)
            saved_count = trace["responses"][turn]["usage"]["prompt_tokens"]
            item = {
                "task": path.stem,
                "turn": turn + 1,
                "history_restart": bool(start),
                "late_system_adaptation": bool(later),
                "prompt_equal": actual["prompt"] == expected,
                "tokens_equal": actual["tokens"] == expected_tokens,
                "tokens": len(actual["tokens"]),
                "saved_prompt_tokens": saved_count,
                "saved_count_equal": len(actual["tokens"]) == saved_count,
            }
            if not item["prompt_equal"]:
                mismatch = next(
                    (
                        i
                        for i, (a, b) in enumerate(zip(actual["prompt"], expected))
                        if a != b
                    ),
                    min(len(actual["prompt"]), len(expected)),
                )
                item["difference"] = {
                    "offset": mismatch,
                    "native": actual["prompt"][max(0, mismatch - 100) : mismatch + 250],
                    "publisher": expected[max(0, mismatch - 100) : mismatch + 250],
                }
            report["requests"].append(item)
request_path.unlink()
(OUT / "template-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {
            "requests": len(report["requests"]),
            "prompt_matches": sum(x["prompt_equal"] for x in report["requests"]),
            "token_matches": sum(x["tokens_equal"] for x in report["requests"]),
            "saved_count_matches": sum(
                x["saved_count_equal"] for x in report["requests"]
            ),
        },
        indent=2,
    )
)

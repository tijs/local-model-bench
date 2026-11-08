"""Require the same prompt, teacher token and KV state geometry in both traces."""

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def identity(path, expected_tokens):
    record = json.loads(path.read_bytes())
    trace = Path(record["trace"])
    has_contents = (
        any(trace.iterdir())
        if trace.is_dir()
        else trace.is_file() and trace.stat().st_size > 0
    )
    if (
        trace.suffix != ".gputrace"
        or path.resolve() != Path(f"{trace}.json").resolve()
        or not has_contents
    ):
        raise ValueError(f"missing or mismatched Metal trace: {path}")
    if record["prompt_tokens"] != expected_tokens:
        raise ValueError(f"wrong prompt size: {path}")
    if not re.fullmatch(r"[0-9a-f]{64}", record["token_ids_sha256"]):
        raise ValueError(f"invalid token identity: {path}")
    for key in ("teacher_token_id", "decoded_token_id"):
        token = record[key]
        if type(token) is not int or token < 0:
            raise ValueError(f"invalid {key}: {path}")
    cache = record["prefill_cache"]
    if not cache or not any(layer["state"] for layer in cache):
        raise ValueError(f"capture lacks prefill cache evidence: {path}")
    return {key: record[key] for key in record if key != "trace"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", choices=("short", "loaded"))
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    if args.control.resolve() == args.candidate.resolve():
        raise ValueError("compare two distinct trace receipts")
    plan = json.loads((HERE / "qwen-decode-trace-plan.json").read_bytes())
    tokens = plan["expected_templated_tokens"][args.context]
    control, candidate = (
        identity(path, tokens) for path in (args.control, args.candidate)
    )
    if control != candidate:
        raise ValueError(
            "prompt, teacher token or cache geometry differs across traces"
        )
    print(
        f"{args.context}: matching {tokens}-token trace fixture; inspect dispatch next."
    )


if __name__ == "__main__":
    main()

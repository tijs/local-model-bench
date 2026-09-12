#!/usr/bin/env python3
"""Per-request prefill/generate for llama.cpp, comparable to Mei's --request-log.

llama-server has no --request-log equivalent, which left every "parity with
llama.cpp" claim in this repo resting on an inherited number rather than a
like-for-like measurement. It does, however, log per-request timings:

    slot print_timing: ... prompt eval time = X ms / N tokens
    slot print_timing: ...        eval time = Y ms / M tokens

which is the same shape as Mei's prefill_ms / generate_ms. Parsing them makes
the two engines directly comparable per request.

usage: parse_llama_timings.py <llama-server-log>
"""
import re
import sys

path = sys.argv[1]
prefill, generate, ptok, etok = [], [], [], []
for line in open(path):
    m = re.search(r"prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens", line)
    if m:
        prefill.append(float(m.group(1)) / 1000)
        ptok.append(int(m.group(2)))
    m = re.search(r"\|\s+eval time =\s*([\d.]+) ms /\s*(\d+) tokens", line)
    if m:
        generate.append(float(m.group(1)) / 1000)
        etok.append(int(m.group(2)))

n = len(prefill)
if not n:
    raise SystemExit(f"no per-request timings found in {path} — is it a "
                     f"llama-server log with slot print_timing lines?")

big = [p for p, t in zip(prefill, ptok) if t > 15000]
print(f"requests: {n}")
print(f"  prefill   total {sum(prefill)/60:6.2f} min   per request {sum(prefill)/n:5.2f} s")
print(f"  generate  total {sum(generate)/60:6.2f} min   per request "
      f"{sum(generate)/max(1, len(generate)):5.2f} s")
print(f"  prompt tokens {sum(ptok):,}   output tokens {sum(etok):,}")
print(f"  decode rate {sum(etok)/max(1e-9, sum(generate)):.1f} tok/s")
print(f"  cold prefills >15k tokens: {len(big)} ({sum(big)/60:.2f} min)")
print()
print("  Measured 2026-09-12 on the Ornith GGUF Q4_K_M lane, 262 requests:")
print("    llama.cpp       prefill 2.62 s/req, >15k prefills 2, decode 36.3 tok/s")
print("    Mei anchors off prefill 4.64 s/turn, >15k prefills 8, decode 57.4 tok/s")
print("    Mei anchors on  prefill 2.82 s/turn, >15k prefills 1, decode 57.4 tok/s")

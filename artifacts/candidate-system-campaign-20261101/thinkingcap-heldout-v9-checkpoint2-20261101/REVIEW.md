# ThinkingCap checkpoint-bounded v9 result

Household `20261101T202525Z-33effef7`: **11/12**.
Python `20261101T202927Z-699cdc5e`: **3/3**.
Released method benchmark-v9 (`0834ad036f3c`), config
`configs/candidates-20261101/thinkingcap-checkpoint2.yaml`.
Owned supervisor completed normally in 527.273 seconds (8m 47s), excluding the
30-second baseline and including startup/native admission. One trial per task.

The only failure is `resume-step`: the final answer was “The next step is to put
in your water bottle.” This is the right step, but omits the record ID required
by the system's factual-answer citation contract. The tool read the right `bag`
record. This is not a wrong-step or API transformation failure. No unsafe
attempt, invalid operation or critical boundary failure was recorded.

All 12 grades reproduced from preserved state. Model API tool names/arguments
matched the domain journals. Every submitted script independently passed all
four visible/unseen fixture variants. `audit.py` reproduces these sidecar checks
without modifying raw rows. See `audit.json` for detailed results.

All 104 pressure samples were normal, with no swap growth. Minimum kernel free
percentage was 23%, retained as telemetry. All 184 checkpoint-creation log entries
respected the two-snapshot cap. This profile completed where the original default
32-snapshot profile stopped, supporting the bounded cache plan. The original
interruption also differs in stochastic trajectory and validator version; this
is not an isolated causal measurement of snapshot memory alone.

The model post-run SHA matched the publisher pin. Server log is preserved, owned
server stopped and port 8017 is free. No persistent disk KV cache was configured.
Weights, sampler, 65,536 context, f16 K/V and GPU placement are unchanged from the
original; the retained-checkpoint profile differs explicitly.

Keep ThinkingCap provisional pending independent repeats and matched v9 reference
runs. This is a GGUF/llama.cpp profile, not Mei/MLX, vision quality, full-context
capacity or real Peixinho application acceptance.

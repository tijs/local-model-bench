# local-model-bench benchmark-v8.5

Adds the official ThinkingCap Gemma4 26B/A4B Q4_K_M GGUF profile for the ongoing
four-candidate campaign. Existing measurement helpers, task/validator contracts,
budgets, supervisor and prior configs remain byte-identical to v8.4. No scores
or historical source identities are rewritten.

The17,010,980,160byte file atbb52b322579d218a9931261d6c9cd7403d80eb96 matched
the publisher SHA256. Pinned llama.cpp1268edac source, binary and shared libraries
are verified; this establishes provenance/static architecture support, not native
acceptance. Text only, projector absent, thinking explicitly on, nativeT1/p.95/k64.
Min_p.05/repetition1/presence0/frequency0 are explicit frozen runtime defaults
corresponding to the publisher GGUF recipe, not an unrelated model's settings.

The65K profile uses f16K/V, batch512/ubatch128, flash attention and the pinned
optimized SWA cache default. Metadata has5 full layers (2KVheads/head512) and25
SWA layers (8KVheads/head256,1024window); padded SWA capacity1280. Fixed cache
estimate1,604,321,280bytes; total capacity plan25,057,752,384bytes including model,
workspace and host allowances. Real allocation logs and unchanged actual pressure,
swap, disk and deadline guards determine whether the run can proceed. Kernel
free percentage is telemetry only. Native tools and full score remain pending.

Groot's first complete audited v8.4-equivalent result is11/12 household+3/3 Python
in578.527s including build/startup, allnormal/no swap growth. The only failure
was a denied foreign-private read; no private content exposure or critical
boundary failure. All grades, API journals, script replays and posthashes matched.
Groot is provisional pending independent repeats. See the candidate comparison
and campaign artifacts; synthetic results are not actual Peixinho acceptance.

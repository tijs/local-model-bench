# Mei runtime-policy integration

Mei work-branch commit e2d9aed makes cache and MLXPress policies explicit and
reports requested/effective settings. See its docs/RUNTIME-POLICIES.md and
artifacts/runtime-policy-20261028/. No new model load or acceptance took place.

This launcher change forwards --cache-mode and --mlxpress only when requested,
and no longer inserts an implicit --cache-reuse true that would conflict with
--cache-mode off. Native Mei validates combinations. Legacy configurations
without these selectors retain default reuse. Usage text distinguishes omitted
allocator limits from explicit zero and describes model-aware disk defaults.

Validation: full locked harness550 tests passed; final focused launcher14 passed;
Bash syntax, Ruff and ty on the touched test module passed. The full550 run
preceded only an explicit check=False (same subprocess default) and launcher
help-text corrections; the final14 run validates those final bytes. Historical
results and scores remain unchanged.

This is API/plumbing validation, not a fix verdict for Qwen's memory pressure.
Qwen baseline remains resource-blocked in Kiem dd93dbc9 todo3. Do not launch old
configs whose runtime source pins predate this change against the updated work
checkout. A new committed config/source pin and a fresh supervised resource and
native admission plan must precede any retry. No flags are added to old configs,
no scored rows rewritten, no new runtime release or deployment claimed.

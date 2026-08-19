# hermes_ops fixture provenance

This suite tests tool-use behavior under a realistic large system prompt +
full tool manifest, not coding ability. Everything here is either real-but-
generic content or clearly-labeled synthetic content — nothing here is
derived from Tijs's actual personal memory, user profile, or project
context, even though this fixture is designed to be roughly the same *size*
as what Hermes really sends.

- **`tools.json`** — real, verbatim: the actual 41 tool schemas from a live
  Hermes session (`~/.hermes/sessions/request_dump_*.json`, captured
  2026-08-19). These are pure function definitions (name/description/
  params) — inherently generic, no personal data.
- **`system_prompt.txt`**, three parts concatenated:
  1. Real, verbatim: hermes-agent's own static prompt-engineering string
     constants (`MEMORY_GUIDANCE`, `KANBAN_GUIDANCE`,
     `TOOL_USE_ENFORCEMENT_GUIDANCE`, etc.), extracted directly from
     `~/.hermes/hermes-agent/agent/prompt_builder.py` — these are
     hermes-agent's own shipped behavior instructions, not personal data.
  2. Real, verbatim: a skills index built from the actual installed skill
     categories/names and their `DESCRIPTION.md` files under
     `~/.hermes/skills/` — generic capability descriptions.
  3. Entirely synthetic memory/user-profile/project-context sections,
     written fresh (not derived from or redacted from the real
     `~/.hermes/memories/MEMORY.md`) to be structurally representative of
     what that content looks like, with every fact fictional.

**Size**: ~106K chars combined (~26-27K tokens), vs. the real live
measurement of ~29K tokens (`hermes prompt-size --json`) — close enough for
testing whether a model can function under this much fixed context, which is
the actual point; not chased to exact byte parity since the specific content
isn't graded, only used as load.

Regenerate by re-running the extraction steps in the local-model-bench
project history (kiem note `proj/local_model_bench`) if Hermes's real
manifest changes significantly (e.g. new capabilities installed).

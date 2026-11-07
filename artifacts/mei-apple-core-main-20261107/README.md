# Mei qualification with Apple MLX core main

Compare the Homebrew Mei 0.11.0 artifact with the candidate that merges Apple
MLX core `fc344c986c4169d99f76b5d95ae6b4a58a359a63`. This campaign adds no
scored task rows and does not change the active model roster.

- Native admission uses each candidate's exact staged Qwen, Ornith, Groot or
  Gemma RAM13GB checkpoint and the released profile's disk cache settings. It
  checks plain output, native tools, replay, cache reuse and the 65,536-token
  limit before timing can start.
- Timing uses four fresh processes per model in stable/candidate/candidate/stable
  order. Both versions disable cache reuse and use the same tokenizer-derived
  short and approximately 30,000-token chat inputs. The tokenizer and chat
  template determine each model's actual token counts. Each process has five
  measured repeats per input, with separate cold and warm-up observations.
- Compare first generated token, first visible text when present, decode rate,
  and total request time separately. The runner checks greedy output and usage
  against the first control; a difference halts the campaign for review.

Use the same benchmark host, exclusive runtime, capacity and supervision
rules. The wrapper reads the committed declaration, verifies model bytes before
and after each run, preserves logs and removes only that run's owned KV after
the child exits. A failed or declined cell stays in its original directory.

The checked-out candidate, SwiftPM lock, executable and colocated Metal library
must match the committed profiles. `prepare.py` freezes profiles once from
those files; `run_campaign.py native` and `run_campaign.py timing` run separate
phases through the locked `uv` environment.

# Mei qualification with Apple MLX core main

Compare the Homebrew Mei 0.11.0 artifact with the candidate that merges Apple
MLX core `fc344c986c4169d99f76b5d95ae6b4a58a359a63`. This campaign adds no
scored task rows and does not change the active model roster.

- [Native qualification](NATIVE.md): all four model profiles passed.
- [Four-model timing report](COMPARISON.md): all 16 processes passed their
  audits. Qwen and Ornith slowed on short requests; Ornith finished long
  requests sooner. Groot and Gemma's total times changed by less than 1%.
- [Completed Qwen timing](COMPARISON-QWEN.md): short-prompt decode slowed in
  both run orders; long-prompt total time was essentially unchanged.
- [Completed Ornith timing](COMPARISON-ORNITH.md): short-prompt decode slowed
  in both orders, while the long prompt finished about five seconds sooner.
- [Completed Groot timing](COMPARISON-GROOT.md): decode and total request time
  changed by about 1% or less in either context.
- [Release graph validation](RELEASE-BUILD-VALIDATION.md): the tested
  Apple-main binary includes debug-only work in its Metal evaluator. The
  original timings apply to that binary; a separate comparison isolates it.
- [Upstream changes and follow-up experiments](PERFORMANCE-ROUTES.md): which
  model paths can use each optimization, results from Gemma's window screen,
  and how to isolate the Qwen regression.

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

`uv run --locked python artifacts/mei-apple-core-main-20261107/summarize.py --model qwen --write`
can write a report as soon as that model's four runs have passed all
audits. This writes separate `COMPARISON-QWEN.md` and `comparison-qwen.json`
files. Omit `--model` to require and report the full campaign.

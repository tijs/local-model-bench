<picture>
  <source media="(max-width: 600px)" srcset="docs/assets/header-narrow.svg">
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/header-dark.svg">
  <img alt="Kapitsa writes 346 tok/s on Qwen3.6 35B-A3B on an M5 Max, against 138-281 for MLX, Ollama, llama.cpp, oMLX, mlx-serve and Splash." src="docs/assets/header-light.svg">
</picture>

Kapitsa is an inference engine for Apple silicon that runs Qwen, Nemotron and Recursive's Flint models locally, built for coding agents. It starts opencode, Claude Code, Codex or pi on a local model, and serves OpenAI and Anthropic APIs.

[Quickstart](#quickstart) · [Benchmarks](#benchmarks) · [Features](#features) · [CLI](#cli) · [Models](#supported-models) · [How KFlash works](docs/kflash.md) · [Docs](docs/usage.md)

## Quickstart

**Requirements:** a Mac with Apple silicon (M1 or newer) and macOS 14 Sonoma or later.

**Limits:** Apple silicon only: no Linux or Windows. Flint, the four text-only Nemotrons and the 35B's `16gb` build read text only, not images ([which models read images](docs/usage.md#images)).

```bash
brew install nace-ai/tap/kapitsa
# or: curl -fsSL https://raw.githubusercontent.com/nace-ai/kapitsa/main/install.sh | bash
```

```bash
kapitsa opencode --model 35b    # also: claude, codex, pi
```

<sub>On a 16-24 GB Mac use `--model 9b`, or `4b` for the quickest replies.</sub>

## Benchmarks

Kapitsa has the fastest decode in 33 of the 38 model and Mac pairs measured against nine engines ([how each number was measured](docs/benchmarks.md#how-the-readme-poster-was-measured)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/benchmarks-dark.webp">
  <img alt="Poster of prefill / decode speed for Kapitsa and nine other engines on a MacBook Pro M5 Max, M5 Pro, M4 Pro, M3 Pro and M1 Pro; the numbers are in the poster and in the Models section's tables" src="docs/assets/benchmarks-light.webp">
</picture>

<sub>Each cell reads prefill / decode in tokens per second, from a 4K-token prompt and a 512-token answer at T 0.6 (Flint at its card's T 1.0). The M5 Pro's Flash-Next 180B Q2 row is a 256-token answer at T 0 on that run's own 4,074-token prompt, and its Kapitsa column is Kapitsa with KFlash against plain Splash 1.5.0: a tie, the two engines' ranges overlap ([record](bench/results/2026-10-30-m5-pro-flash-next-kflash/README.md)). Footnotes, run dates and flags: [docs/benchmarks.md](docs/benchmarks.md#how-the-readme-poster-was-measured).</sub>

The poster's numbers, and the models it leaves out, are in each Mac's table under [Models](#models). Every recorded run, with its Mac, model, prefill and decode speed, is in the [benchmark table](bench/README.md). Measure your Mac: `kapitsa bench --submit` adds it to the [community results](bench/community/RESULTS.md). Another engine faster on your Mac? `kapitsa bench compare` ranks every engine you have installed, and `--report` writes a Markdown report.

## 🔥 What's new

- [2026/10] 🍀 **DiffuSpace's Clover-35B-A3B, a block-diffusion MoE, writes at 319 tok/s on an M5 Max**: `kapitsa serve --model clover` ([numbers](docs/benchmarks.md#diffuspace-clover-35b-a3b-m5-max-2026-10-28), [how](docs/usage.md#other-models)).
- [2026/10] 🗄️ **A 180B model runs on a 48 GB Mac**: Qwen3.8-Flash-Next's Q2_0 experts stream from the SSD ([numbers](bench/results/2026-10-28-m5-pro-flash-next-engines/README.md)).
- [2026/10] 🏆 **The fastest decode in 32 of the 38 model and Mac pairs** measured against nine engines ([poster](#benchmarks)).

## Features

- **346 tok/s on Qwen3.6 35B-A3B (M5 Max), the fastest decode in 33 of 38 model and Mac pairs.** KFlash, tree speculative decoding: one verify pass checks a tree of the drafter's guesses, with a DFlash2, DFlash, MTP, DSpark or LiLiCorr drafter behind every model that ships one ([how it works](docs/kflash.md)).
- **A 180B model on a 48 GB Mac, at 56 tok/s (M5 Pro).** Its routed experts stream from the SSD, as many as the budget holds.
- **A 16K follow-up after a restart starts in 0.16 s instead of 17 s.** Conversations stay on the SSD (`--disk-cache`).
- **Prefill on the GPU and the Neural Engine together.** Prefill hands part of its work to the Neural Engine, which the GPU would otherwise wait on.
- **Your tools, unchanged.** `/v1/chat/completions`, `/v1/messages` and `/v1/responses` with streaming, tool calls and JSON-schema output, and a chat page, all on `http://127.0.0.1:8000`.
- **An agent in one command.** `kapitsa claude`, `kapitsa codex`, `kapitsa opencode` and `kapitsa pi` start on the local model.
- **One calibrated probability per option.** `kapitsa-systemone` serves Drex 2.0 and Drex Max v1 that way: a state and its questions in, a probability per option out (`POST /v1/systemone`) ([decisions](docs/systemone.md), [Drex Max v1](docs/drex-max.md)).
- **Several Macs, one model.** A Mac that cannot hold a model sends its requests to one that can, and `--split` spreads one model's layers across a network ([several Macs](docs/usage.md#several-macs)).
- **Images.** Screenshots and photos in the chat page and the APIs, on every catalog model but the four text-only Nemotrons, Flint, Clover and the 35B's `16gb`.

### Drex Max v1

Drex Max v1 runs on Kapitsa v0.2.25 or later, through `kapitsa-systemone` (the Q8_0 GGUF imported to Kapitsa's affine 8-bit layout; an affine Q4 checkpoint is in [its guide](docs/drex-max.md#run-the-affine-q4-checkpoint)):

```bash
brew install nace-ai/tap/kapitsa
kapitsa import /path/to/drex-max-v1-Q8_0.gguf --name drex-max-v1
kapitsa-drex-pointer /path/to/drex-max-v1-Q8_0.gguf ~/.cache/kapitsa/models/drex-max-v1/pointer.bin
kapitsa-systemone --model ~/.cache/kapitsa/models/drex-max-v1 --port 8000 --context 2048
```

[Drex Max v1 on Kapitsa](docs/drex-max.md) has the request, the memory a longer context needs and the encoding.

## CLI

```bash
kapitsa serve                   # chat + OpenAI/Anthropic APIs at http://127.0.0.1:8000
kapitsa claude                  # Claude Code on Kapitsa
kapitsa doctor                  # this Mac's GPU and memory, and which models fit it
kapitsa cluster                 # the Macs on this network that run Kapitsa, and their models
kapitsa bench                   # benchmark this Mac, share it with the community
kapitsa bench compare           # the same test against the other engines installed here
kapitsa pull 27b                # download a model without starting it
kapitsa list                    # downloaded models and their size
kapitsa rm 27b                  # delete a downloaded model
kapitsa import model.gguf       # use a Qwen or Flint GGUF from LM Studio, Ollama or llama.cpp
kapitsa update                  # update now (it also updates itself)
```

<sub>`--model` picks the model and its precision (`35b:6bit`). `kapitsa <command> --help` has the options.
A Mac that cannot hold a model whole uses another Mac on the network that runs it, and two Macs that would each stream
Flash-Next pair to hold it in memory between them ([Several Macs](docs/usage.md#several-macs)); `--private` keeps a
server to its own Mac. [Usage guide](docs/usage.md)</sub>

## In-process SDK

The opt-in [C ABI SDK](sdk/README.md) lets desktop clients reuse a loaded model,
stream and cancel requests. See its build instructions and host-process lifetime limitations.
The [Node.js / TypeScript binding](sdk/node/README.md) provides async calls over the same C ABI.

**Roadmap** — what is open in the [tracker](https://github.com/nace-ai/kapitsa/issues): KV cache quantization ([#547](https://github.com/nace-ai/kapitsa/issues/547)).

## Supported models

The most precise variant of each catalog model that runs on a Mac of each size. Sizes, download times and draft models: [Models and downloads](docs/usage.md#models-and-downloads); `kapitsa doctor` prints the same for this Mac.

| Model | 16 GB | 24 GB | 32 GB | 36 GB | 48 GB | 64 GB | 128 GB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Qwen3.5-4B** · `4b` | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 |
| **Qwen3.5-9B** · `9b` | 4-bit | 4-bit | 4-bit | 4-bit | 4-bit | 4-bit | 4-bit |
| **Qwen3.8-27B** · `27b` | — | 4-bit† | 5-bit | 5-bit | 8-bit | 8-bit | BF16 |
| **Qwen3.6-35B-A3B** · `35b` | 2-bit† | 2-bit | 4-bit | 4-bit | 6-bit | 8-bit | BF16 |
| **Qwen3.8-Flash-Next 180B-A7B** · `flash-next` | — | — | — | — | 2-bit + SSD | 2-bit | 4-bit |
| **Nemotron 3.5 Lightning 30B-A3B** · `lightning` | — | NVFP4† | NVFP4 | NVFP4 | NVFP4 | NVFP4 | NVFP4 |
| **Nemotron 3.5 Bolt 74B-A9B** · `bolt` | — | — | 2-bit† | 2-bit | 2-bit | 2-bit | 2-bit |
| **Nemotron 3.5 Super-VL 120B-A12B** · `super-vl` | — | — | — | — | — | — | NVFP4 |
| **Recursive Flint 40B-A2.5B** · `flint` | 2-bit† | 2-bit | 2-bit | 4-bit | 4-bit | 4-bit | 4-bit |
| **Clover-35B-A3B-Preview** · `clover` | — | — | 4-bit | 4-bit | 4-bit | 4-bit | 4-bit |
| **Nemotron Dory1.0 4B** · `dory` | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 |
| **Nemotron 3 Nano 4B** · `nano-4b` | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 | BF16 |
| **Nemotron Nano 9B v2** · `nano-9b` | NVFP4 | NVFP4 | NVFP4 | NVFP4 | NVFP4 | NVFP4 | NVFP4 |
| **Drex 2.0** · `kapitsa-systemone` | — | — | — | Q4† | Q4 | Q8 | Q8 |

<sub>Cells name the catalog's variant labels — `4bit`, `5bit`, `6bit`, `8bit`, `bf16` and `nvfp4`, with `16gb`, `24gb` and Flash-Next's `64gb` shown as 2-bit — that `kapitsa serve <name>:<variant>` takes, the most precise one that starts on that Mac at the bottom of its working-set range: weights, drafter, activations and 8K tokens of context. † needs the top of the range, about 80% of the RAM against 69% at the bottom; — nothing starts. Flash-Next's 48 GB cell is its Q2_0 pack with the experts the budget does not hold streamed from the SSD, and Drex 2.0's Q4 and Q8 are its release builds, served by `kapitsa-systemone` ([decisions](docs/systemone.md)). The 24, 32 and 64 GB columns are `kapitsa doctor`'s plan, and so is any cell in the 16, 36, 48 and 128 GB ones that differs from the default variant those [Macs](#models) ran, usually 4-bit; `kapitsa doctor` prints the plan for this Mac.</sub>

## Models

The catalog models measured on each Mac, against the engines that run them: one collapsed section per Mac, with a table for each model family. Decode is a 512-token coding answer at T 0.6 (Flint at its card's T 1.0), prefill a 4K-token prompt. Under each model's name are the weights Kapitsa ran; the other engines' weights and how each number was measured are in [docs/benchmarks.md](docs/benchmarks.md#the-readmes-tables). Flint's speed from 1K to 128K tokens of prompt on the M5 Pro, against llama.cpp: [bench/results/2026-10-24-flint-m5pro-context](bench/results/2026-10-24-flint-m5pro-context/README.md).

<sub>Each cell: prefill / decode, tokens/s (a lone number is decode: no prefill run) · 🟩 fastest decode · ≈ a decode tie with Kapitsa · small type: the decoding method (none: no speculative decoding) · × can't run on that Mac · — not measured</sub>

<details>
<summary><b>MacBook Pro (16-inch, 2026) · M5 Max · 128 GB</b> · 9 models</summary>

**Qwen and Nemotron**

| Model | <mark>**Kapitsa**</mark> | <sub>mlx‑serve<br>26.10.2 / 26.10.3</sub> | <sub>oMLX<br>0.7.1rc1 / 0.7.3.dev2</sub> | <sub>Splash<br>1.4.0</sub> | <sub>Ollama<br>0.40.5 / 0.40.11</sub> | <sub>MTPLX<br>2.12.2</sub> | <sub>MLX<br>mlx-vlm 0.7.8 / 0.7.10</sub> | <sub>llama.cpp<br>b11669 / b11871</sub> | <sub>LM&nbsp;Studio<br>MLX runtime 1.13.1 (nax), llama.cpp runtime 2.60.0</sub> |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Qwen3.8-27B** · `27b`<br><sub>dense · 4-bit, 20.2 GB</sub> | 🟩 904 / **143**<br><sub>KFlash</sub> | 792 / 128<br><sub>DFlash2 · 26.10.3</sub> | 902 / 92<br><sub>DFlash2 · 0.7.3.dev2</sub> | 1039 / 116<br><sub>DFlash2</sub> | 844 / 71<br><sub>MTP · 0.40.11, MLX runner</sub> | 848 / 73<br><sub>MTP</sub> | 856 / 56<br><sub>MTP · mlx-vlm 0.7.10</sub> | 578 / 48<br><sub>MTP · b11871</sub> | 918 / 33<br><sub>MLX runtime 1.13.1 (nax)</sub> |
| **Qwen3.6-35B-A3B** · `35b`<br><sub>MoE, 3B active · 4-bit, 22.1 GB</sub> | 🟩 6036 / **346**<br><sub>KFlash</sub> | 4622 / 235<br><sub>MTP · 26.10.3</sub> | 3005 / 189<br><sub>DFlash2 · 0.7.3.dev2</sub> | 6386 / 281<br><sub>DFlash2</sub> | 3077 / 162<br><sub>MTP · 0.40.11, MLX runner</sub> | 4291 / 130<br><sub>MTP</sub> | 4439 / 138<br><sub>DFlash2 · mlx-vlm 0.7.10</sub> | 2881 / 171<br><sub>MTP · b11669</sub> | 4672 / 136<br><sub>MLX runtime 1.13.1 (nax)</sub> |
| **Qwen3.8-Flash-Next 180B-A7B** · `flash-next`<br><sub>MoE, 7B active · 4-bit, 105.9 GB</sub> | 🟩 1701 / **108**<br><sub>KFlash</sub> | 🟩 1720 / **108**<br><sub>26.10.2</sub> | 1260 / 107<br><sub>MTP · 0.7.1rc1</sub> | × | 60<br><sub>0.40.6</sub> | 1263 / 88<br><sub>MTP</sub> | 1030 / 77<br><sub>MTP · mlx-vlm 0.7.8</sub> | 842 / 96<br><sub>b11669</sub> | × |
| **Nemotron Dory1.0 4B** · `dory`<br><sub>looped dense · NVFP4, 3.2 GB</sub> | 🟩 **122**<br><sub>KFlash</sub> | × | × | × | × | × | 76<br><sub>mlx-vlm 0.7.8</sub> | 9<br><sub>b11669</sub> | × |
| **Nemotron 3.5 Lightning 30B-A3B** · `lightning`<br><sub>hybrid MoE, 3B active · NVFP4, 22.9 GB</sub> | 🟩 **287**<br><sub>KFlash</sub> | 190<br><sub>26.10.2</sub> | 190<br><sub>0.7.1rc1</sub> | × | 153<br><sub>0.40.5</sub> | 131 | 139<br><sub>mlx-vlm 0.7.8</sub> | 159<br><sub>b11669</sub> | 110<br><sub>llama.cpp runtime 2.60.0</sub> |
| **Nemotron 3.5 Bolt 74B-A9B** · `bolt`<br><sub>hybrid MoE, 9B active · 2/4/8-bit mix, 25.1 GB</sub> | 🟩 1075 / **154**<br><sub>KFlash</sub> | × | 903 / 71<br><sub>0.7.3.dev2</sub> | × | × | × | 936 / 66<br><sub>mlx-vlm 0.7.10</sub> | × | × |
| **Nemotron 3.5 Super-VL 120B-A12B** · `super`<br><sub>hybrid MoE, 12B active · NVFP4, 76.4 GB</sub> | 🟩 **87**<br><sub>KFlash</sub> | × | 52<br><sub>0.7.1rc1</sub> | × | 64<br><sub>0.40.5</sub> | 44 | 46<br><sub>mlx-vlm 0.7.8</sub> | 66<br><sub>b11669</sub> | 61<br><sub>llama.cpp runtime 2.60.0</sub> |

**Recursive Flint**

| Model | <mark>**Kapitsa**</mark> | <sub>llama.cpp<br>Q4_1, b11871</sub> | <sub>rec<br>0.1.0</sub> |
| --- | ---: | ---: | ---: |
| **Recursive Flint 40B-A2.5B** · `flint`<br><sub>MoE, 2.5B active · 4-bit, 22.6 GB</sub> | 🟩 5770 / **265**<br><sub>KFlash</sub> | 3827 / 130 | 2863 / 224 |

**DiffuSpace Clover**

| Model | <mark>**Kapitsa**</mark> |
| --- | ---: |
| **Clover-35B-A3B-Preview** · `clover`<br><sub>block-diffusion MoE, 3B active · 4-bit pack converted by tools/convert_clover.py, 19.5 GB (measured; the catalog's `clover` serves the same files)</sub> | 🟩 6002 / **319**<br><sub>KFlash</sub> |

<sub>Kapitsa's cells are the 2026-11-01 runs (main 7f4e709, [results](bench/results/2026-11-01-m5-max-kapitsa/README.md)), each the median of three runs (Super-VL five) on AC power in High Power mode, Clover's excepted (2026-10-28). The other engines' 27B, 35B-A3B and Bolt cells are the 2026-10-25 session (each engine's latest release, macOS 26.4); llama.cpp's 35B-A3B cell and the other engines' Flash-Next, Lightning, Super-VL and Dory cells are the 2026-10-18 runs, not yet re-measured; rec's and llama.cpp's Flint cells are one block on 2026-10-26 ([results](bench/results/2026-10-26-m5-max/README.md)). The build each cell ran is under its number; details in [bench/results/2026-10-25-m5-max](bench/results/2026-10-25-m5-max/README.md) and [its re-runs](bench/results/2026-10-25-m5-max/2026-10-26-reruns.md).</sub>

</details>

<details>
<summary><b>MacBook Pro (16-inch, 2026) · M5 Pro · 48 GB</b> · 7 models</summary>

**Qwen and Nemotron**

| Model | <mark>**Kapitsa**</mark> | <sub>mlx‑serve<br>26.10.2</sub> | <sub>oMLX<br>0.7.1rc1</sub> | <sub>Splash<br>1.4.0</sub> | <sub>Ollama<br>0.40.5 / 0.40.6</sub> | <sub>MTPLX<br>2.12.2</sub> | <sub>MLX<br>mlx-lm 0.32.2, mlx-vlm 0.7.8</sub> | <sub>llama.cpp<br>b11669 / b11871</sub> | <sub>LM&nbsp;Studio<br>MLX runtime 1.13.1, llama.cpp runtime 2.60.0</sub> |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Qwen3.8-27B** · `27b`<br><sub>dense · 4-bit, 20.2 GB</sub> | 606 / 77<br><sub>KFlash</sub> | 🟩 464 / **78**<br><sub>DFlash2</sub> | 446 / 51<br><sub>DFlash2</sub> | 674 / 72<br><sub>DFlash2</sub> | 470 / 40<br><sub>MTP</sub> | 462 / 41<br><sub>MTP</sub> | 421 / 32<br><sub>MTP</sub> | 322 / 30<br><sub>MTP</sub> | 118 / 17 |
| **Qwen3.6-35B-A3B** · `35b`<br><sub>MoE, 3B active · 4-bit, 22.1 GB</sub> | 🟩 2802 / **201**<br><sub>KFlash</sub> | 2494 / 156<br><sub>MTP</sub> | 1619 / 144<br><sub>DFlash2</sub> | 3514 / 181<br><sub>DFlash2</sub> | 1518 / 102<br><sub>MTP</sub> | 2569 / 89<br><sub>MTP</sub> | 2474 / 98<br><sub>DFlash2</sub> | 1755 / 107<br><sub>MTP</sub> | 997 / 96 |
| **Qwen3.8-Flash-Next 180B-A7B** · `flash-next`<br><sub>MoE, 7B active · Q2_0 experts streamed from the SSD</sub> | 🟩 1218 / **61**<br><sub>KFlash · e67b764f</sub> | × | × | 1178 / **≈56**<br><sub>1.5.0</sub> | — | × | × | 37 / 9<br><sub>c7474afc</sub> | — |
| **Nemotron Dory1.0 4B** · `dory`<br><sub>looped dense · NVFP4, 3.2 GB</sub> | 🟩 **70**<br><sub>KFlash</sub> | × | × | × | × | × | 53 | 13 | × |
| **Nemotron 3.5 Lightning 30B-A3B** · `lightning`<br><sub>hybrid MoE, 3B active · NVFP4, 22.9 GB</sub> | 🟩 3141 / **159**<br><sub>KFlash</sub> | 1728 / 115<br><sub>MTP</sub> | 1938 / 124<br><sub>MTP</sub> | × | 2369 / 92 | 1743 / 101 | 1881 / 94 | 1915 / 101<br><sub>MTP</sub> | 1479 / 72 |
| **Nemotron 3.5 Bolt 74B-A9B** · `bolt`<br><sub>hybrid MoE, 9B active · 2/4/8-bit mix, 25.1 GB</sub> | 🟩 **79**<br><sub>KFlash</sub> | × | 39 | × | × | × | 41 | × | × |

**Recursive Flint**

| Model | <mark>**Kapitsa**</mark> | <sub>llama.cpp<br>b11804</sub> | <sub>rec<br>0.1.0</sub> |
| --- | ---: | ---: | ---: |
| **Recursive Flint 40B-A2.5B** · `flint`<br><sub>MoE, 2.5B active · 4-bit, 22.6 GB</sub> | 🟩 2691 / **149**<br><sub>KFlash</sub> | 2072 / 92 | 2138 / 145 |

<sub>Qwen3.8-Flash-Next 180B-A7B does not fit in 48 GB, so both engines stream its experts from the SSD. With Q2_0 weights on both and Kapitsa's expert store pinned at 24 GB (the auto size here is about 29.9 GB, but four runs at that size were stopped at memory pressure), Kapitsa's prefill is behind on short prompts, level at 4K and 16K and 2.7% ahead at 32K: not the fastest everywhere (correction, 24 Oct: on Kapitsa's warm second leg alone its prefill is 13.5-14.5% behind at 1K, level at 4K and a few percent ahead at 16K and 32K; [numbers and caveats](docs/benchmarks.md#qwen38-flash-next-streamed-from-the-ssd-kapitsa-against-llamacpp-m5-pro-48-gb-2026-10-24)). The Flash-Next 180B Q2 row's Kapitsa and Splash cells are a 2026-10-30 re-measure ([record](bench/results/2026-10-30-m5-pro-flash-next-kflash/README.md)): Kapitsa at main `e67b764f` running **KFlash** against the plain Splash 1.5.0 release, both at `--expert-memory 16G --idle-release off`, interleaved K S K S, 5 legs per arm of 2 runs each, with the scripts of the 2026-10-27 run. Its decode is a 256-token answer at T 0, not this table's 512-token answer at T 0.6, counted from the first token to the last over 10 requests per engine; its 4K prefill is prompt tokens over time to first token on that run's own 4,074-token prompt, against this table's 4,133. Kapitsa read 61.3 decode (53.7-64.7) and 1,218 prefill (976-1,269) against Splash's 56.5 (51.9-60.2) and 1,178 (1,040-1,262): the ranges overlap, so by the rule registered before the run it is a tie, not a win. KFlash's interleaved A/B at `--expert-memory 20G` (29 Oct, more runs per arm) measured decode 1.101x and 4K prefill 1.004x the release, the same tokens as the release on 6 prompts × 22 runs ([numbers](docs/benchmarks.md#m5-pro)). The llama.cpp cell is the 2026-10-27 four-engine run, PR #751 ([record](bench/results/2026-10-28-m5-pro-flash-next-engines/README.md)), 2 requests. Kapitsa's own engine ran in that record too, with MTP depth 2 and its expert store pinned at 24 GB, not sized from free memory: 847 prefill and 53.7 decode at T 0, but three of its legs were stopped at memory-pressure level 4, with up to 4.5 GB of swap, late in the leg (16K prefill or turn 2), so its 16K and turn-2 cells have 9 runs against 12. Ollama and LM Studio were not run on that Q2_0 pack, so their cells are dashes, and mlx-serve, oMLX, MTPLX and MLX have no pack of this model that fits 48 GB.</sub>

</details>

<details>
<summary><b>MacBook Pro (16-inch, 2024) · M4 Pro · 48 GB</b> · 7 models</summary>

**Qwen and Nemotron**

| Model | <mark>**Kapitsa**</mark> | <sub>mlx‑serve<br>26.10.2</sub> | <sub>oMLX<br>0.7.1rc1</sub> | <sub>Splash<br>1.4.0</sub> | <sub>Ollama<br>0.40.5 / 0.40.6</sub> | <sub>MTPLX<br>2.12.2</sub> | <sub>MLX<br>mlx-lm 0.32.2, mlx-vlm 0.7.8</sub> | <sub>llama.cpp<br>b11669 / b11871</sub> | <sub>LM&nbsp;Studio<br>MLX runtime 1.13.1, llama.cpp runtime 2.60.0</sub> |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Qwen3.5-4B** · `4b`<br><sub>dense · 4-bit, 4.6 GB</sub> | 🟩 1930 / **201**<br><sub>KFlash</sub> | 874 / 137<br><sub>MTP</sub> | 803 / 102<br><sub>MTP</sub> | × | 758 / 109<br><sub>MTP</sub> | 780 / 104<br><sub>MTP</sub> | 843 / 88<br><sub>MTP</sub> | 650 / 70<br><sub>MTP</sub> | 801 / 81 |
| **Qwen3.8-27B** · `27b`<br><sub>dense · 4-bit, 20.2 GB</sub> | 🟩 396 / **63**<br><sub>KFlash</sub> | 129 / 54<br><sub>DFlash2</sub> | 136 / 45<br><sub>DFlash2</sub> | 53<br><sub>DFlash2</sub> | 124 / 32<br><sub>MTP</sub> | 126 / 36<br><sub>MTP</sub> | 131 / 28<br><sub>MTP</sub> | 84 / 18<br><sub>MTP</sub> | 127 / 15 |
| **Qwen3.6-35B-A3B** · `35b`<br><sub>MoE, 3B active · 4-bit, 22.1 GB</sub> | 🟩 1168 / **161**<br><sub>KFlash</sub> | 986 / 124<br><sub>MTP</sub> | 1035 / 127<br><sub>DFlash2</sub> | 135<br><sub>DFlash2</sub> | 892 / 89<br><sub>MTP</sub> | 918 / 80<br><sub>MTP</sub> | 985 / 86<br><sub>DFlash2</sub> | 663 / 69<br><sub>MTP</sub> | 957 / 86 |
| **Nemotron Dory1.0 4B** · `dory`<br><sub>looped dense · NVFP4, 3.2 GB</sub> | 🟩 **64**<br><sub>KFlash</sub> | × | × | × | × | × | 48 | 6 | × |
| **Nemotron 3.5 Lightning 30B-A3B** · `lightning`<br><sub>hybrid MoE, 3B active · NVFP4, 22.9 GB</sub> | 🟩 945 / **112**<br><sub>KFlash</sub> | — | — | × | — | — | 721 / 65<br><sub>DSpark</sub> | — | — |
| **Nemotron 3.5 Bolt 74B-A9B** · `bolt`<br><sub>hybrid MoE, 9B active · 2/4/8-bit mix, 25.1 GB</sub> | 🟩 519 / **69**<br><sub>KFlash</sub> | — | 298 / 35 | × | — | — | 300 / 32 | × | — |

**Recursive Flint**

| Model | <mark>**Kapitsa**</mark> | <sub>llama.cpp<br>b11804</sub> | <sub>rec<br>0.1.0</sub> |
| --- | ---: | ---: | ---: |
| **Recursive Flint 40B-A2.5B** · `flint`<br><sub>MoE, 2.5B active · 4-bit, 22.6 GB</sub> | 🟩 968 / **128**<br><sub>KFlash</sub> | 977 / 80 | 796 / 127 |

<sub>Splash's cells are Splash 1.4.0 at decode only (2026-10-21): Splash needs macOS 26.4 or later, and this MacBook is on 27.0.1. On an AWS EC2 Mac mini M4 Pro (48 GB, macOS 26.7) on 2026-10-28, Splash 1.4.1 read 1056 / 140 on the 35B-A3B and 251 / 50 on the 27B, against Kapitsa 0.2.23's 1171 / 169 and 392 / 65 on the same Mac ([record](bench/results/2026-10-28-m4pro-ec2-macos26/README.md)).</sub>

</details>

<details>
<summary><b>MacBook Pro (16-inch, 2023) · M3 Pro · 36 GB</b> · 10 models</summary>

**Qwen and Nemotron**

| Model | <mark>**Kapitsa**</mark> | <sub>Ollama<br>0.40.8</sub> | <sub>MTPLX<br>2.12.2</sub> | <sub>MLX<br>mlx-lm 0.32.2, mlx-vlm 0.7.8</sub> | <sub>llama.cpp<br>b11669 / b11871</sub> |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Qwen3.5-4B** · `4b`<br><sub>dense · 4-bit, 4.6 GB</sub> | 🟩 703 / **120**<br><sub>KFlash</sub> | 600 / 67<br><sub>MTP</sub> | 612 / 64<br><sub>MTP</sub> | 642 / 56<br><sub>MTP</sub> | 512 / 50<br><sub>MTP · b11804</sub> |
| **Qwen3.5-9B** · `9b`<br><sub>dense · 4-bit, 9.0 GB</sub> | 🟩 381 / **77**<br><sub>KFlash</sub> | — | — | 353 / 27 | 307 / 23<br><sub>b11804</sub> |
| **Qwen3.8-27B** · `27b`<br><sub>dense · 4-bit, 20.2 GB</sub> | 🟩 110 / **40**<br><sub>KFlash</sub> | 99 / 23<br><sub>MTP</sub> | 99 / 22<br><sub>MTP</sub> | 102 / 18<br><sub>MTP</sub> | 86 / 16<br><sub>MTP · b11804</sub> |
| **Qwen3.6-35B-A3B** · `35b`<br><sub>MoE, 3B active · 4-bit, 22.1 GB</sub> | 🟩 855 / **106**<br><sub>KFlash</sub> | 681 / 58<br><sub>MTP</sub> | 671 / 53<br><sub>MTP</sub> | 695 / 53<br><sub>DFlash2</sub> | 578 / 53<br><sub>MTP · b11804</sub> |
| **Nemotron Dory1.0 4B** · `dory`<br><sub>looped dense · NVFP4, 3.2 GB</sub> | 🟩 450 / **36**<br><sub>KFlash</sub> | × | × | 344 / 30 | — |
| **Nemotron 3 Nano 4B** · `nano-4b`<br><sub>hybrid Mamba-2 · FP8, 5.3 GB</sub> | 765 / 34<br><sub>KFlash</sub> | — | — | — | 🟩 413 / **35**<br><sub>Q4_K_M, b11804</sub> |
| **Nemotron Nano 9B v2** · `nano-9b`<br><sub>hybrid Mamba-2 · NVFP4, 7.9 GB</sub> | 330 / 21<br><sub>KFlash</sub> | — | — | 🟩 **25**<br><sub>4-bit</sub> | — |
| **Nemotron 3.5 Lightning 30B-A3B** · `lightning`<br><sub>hybrid MoE, 3B active · NVFP4, 22.9 GB</sub> | 🟩 788 / **75**<br><sub>KFlash</sub> | — | — | 514 / 39<br><sub>DSpark</sub> | — |
| **Nemotron 3.5 Bolt 74B-A9B** · `bolt`<br><sub>hybrid MoE, 9B active · 2/4/8-bit mix, 25.1 GB</sub> | 🟩 256 / **50**<br><sub>KFlash</sub> | — | — | — | — |

**Recursive Flint**

| Model | <mark>**Kapitsa**</mark> | <sub>llama.cpp<br>b11804</sub> |
| --- | ---: | ---: |
| **Recursive Flint 40B-A2.5B** · `flint`<br><sub>MoE, 2.5B active · 4-bit, 22.6 GB</sub> | 🟩 801 / **74**<br><sub>KFlash</sub> | 772 / 51 |

<sub>macOS 14.1, on AC power: Kapitsa's macOS 14 kernels (macOS 15 and later run fused ones). mlx-serve, oMLX and Splash need a newer macOS (×); LM Studio was not installed; rec 0.1.0 refuses this Mac: it requires 48 GiB. Each cell but Flint's is one run of the M4 Pro's protocol (Flint's is the mean of two runs, #341), the other engines in the M4 Pro's setup (not re-tuned here). Nano 4B and 9B v2: Kapitsa runs NVIDIA's published checkpoints, which keep some layers in BF16/FP8, so it reads more per token than the 4-bit files: the 4B's FP8 is ~1 byte per weight against Q4_K_M's ~0.6, the 9B's NVFP4 ~6.11 GB per token against 4.67 GB for mlx-lm's 4-bit. Nano 9B v2 on mlx-lm: no prefill shown, because its template ignores enable_thinking and the timed first token is a thinking token.</sub>

</details>

<details>
<summary><b>MacBook Pro (14-inch, 2021) · M1 Pro · 16 GB</b> · 7 models</summary>

**Qwen and Nemotron**

| Model | <mark>**Kapitsa**</mark> | <sub>mlx‑serve<br>26.10.2</sub> | <sub>oMLX<br>0.7.1rc1</sub> | <sub>Ollama<br>0.40.5 / 0.40.6</sub> | <sub>MTPLX<br>2.12.2</sub> | <sub>MLX<br>mlx-lm 0.32.2, mlx-vlm 0.7.8</sub> | <sub>llama.cpp<br>b11669 / b11871</sub> | <sub>LM&nbsp;Studio<br>MLX runtime 1.13.1, llama.cpp runtime 2.60.0</sub> |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Qwen3.5-4B** · `4b`<br><sub>dense · 4-bit, 4.6 GB</sub> | 🟩 401 / **97**<br><sub>KFlash</sub> | 286 / 62<br><sub>MTP</sub> | 281 / 55<br><sub>MTP</sub> | 298 / 55<br><sub>MTP</sub> | 305 / 42<br><sub>MTP</sub> | 308 / 46 | 315 / 38<br><sub>MTP</sub> | 308 / 47 |
| **Qwen3.5-9B** · `9b`<br><sub>dense · 4-bit, 9.0 GB</sub> | 🟩 217 / **57**<br><sub>KFlash</sub> | 159 / 37<br><sub>MTP</sub> | — | — | — | 170 / 30 | — | — |
| **Qwen3.6-35B-A3B** · `35b:16gb`<br><sub>MoE, 3B active · 2-bit experts (unsloth's GGUF), 10.8 GB</sub> | 🟩 462 / **52**<br><sub>KFlash</sub> | × | × | — | × | × | 38 | — |
| **Nemotron Dory1.0 4B** · `dory`<br><sub>looped dense · NVFP4, 3.2 GB</sub> | 🟩 **39**<br><sub>KFlash</sub> | × | × | × | × | 30 | 4 | × |
| **Nemotron 3 Nano 4B** · `nano-4b`<br><sub>hybrid Mamba-2 · FP8, 5.3 GB</sub> | 🟩 **37**<br><sub>KFlash</sub> | — | — | — | — | 21<br><sub>BF16</sub> | 28<br><sub>Q4_K_M</sub> | — |
| **Nemotron Nano 9B v2** · `nano-9b`<br><sub>hybrid Mamba-2 · NVFP4, 7.9 GB</sub> | 🟩 **25**<br><sub>KFlash</sub> | — | — | — | — | 18 | 14<br><sub>Q4_K_M</sub> | — |

**Recursive Flint**

| Model | <mark>**Kapitsa**</mark> | <sub>llama.cpp<br>d772569</sub> |
| --- | ---: | ---: |
| **Recursive Flint 40B-A2.5B** · `flint:16gb`<br><sub>MoE, 2.5B active · 2-bit experts (unsloth's GGUF), 11.9 GB</sub> | 🟩 414 / **61**<br><sub>KFlash</sub> | 43 |

</details>

<sub>Other precisions: `--model 35b:6bit` is five times closer to bf16 than the 4-bit default ([KL](docs/benchmarks.md#quality-qwen36-35b-a3b-against-bf16-2026-10-19)). All but Lightning, Dory, the two Nemotron Nanos, Flint, Clover and the 35B's `16gb` read images. What runs on a Mac of each size: [Supported models](#supported-models). [Every model's variants and draft models](docs/usage.md#models-and-downloads)</sub>

## How it works

<picture>
  <source media="(max-width: 600px)" srcset="docs/assets/how-it-works-narrow.svg">
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/how-it-works-dark.svg">
  <img alt="How Kapitsa works: DFlash2 vs KFlash. DFlash2, the drafter's chain, as Splash, oMLX and mlx-serve run it: the drafter guesses the next 7 tokens, the big model checks them in one pass and keeps them up to the first wrong guess (return a, 2 tokens). KFlash, Kapitsa's: in the same one pass the big model checks a best-first tree of the drafter's top candidates in 8 rows; where the drafter is unsure its runner-ups ride along, and the longest branch the big model agrees with is kept (return a + b, 4 tokens). Same output as plain decoding, tree size measured on each Mac, 8-17% more tokens per pass on short prompts. Below: GPU, hand-written Metal code; Neural Engine, helps read long prompts on the 4B, 27B, Bolt and Super-VL; Memory, keeps conversations ready, up to 4 at once." src="docs/assets/how-it-works-light.svg">
</picture>

Kapitsa decodes with **KFlash**. A draft model such as DFlash2 guesses the next seven tokens, with a few candidates for each one. Engines that run it as published (Splash, oMLX, mlx-serve) check one chain of guesses and stop at the first wrong one. KFlash checks a best-first tree of the drafter's candidates in the same pass, so where the drafter hesitates, its runner-ups are checked too and more tokens survive each pass. The tree's size comes from what a verify row costs on your Mac, measured there, and it changes no output: the big model checks every token. It runs on the published drafters as they are: z-lab's DFlash, DFlash2, and NVIDIA's DSpark and LiLiCorr. [How KFlash works](docs/kflash.md)

## Get release notices

Watch → Custom → Releases on [nace-ai/kapitsa](https://github.com/nace-ai/kapitsa) puts every new version in your notifications.

## Star history

<a href="https://star-history.com/#nace-ai/kapitsa&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=nace-ai/kapitsa&type=Date&theme=dark">
    <img alt="Star history of nace-ai/kapitsa on GitHub" src="https://api.star-history.com/svg?repos=nace-ai/kapitsa&type=Date">
  </picture>
</a>

<sub>[How KFlash works](docs/kflash.md) · [Architecture](docs/architecture.md) · [Contributing](CONTRIBUTING.md) · [Press kit](docs/assets/brand/README.md) ·
Apache 2.0, © 2026 [Nace AI](https://nace.ai) · [Third-party notices](THIRD_PARTY_NOTICES)</sub>

# HF Hub GGUF cache cleanup — 2026-09-06

## Scope and authorization

Tijs clarified that primary MLX candidates and their staged copies must be kept (including Ornith and the active Qwen3.6 candidate), while the fully tested GGUF model caches may be removed. This cleanup touched only the four explicit HF Hub model directories below. No `mei-models` directory, provenance file, benchmark result, or shared HF cache root was removed.

## Pre-delete checks

- Active benchmark remained isolated on the staged MLX path:
  `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit`
- Mei server remained on port 8024; no deleted HF Hub path had open file handles.
- HF Hub model directories were public and recoverable from Hugging Face.
- The active benchmark repository had in-progress result changes; none were staged or modified by this cleanup.

## External reference verification

Each local snapshot revision and large-file size matched the public Hugging Face tree:

| Repository | Private | HF API SHA | Local snapshot | Matching large file |
|---|---:|---|---|---:|
| `mudler/gemma-4-26B-A4B-it-APEX-GGUF` | false | `e79ec24ceca5060b55b9a267c565b0b0843f3678` | same | `20576637248` bytes |
| `ornith-ai/Ornith-1.5-35B-A3B-GGUF` | false | `12393612fd4f730ff5aadc23e9b8f9648aa49ceb` | same | `21713463040` bytes |
| `trohrbaugh/Qwen3.8-27B-heretic-ara-gguf-Q5` | false | `26f9b116cb7522faa3989b584cb37b4d41cd0191` | same | `19704559264` bytes |
| `unsloth/Qwen3.8-27B-GGUF` | false | `4ca720788d1e01f1bff70c033e0d0028fd02e502` | same | `19771509664` bytes |

## Deleted paths and before sizes

| Absolute path | `du -sk` before |
|---|---:|
| `/Users/tijs/.cache/huggingface/hub/models--mudler--gemma-4-26B-A4B-it-APEX-GGUF` | 20,094,380 KiB |
| `/Users/tijs/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-35B-A3B-GGUF` | 21,204,560 KiB |
| `/Users/tijs/.cache/huggingface/hub/models--trohrbaugh--Qwen3.8-27B-heretic-ara-gguf-Q5` | 19,242,740 KiB |
| `/Users/tijs/.cache/huggingface/hub/models--unsloth--Qwen3.8-27B-GGUF` | 19,308,120 KiB |
| **Total** | **79,849,800 KiB** |

## Post-delete verification

- All four explicit paths are absent.
- No `models--*` model directories remain directly under `/Users/tijs/.cache/huggingface/hub`.
- No `.incomplete` files were found under the HF Hub root or retained Mei model root.
- Retained MLX staged roots still exist:
  - `Ornith-1.5-35B-A3B-MLX-4bit-aligned` — 18.19 GiB
  - `Qwen3.6-35B-A3B-4bit` — 19.03 GiB
  - `Qwen3.8-27B-4bit` — 14.98 GiB
  - `Qwen3.8-27B-Uncensored-MLX-4bit` — 14.98 GiB
  - `gemma-4-26b-a4b-it-4bit` — 14.32 GiB

## Disk result

- Before: 380 GiB used, 34 GiB available, 92% capacity.
- After: 304 GiB used, 110 GiB available, 74% capacity.
- Reported filesystem change: approximately 76 GiB reclaimed, consistent with the explicit 79,849,800 KiB aggregate.

The active Qwen3.6 Mei benchmark was still running after cleanup; its server process and staged model path were unchanged.

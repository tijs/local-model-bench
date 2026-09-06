# MLX candidate discard cleanup — 2026-09-06

## Scope and decision

Tijs officially discarded Gemma and Qwen3.8 as too low-quality/too slow. This cleanup removed their staged MLX model copies and tied provenance sidecars. Historical benchmark results and configs remain preserved as evidence; this is a storage/candidate cleanup, not a rewrite of past measurements.

## Pre-delete checks

- The active Mei benchmark was serving only:
  `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.6-35B-A3B-4bit`
- Its live KV cache was `mei-runtime/kv-qwen36-35B`.
- The shared Mei build `mei-build-67e897e` was retained.
- No deleted model directory or provenance sidecar had open file handles.
- No Gemma- or Qwen3.8-specific runtime KV cache existed; only the active Qwen3.6 cache was present.

## External reference verification

The staged model sources were public and recoverable:

| Model | Repository/revision | Public | Local staged weight bytes |
|---|---|---:|---:|
| Gemma 4 | `mlx-community/gemma-4-26b-a4b-it-4bit` / `main` (`0d77464eeb233a2da68ebf9d7dc4edaac7db956d`) | true | 15,341,206,796 |
| Qwen3.8 | `mlx-community/Qwen3.8-27B-4bit` / `main` (`3e6447f082e89cc7f0bc6e5441afd38dfce760ff`) | true | 16,054,542,296 |
| Qwen3.8 uncensored | `orcarouter/Qwen3.8-27B-Uncensored-MLX` / `14963e70f886455cf93090ac95bdbf4c8730cbe1` | true | 16,054,541,692 |

The local staged weight totals matched the corresponding upstream 4-bit shard sets within the expected safetensors header-padding differences.

## Deleted paths and before sizes

| Absolute path | `du -sk` before |
|---|---:|
| `/Users/tijs/.local/share/local-model-bench/mei-models/gemma-4-26b-a4b-it-4bit` | 15,013,356 KiB |
| `/Users/tijs/.local/share/local-model-bench/mei-models/gemma-4-26b-a4b-it-4bit.provenance.json` | 4 KiB |
| `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.8-27B-4bit` | 15,704,700 KiB |
| `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.8-27B-4bit.provenance.json` | 4 KiB |
| `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.8-27B-Uncensored-MLX-4bit` | 15,704,708 KiB |
| `/Users/tijs/.local/share/local-model-bench/mei-models/Qwen3.8-27B-Uncensored-MLX-4bit.provenance.json` | 4 KiB |
| **Total** | **46,422,776 KiB** |

## Post-delete verification

- All six explicit paths are absent.
- Remaining staged model roots are only:
  - `Ornith-1.5-35B-A3B-MLX-4bit-aligned` — 18.19 GiB
  - `Qwen3.6-35B-A3B-4bit` — 19.03 GiB
- Remaining provenance sidecars correspond only to Ornith and Qwen3.6.
- `kv-qwen36-35B`, the shared Mei build, benchmark logs, configs, and historical results remain.
- No `.incomplete` markers were found under the retained model or runtime roots.

## Disk result

- Before: 304 GiB used, 110 GiB available, 74% capacity.
- After: 259 GiB used, 153 GiB available, 63% capacity.
- Reported filesystem change: approximately 44 GiB reclaimed, consistent with the explicit 46,422,776 KiB aggregate.

The active Qwen3.6 benchmark remained running after cleanup and continued using its staged model and KV cache.

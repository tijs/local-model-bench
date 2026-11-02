---
license: apache-2.0
base_model:
- GrootTeam/Groot-19B-A3B-261023
- hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw
library_name: mlx
pipeline_tag: text-generation
tags:
- mlx
- qwen3_5_moe
- text-only
---
# Groot 19B/A3B RCO role 4.5 bpw — text-only preparation

A text-only preparation of [hermitdave's quant](https://huggingface.co/hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw),
derived from [GrootTeam's model](https://huggingface.co/GrootTeam/Groot-19B-A3B-261023).
All retained language tensor bytes, shapes and dtypes are preserved. Vision and
MTP tensors are removed, saving about 1.78 GB of staged weight storage. The five
weight files total **12,294,068,648 bytes**.

The preparation makes supported mixed precision explicit, including split six-bit
projections omitted from the source map, and reconciles stale quantization names.
Every retained payload has a SHA256 in `MEI_TEXT_EXPORT.json`. This verifies the
preparation; it does not establish BF16 accuracy parity or multimodal capability.

## Use with Mei

```sh
uvx --from huggingface-hub hf download Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly --revision 53f52e0eb8d67d2941010688b2a6b8807d9a3bea --local-dir ./Groot-text
mei-preview --model-dir ./Groot-text --model-profile groot-19b-a3b-text --served-model-id Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly
```

[Mei 0.10.0-rc.2](https://github.com/tijs/mei/releases/tag/v0.10.0-rc.2) is released
and available through `brew install tijs/tap/mei-preview`. The distributed binary
passed all 13 native probes, including streaming/nonstreaming automatic tools,
cache history, exact 65,536-token admission and over-cap rejection. This is a
qualified preview, not a stable-promotion or full-window quality claim.

Use `--model-profile groot-19b-a3b-text` for the named settings (prefill 256,
anchors off, server cap 8192); explicit flags take precedence. The example above
uses server defaults beyond those flags. Exact benchmark context, sampler and
cache settings are in the committed [profiles and reviews](https://github.com/tijs/local-model-bench/blob/main/docs/FINALIST_REPEATS.md).
Other MLX runtimes require their own acceptance tests.

## Benchmark follow-up

On the exact distributed Mei rc.2 executable and the immutable weight snapshot
`53f52e0eb8d67d2941010688b2a6b8807d9a3bea`, the predeclared v9.8 trials scored:

| Request seed | Household | Python | Full-run wall time |
|---:|---:|---:|---:|
| 17 | 11/12 | 3/3 | 10m19s |
| 29 | 10/12 | 3/3 | 10m14s |

Both ran on an M1 Max 32 GiB with normal pressure and no swap growth. Wall time
includes startup, admission and both tracks, excluding the 30-second baseline. Both
repeated a deleted numeric value after correctly saying it was unavailable;
seed 29 additionally made one unassigned routing call before recovering.
All Python scripts passed four isolated fixture variants. These are synthetic
household workflows and real bounded Python tasks, not Peixinho app acceptance
or a pure base-model/quantization ablation. Both outcomes remain public; two
trials do not prove independence or universal reliability. The older v9.5
12/12+3/3 result retains its original model/runtime/method identity.

[Seed 17 review](https://github.com/tijs/local-model-bench/blob/main/artifacts/groot-rc2-v9p8-seed17-20261102/README.md) ·
[Seed 29 review](https://github.com/tijs/local-model-bench/blob/main/artifacts/groot-rc2-v9p8-seed29-20261102/README.md)

This model-card follow-up changes documentation only. The original immutable
snapshot and all weight/config/tokenizer files are preserved.

Shard filenames retain the source numbering. The sixth source shard contained
only removed tensors; the five distributed files contain the complete retained
language model. Mei loads those files directly. Keep hardlinked local preparation
files immutable if you recreate the export yourself.

## Provenance and limits

- Original model revision: `d089dadfe280289b2f3cd2ae9ef9796c2495529a`.
- Quant revision: `6b0c0cfedb818d739ce5fded969dbbb071546f45`.
- Preparation tool: Mei `e191d1a`, `tools/export_qwen_text.py`.
- Context, sampler and runtime choices remain explicit benchmark profiles.
- Text-only; vision and MTP are absent. Full-window usability and application
  acceptance require separate tests.

License: Apache-2.0, as declared by both source model cards. See `LICENSE` and
`ATTRIBUTIONS.md`. The original model authors and quantizer retain their credit.

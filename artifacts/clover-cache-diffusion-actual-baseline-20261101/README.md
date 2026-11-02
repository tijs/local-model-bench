# Clover early-residency cache controls: passed

All three cases passed in **262.708 seconds**, excluding the host baseline:
repeated prompt, growing tool history and continuation after a seven-token
partial diffusion block. Each warm response matched two deterministic cold
responses, including reasoning, content and parsed tool arguments. Random tool
call IDs are excluded. All tool contracts passed.

| Case | Warm cached tokens | Cold cached tokens | Cold determinism | Warm equals cold |
|---|---:|---|---|---|
| Repeat | 1,577 | 0 / 0 | Passed | Passed |
| Growing tool history | 1,646 | 0 / 0 | Passed | Passed |
| After partial block | 1,572 | 0 / 0 | Passed | Passed |

Seven fresh model processes ran sequentially. All 51 resource samples were
normal and swap did not grow. Every restart used seven normal-pressure,
flat-swap recovery observations; wired/compressor bytes remained telemetry.
All 15 model-file hashes matched afterward. The owned server stopped; no disk
cache was enabled and weights remain staged.

This qualifies these focused cache controls on the early-weight-residency
candidate. It does not prove a universal memory fix, near-64K behavior, pure
base-model/quant quality or actual Peixinho acceptance. No scored rows were
created. The original loader's two resource interruptions and the overly strict
recovery-condition timeout remain separately preserved.

Source: derived local `211b2b47c59e42cbe16ce81b08c96ac1dff23d6c`, binary
`5f42ec14ab1c62b2fdbf5121e0deee83452576fdfce50b194a49f4119453546f`.
The [published base/patch/tree and license](../candidate-system-campaign-20261101/kapitsa-loader-residency-preparation/)
reproduce this source, which is not an upstream release. Decoder: native
Kapitsa/Metal, actual 32-row block diffusion/threshold 0.95, no drafter. The
MLX-format weight pack is unchanged.

[Comparison](cache-comparison.json) · [Outcome](outcome.json) ·
[Resource samples](resources.jsonl) · [Post-run hashes](post-run-model-hashes.json)

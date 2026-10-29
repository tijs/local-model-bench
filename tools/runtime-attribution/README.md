# Fixed-history runtime attribution probe

Diagnostic only; never writes benchmark result rows. It links exact published
Mei/VMLX source revisions rather than a mutable local checkout. Production
Mei/VMLX repositories and APIs are unchanged.

Build with Xcode's Swift toolchain and explicit testing visibility (required to
reuse Mei's internal default-off Flint registration):

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  swift build -c release -Xswiftc -enable-testing --package-path tools/runtime-attribution \
  --scratch-path /absolute/external/build
```

Provision Metal with the pinned Mei `scripts/prepare_metallib.sh`, pointing
`MEI_VMLX_CHECKOUT` and `MEI_METALLIB_BUILD_DIR` at that build's actual checkout
and release directory. Do not mix this diagnostic binary with the normal server.

CLI requires `--model DIR --input CASES.json --out NEW_DIR --prefill N --tail N`.
`--render-only` performs tokenizer work only. For inference run under the
benchmark's existing resource supervisor, with `VMLX_ENABLE_UNSAFE_COMPILE=0`.
Use one model owner at a time and record all source, dependency, binary, Metal,
input and model hashes before execution. Raw float arrays stay outside Git.

Each case supplies the archived request and parsed bad assistant object. Native
rendering of the completed turn must extend the exact request-token prefix.
The resulting forced continuation is canonical, **not a verbatim raw-decoder
capture**. It preserves each model's own tool syntax and reasoning format.

The probe compares ordinary cache-off, an unwrapped repeat, cold coordinator,
same-instance warm reuse, and cache-off with the coordinator's actual preparation
segments. A transparent wrapper records prepare calls until the first logits;
matching replay must consume exactly the same segments. Wrapped/unwrapped logits
must match before any attribution. Every path must consume identical forced IDs,
produce finite full-vocabulary tail rows and exercise positive warm restoration.
The independent Python reference uses the exported IDs and recorded segments.

Matching a bounded set of canonical histories does not establish all runtime
correctness, original stochastic-trajectory parity, disk-deserialization behavior
or base-model/quant/shared-kernel attribution. The dated investigation under
`artifacts/runtime-attribution-20261029/` records those limits and actual outcomes.

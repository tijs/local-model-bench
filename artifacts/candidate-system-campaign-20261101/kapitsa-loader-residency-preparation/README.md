# Early weight residency: preparation record

This records the initial unqualified experiment. Later native/cache controls
and both full trials completed on the candidate with normal pressure and no
swap growth: [current diffusion review](../../../docs/CLOVER_NATIVE.md).
That qualifies the pinned profile, not a universal memory-fix or causal proof.

The cache controls exposed compression/warning/swap spikes during repeated
Clover loads, even after observed host recovery. The original loader fills
shared weight buffers on the CPU, then makes them resident later in model
initialization. This candidate requests each shard buffer's residency before
filling it, so its streamed pages need not remain compressible until that final
request. This is a hypothesis, not a proven root cause or working fix.

The patch inserts six lines in `src/loader/safetensors.cpp`. It changes no
tensor payload, layout, kernel, numerical operator or decoder. Existing
`NI_RESIDENCY` behavior still decides whether a set is used. The original
Kapitsa checkout and executable remain unchanged.

Build and seven selected CPU tests pass, as does upstream `prek run --all-files`.
No live qualification is claimed by this preparation. The new native profile
must pass actual tools/cache/resource controls before scored evaluation.

## Source and reproduction

Base: [nace-ai/kapitsa](https://github.com/nace-ai/kapitsa/tree/70fb55528ad34cbd40c1609c709c1b604766d45d),
Apache-2.0; see [upstream license](UPSTREAM-LICENSE.txt).
Apply [the patch](early-weight-residency.patch) to that clean pinned base.
The resulting Git tree must be `3cfca8464b5c560e272f763632d31420b0ee8b50`.
Build with the upstream CMake release commands and the documented GPU lock for
any later model use. No model files are included here.

The measured local source commit is
`211b2b47c59e42cbe16ce81b08c96ac1dff23d6c`; it is not an upstream/public remote
revision. The published base, patch and tree hash reproduce the source rather
than asking readers to fetch that unavailable commit. A rebuild has its own
binary identity and needs its own committed benchmark config/admission.

[Build and test provenance](build-provenance.json) ·
[CPU tests](cpu-tests.log) · [Lint](prek.log) ·
[Native profile](../../../configs/candidates-20261101/clover-kapitsa-diffusion-native-early-residency.yaml)

# Clean launch audit for the upstream refresh

The residency forwarding change moved the committed launcher hash from
`cfc685b7…` to `bfa28f23…`. The negative test reproduces the stale audit pin.
The updated verifier admits those two exact audited launcher identities,
still rejects unknown/malformed pins and verifies the executed bytes against
the recorded Git object. Historical Groot receipts still validate.

The launcher change only adds enum-validated explicit residency forwarding
and updates help. It introduces no environment default or shell startup hook.
A fake executable verifies that the committed-script path forwards the flag
and excludes inherited Bash functions, BASH_ENV, trace flags and secrets.
No builds or real model loads occur in those fixture tests.

The source audit additionally admits stable Mei2018275d/vMLX9db62ce and
candidate Mei47fdf020/vMLX3fa3d7ed. The stable Sources/Package inputs are
unchanged from the previously audited b5451a8 build; only packaging scripts
and documentation changed. Candidate host changes bind owned weight storage,
explicit bounded residency and legacy-setting rejection. The fixed allowlist
continues to pin unsafe compilation, routed-MoE compilation and fused cache
off; load traces and other inherited variables remain excluded. The executable
and exact Metal artifact remain separately hashed by runtime provenance.

22 clean-launch/qualification tests and17 launcher tests pass. This is harness
validation, not real-model speed qualification or permission to promote Mei.

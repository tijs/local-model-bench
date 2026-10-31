# local-model-bench benchmark-v7.1

Corrects the response-header deadline in both household and Python tracks from30
to90 seconds, matching their existing90-second first-progress allowance. Mei
delays streaming headers until the first engine event so setup/admission failures
can still return a proper HTTP error status. A valid prompt preparation taking
more than30 seconds could therefore exhaust the old header limit before the
first-progress allowance was available. The180-second overall turn deadline,
task/token/turn budgets, sampling, validators and resource guards are unchanged.

A real delayed-header HTTP regression fails with the old limit and passes with
the corrected limit. All655 locked tests pass in95.39 seconds; Ruff and ty pass. This is a transport
budget correction, not a relaxation of task success or household safety checks.

The first released v7 Flint held-out attempt is preserved as household run
`20261031T074937Z-b29b90e2`: two tasks passed, then multipart continuation exceeded
the30-second response-header limit. Only3/12 household tasks ran, and Python did
not run. Normal memory pressure and unchanged swap exclude a resource stop in
this attempt. Its rows remain partial evidence, not a full-model score. Logs were
preserved before2,742,503,442 bytes of owned KV cache were removed.

The earlier complete Qwen development calibration remains evidence for v7 under
its original recorded30-second header budget. It is not converted to a v7.1
result. The four-model held-out comparison must use this patch release's exact
method/config identities for all selected runs. See the
[v7 methodology](benchmark-v7.md) for task and containment boundaries.

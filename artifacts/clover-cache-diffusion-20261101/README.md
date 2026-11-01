# Clover cache controls: interrupted during cold-process handover

The parent stopped the experiment after swap grew from1,419.88 to3,697.69MiB
(2,277.81MiB). It sampled one warning followed by normal pressure; the independent
2GiB swap-growth limit triggered after27.179seconds. The owned server stopped.
All15 model files matched afterward. This is incomplete diagnostic evidence,
with no cache-equivalence verdict, task score or model-quality conclusion.

The first process completed the repeated prompt, growing tool history and
seven-token partial-block follow-up. The follow-up requests returned structured
calls and actual cache hits. The cold comparisons had not completed when the
second process was stopped during loading. Warm calls alone cannot prove cache
equivalence.

The resource trace shows wired memory falling from about21.46GiB to2.60GiB
between processes, while compressor memory briefly reached15.83GiB during the
next load; swap growth followed. This localizes the spike to rapid process/load
handover, but does not identify its allocator/driver root cause. A process exit
alone did not establish a quiet resource window for the next model load.

The next declared profile adds a bounded recovery observation after every
process exit: seven normal-pressure/flat-swap samples, wired and compressor
bytes within512MiB of the initial baseline, at most90seconds. Global pressure,
swap, disk and deadline stops remain unchanged. This is a cleanup/recovery
condition, not a free-percentage capacity gate. No unrelated applications or
services were stopped and no system-wide purge was used.

The original cache script used1024 tokens for its request controls, despite
the inherited native-config budget field saying4096. The original source and
requests preserve what actually ran. The new profile explicitly declares1024
and the script reads that field. No historical evidence is edited.

[Outcome](outcome.json) · [Resource trace](resources.jsonl) ·
[Warm requests/responses](.) · [First server](server-1.log) ·
[Second server](server-2.log) · [Post-run hashes](post-run-model-hashes.json)

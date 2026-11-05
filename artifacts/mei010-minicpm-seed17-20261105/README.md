# MiniCPM startup failure — seed 17

The owned server timed out waiting for health after 1,804 seconds, before admission or any task rows. Its main thread was blocked in the operating system while opening the GGUF under the Expansion-backed Hugging Face cache; a directory listing of that snapshot also blocked. This does not establish model quality or memory failure. The process exited after the startup timeout. The separately downloaded internal copy matches the pinned publisher SHA-256 and size; see [staging receipt](../mei-stable-qualification-20261102/minicpm-internal-staged-model-hashes.json).

Evidence: [outcome](outcome.json), [server log](server.log), [process sample](startup-process-sample.txt), [resource samples](resources.jsonl), and [configuration](config.yaml).

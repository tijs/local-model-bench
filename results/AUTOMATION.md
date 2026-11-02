# Python automation

Real isolated Python execution on synthetic files. Separate from household workflow and real Peixinho app results.

Each submitted script is checked on visible and unseen fixture variants. Shared server/cache trials are not independent samples.

| Run | Model / engine | Config / runner | Partition / profile | Status | Executed / planned | Passed | Invalid calls | Task seconds |
|---|---|---|---|---|---:|---:|---:|---:|
| 20261029T203120Z-9d094ff0 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 3f6c0d34e1a8 / c1af468a36fd+dirty | development / model_card | running (incomplete/unusable) | 2/3 | 1 | 0 | 66.55 |
| 20261031T074330Z-0e134560 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 324174f0b837 / cc2fc1b0ea7a | development / model_card | completed | 3/3 | 3 | 0 | 95.11 |
| 20261031T215706Z-a78ab535 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | bbff2f1ff45d / 4efa076ca91e | heldout / model_card | completed | 3/3 | 2 | 1 | 99.55 |
| 20261101T101654Z-c9239aca | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | d4c9ac05c7bb / 9073dda058d6 | heldout / model_card | completed | 3/3 | 0 | 3 | 310.95 |
| 20261101T103610Z-d5de7e35 | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 8f7ae9ba649b / 56db80b8d61a | heldout / model_card | completed | 3/3 | 3 | 0 | 89.22 |
| 20261101T105601Z-7a8bf77e | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | d4c9ac05c7bb / e01b2b02457e | heldout / model_card | interrupted (incomplete/unusable) | 2/3 | 0 | 1 | 101.39 |
| 20261101T112104Z-6fbe24e4 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | d4c9ac05c7bb / 81a315f15bc4 | heldout / model_card | completed | 3/3 | 2 | 0 | 247.03 |
| 20261101T121557Z-29c77d62 | openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M / llama.cpp | d23069a83dd4 / cae5818180b2 | heldout / instruct | completed | 3/3 | 2 | 0 | 113.36 |
| 20261101T194323Z-2301e961 | hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw / mei | d67be3456120 / 51b8e9c2adda | heldout / model_card | completed | 3/3 | 3 | 0 | 209.57 |
| 20261101T202927Z-699cdc5e | bottlecapai/ThinkingCap-gemma-4-26B-A4B-it-GGUF:Q4_K_M / llama.cpp | 54253c2bab35 / 0834ad036f3c | heldout / thinking | completed | 3/3 | 3 | 0 | 271.34 |
| 20261101T204934Z-6cf50401 | openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q4_K_M / llama.cpp | 04d3b7d81e73 / d6fd01417719 | heldout / instruct | completed | 3/3 | 3 | 0 | 169.49 |
| 20261101T210635Z-aa8c55ce | Tostibrown/Qwen3.6-35B-A3B-4bit-textonly / mei | 8f7ae9ba649b / 72b6376db223 | heldout / model_card | completed | 3/3 | 3 | 0 | 103.57 |
| 20261101T211729Z-8acde4a3 | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit / mei | d4c9ac05c7bb / 46406ad1b123 | heldout / model_card | completed | 3/3 | 2 | 1 | 284.25 |
| 20261101T213227Z-d8513cc2 | hermitdave/Groot-19B-A3B-261023-MLX-rco-role-4.5bpw / mei | d67be3456120 / 5d0d215cdc89 | heldout / model_card | completed | 3/3 | 3 | 0 | 237.14 |
| 20261101T215954Z-d263a1bb | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | b818e1ac3f0b / 4bec7d1f85c3 | heldout / thinking | completed | 3/3 | 3 | 0 | 108.89 |
| 20261102T003215Z-e3f5500d | kapitsaprime/Clover-35B-A3B-Preview-MLX-4bit / kapitsa-metal | ec76e56af9e4 / 6fea0c2a3c91 | heldout / diffusion-greedy | completed | 3/3 | 2 | 0 | 197.83 |
| 20261102T010429Z-a2cd6cb4 | kapitsaprime/Clover-35B-A3B-Preview-MLX-4bit / kapitsa-metal | 3bdcc8add765 / e9c8b1432f6f | heldout / diffusion-greedy | completed | 3/3 | 2 | 0 | 211.97 |
| 20261102T012748Z-fc4bfc6b | Tostibrown/Groot-19B-A3B-261023-rco-role-4.5bpw-textonly / mei | 536e083ca5f0 / 501fa1be08da | heldout / model_card | completed | 3/3 | 3 | 0 | 240.55 |
| 20261102T014734Z-e8790c6b | bartowski/Logics-MLLM_Logics-SWE-Qwen3.6-35B-A3B-GGUF:IQ4_XS / llama.cpp | 0a82b37aa304 / 0da8dd57591a | heldout / thinking | completed | 3/3 | 3 | 0 | 143.25 |

Scores require matching task/tool/validator and release identities. Partial runs are never a complete-model score.

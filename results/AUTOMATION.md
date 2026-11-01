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

Scores require matching task/tool/validator and release identities. Partial runs are never a complete-model score.

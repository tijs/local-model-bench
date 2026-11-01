# Ornith matched v9 reference result

Household `20261101T211134Z-a1e01211`: **9/12**.
Python `20261101T211729Z-8acde4a3`: **2/3**.
Unchanged config `configs/capacity-v8-20261101/ornith.yaml`, released v9.1 method.
Completed native admission and both tracks in 669.805 seconds (11m 10s),
excluding the 30-second baseline. Health/startup wait was 18.1 seconds.
All 132 pressure samples were normal, with no swap growth.

Household failures:

- Multipart capture used an invented routing operation ID. The domain denied it;
  later successful repair/retries do not erase the invalid attempted mutation.
- Grounded retrieval repeated the deleted code while describing its prior source.
  The task forbids reusing that deleted source in an answer.
- Routine scheduling used weekday indices inconsistent with the explicit schedule.

Reminder repair produced a correct final script but initially sent an unsupported
`name` field to `write_script`. That is a model-emitted schema violation, preserved
in the API and tool journal. It was later repaired; the invalid call remains part
of the grade. All submitted scripts independently produced correct outputs on
all four visible/unseen variants. A Python contract pass requires correct tool
use as well as eventual code correctness.

All 12 household grades reproduced and API tool arguments matched journals.
No critical boundary failure or accepted unauthorized mutation was recorded.
No benchmark/API transformation defect was found in these failures. Preserve
the earlier v8 9/12 + 2/3 result too: identical counts do not imply identical
trajectories or failures, and one sample does not establish superiority.

All four aligned shards, five sidecars and model config were rehashed against
preserved provenance and matched (10 files). Logs copied before teardown.
The owned server stopped and port 8024 is free. Inventoried and removed
7,675,657,890 bytes of owned KV cache. No model weights were removed.

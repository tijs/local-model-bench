"""The header inventory rejects corrupt or misindexed expert metadata."""

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "artifacts/mei-stable-qualification-20261102"
    ),
)
from inspect_affine_headers import inspect


class AffineHeaderInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.name = "language_model.model.layers.0.mlp.switch_mlp.gate_proj.weight"
        (self.root / "config.json").write_text(
            json.dumps(
                {
                    "model_type": "qwen3_5_moe",
                    "text_config": {
                        "num_hidden_layers": 1,
                        "num_experts": 2,
                        "num_experts_per_tok": 1,
                        "hidden_size": 8,
                        "moe_intermediate_size": 8,
                    },
                }
            )
        )
        (self.root / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {self.name: "part.safetensors"}})
        )
        self.write_shard([0, 16], 16)

    def write_shard(self, offsets, payload_size):
        header = json.dumps(
            {self.name: {"data_offsets": offsets, "dtype": "U32", "shape": [2, 2, 1]}}
        ).encode()
        (self.root / "part.safetensors").write_bytes(
            struct.pack("<Q", len(header)) + header + bytes(payload_size)
        )

    def test_inventory_reports_payload_and_real_file_offset(self):
        data = inspect(self.root)
        self.assertEqual(data["routed_tensor_bytes"], 16)
        self.assertEqual(data["routed_tensor_count"], 1)
        entry = data["routed"][self.name]
        self.assertEqual(
            entry["absolute_offset"],
            (self.root / "part.safetensors").stat().st_size - 16,
        )
        self.assertEqual(entry["offset_mod_16384"], entry["absolute_offset"] % 16384)

    def test_rejects_truncated_payload_and_misindexed_tensor(self):
        self.write_shard([0, 16], 15)
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            inspect(self.root)
        self.write_shard([0, 16], 16)
        (self.root / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {self.name: "wrong.safetensors"}})
        )
        with self.assertRaisesRegex(ValueError, "index mismatch"):
            inspect(self.root)


if __name__ == "__main__":
    unittest.main()

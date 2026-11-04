"""Check page-rounded expert buffer estimates without reading model payloads."""

import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "artifacts/mei-stable-qualification-20261102"
    ),
)
from estimate_affine_mapping import UINT64_MAX, estimate


class AffineMappingEstimateTests(unittest.TestCase):
    def inventory(self):
        routed = {}
        for projection in ("gate_proj", "up_proj", "down_proj"):
            for suffix in ("weight", "scales", "biases"):
                name = f"language_model.model.layers.0.mlp.switch_mlp.{projection}.{suffix}"
                routed[name] = {"shape": [2, 1, 1], "bytes": 16, "absolute_offset": 15}
        return {"directory": "fixture", "experts": 2, "layers": 1, "routed": routed}

    def test_page_rounding_varies_by_expert(self):
        result = estimate(self.inventory(), 16)
        self.assertEqual(result["minimum_bytes"], 9 * 16)
        self.assertEqual(result["maximum_bytes"], 9 * 32)
        self.assertEqual(result["maximum_example"], {"layer": 0, "expert": 0})

    def test_missing_region_and_offset_overflow_are_rejected(self):
        data = self.inventory()
        data["routed"].pop(next(iter(data["routed"])))
        with self.assertRaisesRegex(ValueError, "nine"):
            estimate(data, 16)
        data = self.inventory()
        next(iter(data["routed"].values()))["absolute_offset"] = UINT64_MAX
        with self.assertRaisesRegex(ValueError, "overflow"):
            estimate(data, 16)


if __name__ == "__main__":
    unittest.main()

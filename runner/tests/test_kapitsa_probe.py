import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from probe_kapitsa import REQUIRED, diagnostic_succeeded


class KapitsaProbeTests(unittest.TestCase):
    def test_only_complete_real_diffusion_evidence_can_pass(self):
        good = {"status": "passed", "decoder_verified": "block diffusion",
                "probes": {name: {"status": "passed"} for name in REQUIRED}}
        cases = [
            (good, True),
            (good | {"decoder_verified": "self-speculative"}, False),
            (good | {"status": "running"}, False),
            (good | {"probes": {}}, False),
            (good | {"probes": good["probes"] | {"dependent_continuation": {"status": "failed"}}}, False),
            (good | {"probes": []}, False),
            ([], False),
        ]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for data, expected in cases:
                with self.subTest(data=data):
                    (root / "probe.json").write_text(json.dumps(data))
                    self.assertEqual(diagnostic_succeeded(root), expected)

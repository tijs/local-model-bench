"""Reject malformed Mach-O proof inputs and detect altered executable bytes."""

import hashlib
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "artifacts/mei-stable-qualification-20261102/prepare_inspection.py"
)
SPEC = importlib.util.spec_from_file_location("inspection_preparation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
inspection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspection)
sys.path.insert(0, str(SCRIPT.parent))
import run_inspection


def fixture(payload=b"code"):
    header = struct.pack("<IiiIIIII", 0xFEEDFACF, 0x100000C, 0, 2, 1, 152, 0, 0)
    segment = struct.pack(
        "<II16sQQQQiiII", 0x19, 152, b"__TEXT", 0, 4, 184, 4, 7, 5, 1, 0
    )
    section = struct.pack(
        "<16s16sQQIIIIIIII",
        b"__text",
        b"__TEXT",
        0,
        len(payload),
        184,
        2,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    return header + segment + section + payload


class BinaryProofTests(unittest.TestCase):
    def test_task_snapshot_rejects_actual_false_green_attachment_result(self):
        root = SCRIPT.parent
        self.assertFalse(
            run_inspection.swift_snapshot_valid(
                0,
                (root / "swift-inspect-tool-check-v2.stdout").read_text(),
                (root / "swift-inspect-tool-check-v2.stderr").read_text(),
            )
        )
        actual = (root / "swift-inspect-tool-check-v3.stdout").read_text()
        self.assertTrue(run_inspection.swift_snapshot_valid(0, actual, ""))
        self.assertFalse(run_inspection.swift_snapshot_valid(1, actual, ""))
        self.assertFalse(run_inspection.swift_snapshot_valid(0, "TASKS\nTHREADS\n", ""))

    def test_sections_hash_actual_payload_and_detect_changes(self):
        original = inspection.sections(fixture())
        self.assertEqual(
            original["__TEXT:__text"]["sha256"], hashlib.sha256(b"code").hexdigest()
        )
        self.assertEqual(original["__TEXT:__text"]["size"], 4)
        self.assertNotEqual(original, inspection.sections(fixture(b"edit")))

    def test_truncation_and_wrong_format_fail_closed(self):
        good = fixture()
        for bad in (b"", b"not a Mach-O", good[:31], good[:50], good[:-1]):
            with self.assertRaises(ValueError):
                inspection.sections(bad)


if __name__ == "__main__":
    unittest.main()

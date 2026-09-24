"""No-network unit tests for the probe_mei tokenizer selection logic.

Run: uv run --locked python -m unittest runner.tests.test_probe_mei -v
   (or the repo-wide: uv run --locked python -m unittest discover -s runner/tests -v)

Covers the narrowly scoped Bonsai tokenizer override used by the exact-token
context-cap probe: only a directory whose own metadata carries both halves of
the staged fingerprint (config.json model_type `prism_hadamard_qwen35` AND
tokenizer_config.json tokenizer_class `Qwen2Tokenizer`) gets the explicit
Qwen2 + fix_mistral_regex=True load; an ordinary tokenizer directory gets
the historical plain AutoTokenizer behavior. No tokenizer/model is ever
loaded and no network is touched: the load-routing tests stub the
`transformers` module in sys.modules with recording fakes.
"""
import contextlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import probe_mei  # noqa: E402


def _make_dir(root: Path, name: str, config, tokenizer_config) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    if config is not None:
        raw = config if isinstance(config, str) else json.dumps(config)
        (directory / "config.json").write_text(raw)
    if tokenizer_config is not None:
        raw = tokenizer_config if isinstance(tokenizer_config, str) else json.dumps(tokenizer_config)
        (directory / "tokenizer_config.json").write_text(raw)
    return directory


class _FakeQwen2Tokenizer:
    calls = []
    fail = False

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        cls.calls.append((args, kwargs))
        if cls.fail:
            raise RuntimeError("synthetic direct-load failure")
        return "qwen2-loaded"


class _FakeAutoTokenizer:
    calls = []

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        cls.calls.append((args, kwargs))
        return "generic-loaded"


@contextlib.contextmanager
def _patched_transformers():
    """Stub the transformers module with recording fakes for one call."""
    original = sys.modules.get("transformers")
    fake = types.ModuleType("transformers")
    setattr(fake, "Qwen2Tokenizer", _FakeQwen2Tokenizer)
    setattr(fake, "AutoTokenizer", _FakeAutoTokenizer)
    _FakeQwen2Tokenizer.calls = []
    _FakeAutoTokenizer.calls = []
    sys.modules["transformers"] = fake
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop("transformers", None)
        else:
            sys.modules["transformers"] = original


class MetadataSelectionTests(unittest.TestCase):
    def test_bonsai_metadata_gets_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "bonsai",
                config={"model_type": "prism_hadamard_qwen35"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            self.assertEqual(
                probe_mei.tokenizer_override_kwargs(directory),
                {"fix_mistral_regex": True},
            )

    def test_override_kwargs_are_exactly_fix_mistral_regex(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "bonsai",
                config={"model_type": "prism_hadamard_qwen35"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            self.assertEqual(
                probe_mei.tokenizer_override_kwargs(directory),
                {"fix_mistral_regex": True},
            )
            kwargs = probe_mei.tokenizer_override_kwargs(directory)
            if kwargs is None:
                self.fail("expected override kwargs")
            self.assertNotIn("trust_remote_code", kwargs)

    def test_ordinary_qwen2_directory_gets_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "ordinary",
                config={"model_type": "qwen2"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(directory))

    def test_model_type_alone_is_not_enough(self):
        # Same custom model_type but a different tokenizer class: default-off.
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "other-class",
                config={"model_type": "prism_hadamard_qwen35"},
                tokenizer_config={"tokenizer_class": "Qwen3Tokenizer"},
            )
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(directory))

    def test_tokenizer_class_alone_is_not_enough(self):
        # Same Qwen2 tokenizer class but an ordinary model_type: default-off.
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "generic-qwen2",
                config={"model_type": "qwen2"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(directory))

    def test_missing_metadata_gets_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            no_config = _make_dir(root, "no-config", config=None, tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"})
            no_tokenizer_config = _make_dir(root, "no-tok-config", config={"model_type": "prism_hadamard_qwen35"}, tokenizer_config=None)
            empty = root / "empty"
            empty.mkdir()
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(no_config))
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(no_tokenizer_config))
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(empty))

    def test_malformed_metadata_gets_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_json = _make_dir(
                root, "bad-json",
                config="{not json",
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            list_json = _make_dir(
                root, "list-json",
                config=["prism_hadamard_qwen35"],
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(bad_json))
            self.assertIsNone(probe_mei.tokenizer_override_kwargs(list_json))


class LoadRoutingTests(unittest.TestCase):
    def test_special_path_uses_qwen2_contract_with_override_kwargs(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "bonsai",
                config={"model_type": "prism_hadamard_qwen35"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            with _patched_transformers():
                loaded = probe_mei.load_exact_prompt_tokenizer(directory)
                self.assertEqual(loaded, "qwen2-loaded")
                (args, kwargs), = _FakeQwen2Tokenizer.calls
                self.assertEqual(args, (directory,))
                self.assertEqual(kwargs, {"fix_mistral_regex": True})
                self.assertEqual(_FakeAutoTokenizer.calls, [])  # generic path not used

    def test_generic_path_uses_plain_auto_tokenizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "ordinary",
                config={"model_type": "qwen2"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            with _patched_transformers():
                loaded = probe_mei.load_exact_prompt_tokenizer(directory)
                self.assertEqual(loaded, "generic-loaded")
                self.assertEqual(_FakeQwen2Tokenizer.calls, [])
                (args, kwargs), = _FakeAutoTokenizer.calls
                self.assertEqual(args, (directory,))
                self.assertEqual(kwargs, {"trust_remote_code": False})

    def test_special_path_failure_is_surfaced_not_routed_to_generic(self):
        # A matched directory whose explicit Qwen2 load fails must surface a
        # RuntimeError with the original exception chained — never silently
        # fall back to AutoTokenizer, which would reintroduce the warnings
        # while the probe appears to work.
        with tempfile.TemporaryDirectory() as tmp:
            directory = _make_dir(
                Path(tmp), "bonsai",
                config={"model_type": "prism_hadamard_qwen35"},
                tokenizer_config={"tokenizer_class": "Qwen2Tokenizer"},
            )
            with _patched_transformers():
                _FakeQwen2Tokenizer.fail = True
                try:
                    with self.assertRaises(RuntimeError) as raised:
                        probe_mei.load_exact_prompt_tokenizer(directory)
                    self.assertIsInstance(raised.exception.__cause__, RuntimeError)
                    self.assertIn("Qwen2Tokenizer", str(raised.exception))
                    self.assertIn("prism_hadamard_qwen35", str(raised.exception))
                    self.assertIn("fix_mistral_regex", str(raised.exception))
                    self.assertEqual(_FakeAutoTokenizer.calls, [])  # no silent fallback
                finally:
                    _FakeQwen2Tokenizer.fail = False


if __name__ == "__main__":
    unittest.main()

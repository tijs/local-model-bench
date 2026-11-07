"""Resolve the host's staging directory for benchmark model weights."""

import argparse
import os
from pathlib import Path

DEFAULT_MODEL_ROOT = "/Volumes/Expansion/local-model-bench"


def model_root(engine: str) -> Path:
    if engine not in {"mei", "gguf"}:
        raise ValueError(f"unsupported model store: {engine}")
    setting = (
        Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        / "local-model-bench/model-root"
    )
    override = os.environ.get("LOCAL_MODEL_BENCH_MODEL_ROOT")
    if override is None:
        try:
            override = setting.read_text().strip()
        except FileNotFoundError:
            override = DEFAULT_MODEL_ROOT
    base = Path(override)
    if not base.is_absolute() or "\n" in override:
        raise ValueError("model-root must name one absolute directory")
    if base.parts[1:2] == ("Volumes",) and (
        len(base.parts) < 3 or not Path(*base.parts[:3]).is_mount()
    ):
        raise ValueError(f"configured model volume is not mounted: {base}")
    store = base / f"{engine}-models"
    if not store.is_dir():
        raise ValueError(f"configured model store is unavailable: {store}")
    return store


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("mei", "gguf"))
    args = parser.parse_args()
    try:
        print(model_root(args.engine))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

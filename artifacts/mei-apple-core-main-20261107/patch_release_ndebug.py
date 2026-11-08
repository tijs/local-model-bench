"""Define NDEBUG consistently for C++ targets that share private MLX types."""

import argparse
import subprocess
from pathlib import Path

FLAG = '.define("NDEBUG", .when(configuration: .release)),'


def original_manifest(checkout):
    return subprocess.check_output(
        ["git", "-C", str(checkout), "show", "HEAD:Package.swift"], text=True
    )


def release_manifest(original, *, graph_shim=True):
    core = "    cxxSettings: cxxSettings + [\n"
    if original.count(core) != 1:
        raise ValueError("unexpected Cmlx manifest layout")
    changed = original.replace(core, core + f"        {FLAG}\n", 1)
    if graph_shim:
        target = '            name: "CmlxGraphShim",\n'
        settings = "            cxxSettings: [\n"
        if changed.count(target) != 1:
            raise ValueError("unexpected CmlxGraphShim manifest layout")
        start = changed.index(target)
        end = changed.index("        ),\n", start)
        block = changed[start:end]
        if block.count(settings) != 1:
            raise ValueError("unexpected CmlxGraphShim C++ settings")
        changed = (
            changed[:start]
            + block.replace(settings, settings + f"                {FLAG}\n", 1)
            + changed[end:]
        )
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    checkout = parser.parse_args().checkout.resolve(strict=True)
    path = checkout / "Package.swift"
    original = original_manifest(checkout)
    changed = release_manifest(original)
    existing = path.read_text()
    if existing == changed:
        return
    if existing not in (original, release_manifest(original, graph_shim=False)):
        raise ValueError("refuse to overwrite an unexpected manifest edit")
    path.chmod(path.stat().st_mode | 0o200)
    path.write_text(changed)


if __name__ == "__main__":
    main()

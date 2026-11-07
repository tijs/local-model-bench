"""Verify the published Mei release and installed Homebrew bytes before scoring."""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

PREP = Path(__file__).resolve().parent
QUALIFICATION = PREP.parent / "mei-upstream-qualification-20261106"
VERSION = "0.11.0"
TAG = f"v{VERSION}"
BUNDLE = f"mei-{VERSION}-macos-arm64"
ARCHIVE = f"{BUNDLE}.tar.gz"
RELEASE = f"https://github.com/tijs/mei/releases/tag/{TAG}"
ASSET = f"https://github.com/tijs/mei/releases/download/{TAG}/{ARCHIVE}"


def read(command, *, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def remote_revision(directory, ref):
    rows = read(["git", "ls-remote", "origin", ref], cwd=directory).splitlines()
    require(len(rows) == 1 and rows[0].split()[1] == ref, f"missing remote ref {ref}")
    return rows[0].split()[0]


def archive_identity(archive, checksum, candidate):
    match = re.fullmatch(r"([0-9a-f]{64}) [ *](\S+)", checksum.read_text().strip())
    require(match is not None and match[2] == ARCHIVE, "invalid published checksum")
    actual = digest(archive)
    require(actual == match[1], "published archive checksum mismatch")
    with tarfile.open(archive, "r:gz") as package:
        for filename, key in (
            ("mei", "binary_sha256"),
            ("mlx.metallib", "metallib_sha256"),
        ):
            name = f"{BUNDLE}/bin/{filename}"
            members = [member for member in package.getmembers() if member.name == name]
            require(
                len(members) == 1 and members[0].isfile(),
                f"missing or duplicate {name}",
            )
            stream = package.extractfile(members[0])
            require(stream is not None, f"cannot read {name}")
            with stream:
                require(
                    hashlib.file_digest(stream, "sha256").hexdigest() == candidate[key],
                    f"published {filename} differs from qualified bytes",
                )
    return actual


def verify(qualification, source, tap):
    candidate = json.loads(
        (QUALIFICATION / f"{qualification}-artifact.json").read_text()
    )
    metadata = json.loads(
        read(
            [
                "gh",
                "release",
                "view",
                TAG,
                "--repo",
                "tijs/mei",
                "--json",
                "tagName,publishedAt,url,isDraft,isPrerelease,assets",
            ]
        )
    )
    require(
        metadata["tagName"] == TAG
        and metadata["url"] == RELEASE
        and not metadata["isDraft"]
        and not metadata["isPrerelease"]
        and bool(metadata["publishedAt"]),
        "GitHub release is not published stable",
    )
    names = {item["name"] for item in metadata["assets"]}
    require({ARCHIVE, f"{ARCHIVE}.sha256"} <= names, "GitHub release assets missing")

    tag = read(["git", "rev-parse", f"{TAG}^{{commit}}"], cwd=source)
    require(
        read(["git", "rev-parse", "HEAD"], cwd=source) == tag,
        "source worktree is not at tag",
    )
    require(
        not read(["git", "status", "--porcelain"], cwd=source),
        "source worktree is dirty",
    )
    tag_ref = f"refs/tags/{TAG}"
    require(
        read(["git", "rev-parse", tag_ref], cwd=source)
        == remote_revision(source, tag_ref),
        "GitHub tag mismatch",
    )
    main = remote_revision(source, "refs/heads/main")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", tag, main], cwd=source, check=True
    )
    subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            candidate["source_revision"],
            tag,
            "--",
            "Sources",
            "Package.swift",
            "Package.resolved",
        ],
        cwd=source,
        check=True,
    )
    lock = json.loads((source / "Package.resolved").read_text())
    vmlx = [
        p["state"]["revision"] for p in lock["pins"] if p["identity"] == "vmlx-swift"
    ]
    require(vmlx == [candidate["vmlx_revision"]], "published dependency pin mismatch")

    with tempfile.TemporaryDirectory(prefix="mei-release-verification-") as tmp:
        directory = Path(tmp)
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                TAG,
                "--repo",
                "tijs/mei",
                "--dir",
                tmp,
                "--pattern",
                ARCHIVE,
                "--pattern",
                f"{ARCHIVE}.sha256",
            ],
            check=True,
        )
        sha = archive_identity(
            directory / ARCHIVE, directory / f"{ARCHIVE}.sha256", candidate
        )

    tap_main = remote_revision(tap, "refs/heads/main")
    formula = read(["git", "show", f"{tap_main}:Formula/mei.rb"], cwd=tap)
    require(
        re.findall(r'^\s*url "([^"]+)"', formula, re.MULTILINE) == [ASSET],
        "remote tap URL mismatch",
    )
    require(
        re.findall(r'^\s*sha256 "([^"]+)"', formula, re.MULTILINE) == [sha],
        "remote tap checksum mismatch",
    )
    installed = Path(read(["brew", "--prefix", "tijs/tap/mei"])).resolve()
    binary = installed / "libexec/mei"
    require(
        read([str(installed / "bin/mei"), "--version"]) == f"mei {VERSION}",
        "installed wrapper version mismatch",
    )
    require(
        read([str(binary), "--version"]) == f"mei {VERSION}",
        "installed binary version mismatch",
    )
    require(
        digest(binary) == candidate["binary_sha256"], "installed executable mismatch"
    )
    require(
        digest(binary.with_name("mlx.metallib")) == candidate["metallib_sha256"],
        "installed Metal library mismatch",
    )
    return {
        "version": VERSION,
        "release": RELEASE,
        "released_at": metadata["publishedAt"],
        "archive_sha256": sha,
        "source_revision": tag,
        "remote_main": main,
        "source_worktree": str(source),
        "vmlx_revision": candidate["vmlx_revision"],
        "core_revision": candidate["core_revision"],
        "qualification_campaign": qualification,
        "runtime_tested_source_revision": candidate["source_revision"],
        "binary_sha256": candidate["binary_sha256"],
        "metallib_sha256": candidate["metallib_sha256"],
        "remote_tap_main": tap_main,
        "installed_binary": str(binary),
        "published_asset_and_installed_artifact_verified": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qualification", choices=("apple-main", "attention-selector"), required=True
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="clean detached release source checkout",
    )
    parser.add_argument(
        "--tap", type=Path, required=True, help="tap worktree with current main object"
    )
    parser.add_argument(
        "--output", type=Path, default=PREP / "verified-release-delivery.json"
    )
    options = parser.parse_args()
    if options.output.exists():
        parser.error("refuse to replace an existing delivery receipt")
    receipt = verify(
        options.qualification, options.source.resolve(), options.tap.resolve()
    )
    with options.output.open("x") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()

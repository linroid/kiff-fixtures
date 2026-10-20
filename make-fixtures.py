"""Writes the release assets of linroid/kiff-fixtures into DIR/<tag>/.

Every byte comes from a seeded generator, so running this again writes identical files. Each
version is its parent plus a small mutation, which keeps a patch between neighbours much smaller
than its target, the way consecutive builds of a real app are.

    python3 make-fixtures.py dist
"""

import random
import sys
import zipfile
from pathlib import Path

# (tag, parent tag), in the order the releases are published. v1.2.1 is a hotfix of v1.2.0
# published after v1.3.0, and v1.4.0-rc.1 is a prerelease.
VERSIONS = [
    ("v1.0.0", None),
    ("v1.1.0", "v1.0.0"),
    ("v1.2.0", "v1.1.0"),
    ("v1.3.0", "v1.2.0"),
    ("v1.2.1", "v1.2.0"),
    ("v1.4.0-rc.1", "v1.3.0"),
]

# Releases that leave tool-<version>.bin out, so a source without the file is exercised.
WITHOUT_TOOL = {"v1.1.0"}

ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def mutate(data: bytes, seed: str) -> bytes:
    rng = random.Random(seed)
    out = bytearray(data)
    for _ in range(8):
        pos = rng.randrange(len(out) - 32)
        out[pos:pos + 32] = rng.randbytes(32)
    for _ in range(2):
        pos = rng.randrange(len(out))
        out[pos:pos] = rng.randbytes(200)
    pos = rng.randrange(len(out) - 100)
    del out[pos:pos + 100]
    return bytes(out)


def lineage(name: str, size: int) -> dict:
    """The bytes of one evolving blob at every version."""
    blobs = {}
    for tag, parent in VERSIONS:
        if parent is None:
            blobs[tag] = random.Random(f"{name}:base").randbytes(size)
        else:
            blobs[tag] = mutate(blobs[parent], f"{name}:{tag}")
    return blobs


def write_zip(path: Path, entries: list) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data, method in entries:
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = method
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)


def main(out: Path) -> None:
    dex = lineage("classes.dex", 48 * 1024)
    lib = lineage("libfoo.so", 64 * 1024)
    data = lineage("data.bin", 16 * 1024)
    desktop = lineage("desktop.jar", 40 * 1024)
    tool = lineage("tool.bin", 96 * 1024)

    for tag, _ in VERSIONS:
        version = tag[1:]
        release = out / tag
        release.mkdir(parents=True, exist_ok=True)

        manifest = (
            '<manifest package="com.example.fixture" '
            f'android:versionName="{version}"/>\n'
        ).encode()
        notes = f"Fixture build {version}.\n".encode() * 40
        write_zip(release / f"app-{version}.apk", [
            ("AndroidManifest.xml", manifest, zipfile.ZIP_DEFLATED),
            ("classes.dex", dex[tag], zipfile.ZIP_STORED),
            ("lib/arm64-v8a/libfoo.so", lib[tag], zipfile.ZIP_STORED),
            ("assets/data.bin", data[tag], zipfile.ZIP_STORED),
            ("res/raw/notes.txt", notes, zipfile.ZIP_DEFLATED),
        ])
        write_zip(release / f"desktop-{version}.zip", [
            ("desktop/lib/desktop.jar", desktop[tag], zipfile.ZIP_STORED),
            ("desktop/VERSION", f"{version}\n".encode(), zipfile.ZIP_STORED),
        ])
        if tag not in WITHOUT_TOOL:
            (release / f"tool-{version}.bin").write_bytes(tool[tag])
        # Unrelated bytes every time, so its patches are too large to keep.
        noise = random.Random(f"noise:{tag}").randbytes(32 * 1024)
        (release / f"noise-{version}.bin").write_bytes(noise)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: make-fixtures.py DIR")
    main(Path(sys.argv[1]))

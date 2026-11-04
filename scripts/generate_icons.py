#!/usr/bin/env python3
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "logo.png"
ASSETS = ROOT / "assets"
ROUNDED = ASSETS / "logo-rounded.png"

ICNS_TYPES = {
    b"ic07": 128,
    b"ic08": 256,
    b"ic09": 512,
    b"ic10": 1024,
    b"ic11": 32,
    b"ic12": 64,
    b"ic13": 256,
    b"ic14": 512,
}


def magick(*args, capture=False):
    result = subprocess.run(
        ["magick", *[str(arg) for arg in args]],
        check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
    )
    return result.stdout


def generate_rounded_png(size=1024, radius=184):
    mask = f"roundrectangle 0,0 {size - 1},{size - 1} {radius},{radius}"
    magick(
        SOURCE,
        "-background",
        "none",
        "-gravity",
        "center",
        "-filter",
        "Lanczos",
        "-resize",
        f"{size}x{size}",
        "-extent",
        f"{size}x{size}",
        "(",
        "-size",
        f"{size}x{size}",
        "xc:none",
        "-fill",
        "white",
        "-draw",
        mask,
        ")",
        "-alpha",
        "set",
        "-compose",
        "DstIn",
        "-composite",
        ROUNDED,
    )


def generate_ico():
    magick(
        ROUNDED,
        "-define",
        "icon:auto-resize=256,128,64,48,32,16",
        ASSETS / "logo.ico",
    )


def generate_icns():
    entries = []
    for icon_type, size in ICNS_TYPES.items():
        payload = magick(
            ROUNDED,
            "-resize",
            f"{size}x{size}",
            "PNG32:-",
            capture=True,
        )
        entries.append((icon_type, payload))

    toc_length = 8 + 8 * len(entries)
    total_length = 8 + toc_length + sum(8 + len(payload) for _, payload in entries)

    with open(ASSETS / "logo.icns", "wb") as icns:
        icns.write(b"icns")
        icns.write(struct.pack(">I", total_length))
        icns.write(b"TOC ")
        icns.write(struct.pack(">I", toc_length))
        for icon_type, payload in entries:
            icns.write(icon_type)
            icns.write(struct.pack(">I", 8 + len(payload)))
        for icon_type, payload in entries:
            icns.write(icon_type)
            icns.write(struct.pack(">I", 8 + len(payload)))
            icns.write(payload)


def main():
    if not SOURCE.exists():
        print(f"Missing source logo: {SOURCE}", file=sys.stderr)
        return 1

    ASSETS.mkdir(exist_ok=True)
    generate_rounded_png()
    generate_ico()
    generate_icns()
    return 0


if __name__ == "__main__":
    sys.exit(main())

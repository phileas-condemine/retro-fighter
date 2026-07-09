"""Generate dummy colored-rectangle PNGs standing in for real character
parts, so the Blender pipeline (rig, animate, render, export) can be built
and tested end-to-end before any real art exists.

Not part of the game or the art pipeline's output -- purely a development
fixture. Real parts (from ChatGPT/DALL-E, see
assets_source/fighters/PARTS_SPEC.md) go through the exact same pipeline
unchanged; only the source images differ.

Usage:
    python blender/make_placeholder_parts.py --out blender/test_fixtures/rose_kunoichi_v2/parts

Requires Pillow (not a project dependency, dev-only -- same caveat as
tools/sprites/validate_manifest.py).
"""
from __future__ import annotations

import argparse
import colorsys
from pathlib import Path

from PIL import Image, ImageDraw

from parts_spec import PARTS

# Limb parts render as a tall rectangle (bone-length-ish proportions), blob
# parts as a roughly square one -- just enough shape variety to visually
# sanity-check the rig assembles into a recognizable silhouette.
SIZE_BY_ASPECT = {
    "limb": (80, 220),
    "blob": (140, 140),
}


def make_part_image(index: int, total: int, size: tuple[int, int], label: str) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    hue = index / max(total, 1)
    r, g, b = (round(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.65, 0.9))
    margin = 6
    draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=10,
                            fill=(r, g, b, 230), outline=(0, 0, 0, 255), width=3)
    draw.line([(width // 2, margin), (width // 2, height - margin)], fill=(0, 0, 0, 120), width=1)
    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="output parts/ directory")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for i, part in enumerate(PARTS):
        size = SIZE_BY_ASPECT[part.aspect]
        img = make_part_image(i, len(PARTS), size, part.name)
        out_path = args.out / f"{part.name}.png"
        img.save(out_path)
        print(f"wrote {out_path} ({size[0]}x{size[1]}, phase {part.phase})")

    print(f"\n{len(PARTS)} placeholder parts written to {args.out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

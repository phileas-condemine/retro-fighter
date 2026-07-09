"""Chroma-key a green-screen PNG to RGBA, with despill.

Usage: py tools/sprites/chroma_key.py <input.png> <output.png> [--thresh N]

Dev-only tool (see the same caveat as tools/sprites/validate_manifest.py) —
not a project dependency, requires Pillow (`py -c "import PIL"`).
"""
import sys
from pathlib import Path

from PIL import Image


def chroma_key(im: Image.Image, thresh: int = 60) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # Green-dominant pixel -> transparent.
            if g > r + thresh and g > b + thresh:
                px[x, y] = (r, g, b, 0)
            elif g > r and g > b:
                # Despill: pull green channel down toward the average of r/b
                # so a residual green fringe doesn't survive on edge pixels.
                avg = (r + b) // 2
                px[x, y] = (r, avg, b, a)
    return im


def main() -> None:
    args = sys.argv[1:]
    thresh = 60
    if "--thresh" in args:
        i = args.index("--thresh")
        thresh = int(args[i + 1])
        del args[i : i + 2]
    src, dst = args
    im = Image.open(src)
    out = chroma_key(im, thresh)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    print(f"wrote {dst} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()

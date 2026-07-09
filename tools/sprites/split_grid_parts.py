"""Split a chroma-keyed RGBA parts sheet into individual named PNGs.

Finds connected components of non-transparent pixels (not a naive grid split
— generated sheets don't reliably align to equal grid cells, adjacent rows
can bleed into each other) and assigns each blob to a name by reading order
(top-to-bottom, then left-to-right within a row band). Dev-only tool,
requires Pillow + scipy.

Usage:
  py tools/sprites/split_grid_parts.py <input.png> <out_dir> \
      --names head,hair_front,hair_back,torso,pelvis,accessory_main --pad 12
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("out_dir")
    ap.add_argument("--names", required=True, help="comma-separated, reading order")
    ap.add_argument("--pad", type=int, default=12)
    ap.add_argument("--thresh", type=int, default=10)
    ap.add_argument("--rows", type=int, default=2,
                     help="number of row bands the parts are laid out in")
    args = ap.parse_args()

    im = Image.open(args.input).convert("RGBA")
    alpha = np.array(im.split()[-1])
    mask = alpha > args.thresh

    # Dilate slightly so a part's own separate strokes (e.g. hair strands)
    # merge into one component instead of splitting further.
    mask = ndimage.binary_dilation(mask, iterations=3)

    labeled, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit("no non-transparent components found")

    objs = ndimage.find_objects(labeled)
    blobs = []
    for idx, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        if (y1 - y0) < 15 or (x1 - x0) < 15:
            continue  # noise speck
        blobs.append((y0, x0, y1, x1))

    # Group into `rows` row bands by y-center: sort by y-center, then split
    # at the (rows - 1) largest gaps between consecutive centers. Parts in
    # the same row can have very different vertical extents/offsets (e.g. a
    # sash's knot sits lower in its cell than a torso's collar), so a fixed
    # pixel threshold on y0 is unreliable — the biggest gaps in sorted
    # y-center are a much more robust signal of an actual row break.
    def y_center(b):
        y0, _, y1, _ = b
        return (y0 + y1) / 2

    blobs.sort(key=y_center)
    n_breaks = args.rows - 1
    if n_breaks > 0 and len(blobs) > args.rows:
        gaps = [
            (y_center(blobs[i + 1]) - y_center(blobs[i]), i)
            for i in range(len(blobs) - 1)
        ]
        gaps.sort(reverse=True)
        break_after = sorted(i for _, i in gaps[:n_breaks])
    else:
        break_after = []

    bands, start = [], 0
    for i in break_after:
        bands.append(blobs[start:i + 1])
        start = i + 1
    bands.append(blobs[start:])

    for band in bands:
        band.sort(key=lambda b: (b[1] + b[3]) / 2)  # left-to-right by x-center
    ordered = [b for band in bands for b in band]

    names = args.names.split(",")
    if len(names) != len(ordered):
        print(f"WARNING: found {len(ordered)} blobs but got {len(names)} names")
        print("blob bounding boxes (y0,x0,y1,x1):", ordered)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    w, h = im.size
    for name, (y0, x0, y1, x1) in zip(names, ordered):
        if not name:
            continue
        x0 = max(0, x0 - args.pad)
        y0 = max(0, y0 - args.pad)
        x1 = min(w, x1 + args.pad)
        y1 = min(h, y1 + args.pad)
        part = im.crop((x0, y0, x1, y1))
        dst = out_dir / f"{name}.png"
        part.save(dst)
        print(f"wrote {dst} ({part.width}x{part.height}) from box ({x0},{y0},{x1},{y1})")


if __name__ == "__main__":
    main()

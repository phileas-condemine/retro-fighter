"""Convenience wrapper around `blender -b --python pipeline.py -- <args>`,
so invoking the pipeline doesn't require remembering Blender's own CLI
flags or where it's installed (see find_blender.py).

Usage:
    python blender/run_pipeline.py --fighter rose_kunoichi \
        --parts-dir assets_source/fighters/rose_kunoichi_v2/parts \
        --out assets/fighters/v2/rose_kunoichi \
        --anims idle,walk,punch_mid

All arguments are forwarded as-is to pipeline.py (see its --help). Paths
are resolved to absolute before being handed to Blender -- relative paths
passed straight through have been observed to resolve inconsistently
depending on Blender's internal notion of "current directory" for a
freshly reset, unsaved scene.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from find_blender import find_blender

HERE = Path(__file__).resolve().parent
PATH_LIKE_FLAGS = {"--parts-dir", "--out"}


def resolve_paths(args: list[str]) -> list[str]:
    resolved = []
    take_next_as_path = False
    for arg in args:
        if take_next_as_path:
            resolved.append(str(Path(arg).resolve()))
            take_next_as_path = False
            continue
        resolved.append(arg)
        if arg in PATH_LIKE_FLAGS:
            take_next_as_path = True
    return resolved


def main() -> int:
    blender_exe = find_blender()
    pipeline_script = HERE / "pipeline.py"
    forwarded_args = resolve_paths(sys.argv[1:])
    cmd = [blender_exe, "-b", "--python", str(pipeline_script), "--", *forwarded_args]
    print("running:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

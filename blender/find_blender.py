"""Locate the Blender executable reproducibly across machines/sessions,
instead of hardcoding an install path in every script/command.

Resolution order:
  1. BLENDER_EXE environment variable, if set.
  2. `blender` on PATH.
  3. Common Windows install locations (winget/installer default).

Usage as a script (prints the path, or exits 1 with a clear error):
    python blender/find_blender.py

Usage as a module:
    from find_blender import find_blender
    exe = find_blender()  # raises FileNotFoundError with install instructions if not found
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

CANDIDATE_GLOBS = [
    r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
]

INSTALL_HINT = (
    "Blender not found. Install it with:\n"
    "  winget install --id BlenderFoundation.Blender.LTS.4.5 --exact\n"
    "or set BLENDER_EXE to an existing install."
)


def find_blender() -> str:
    env_path = os.environ.get("BLENDER_EXE")
    if env_path and Path(env_path).is_file():
        return env_path

    on_path = shutil.which("blender")
    if on_path:
        return on_path

    for pattern in CANDIDATE_GLOBS:
        matches = sorted(Path("/").glob(pattern.lstrip("C:\\").replace("\\", "/")), reverse=True) \
            if not pattern.startswith("C:") else sorted(Path("C:/").glob(pattern[3:].replace("\\", "/")), reverse=True)
        if matches:
            return str(matches[0])

    raise FileNotFoundError(INSTALL_HINT)


if __name__ == "__main__":
    try:
        print(find_blender())
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

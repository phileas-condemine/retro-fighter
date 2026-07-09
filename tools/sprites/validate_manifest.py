#!/usr/bin/env python3
"""Validate a fighter sprite pack against the manifest contract.

See assets/fighters/CONTRACT.md for what this checks and why. Written for
the v2 (Blender) pipeline but works today against the existing ld/hd packs.

Usage:
    python tools/sprites/validate_manifest.py assets/fighters/ld/rose_kunoichi
    python tools/sprites/validate_manifest.py assets/fighters/hd/shinobi --reference assets/fighters/ld/shinobi

Pillow is used for per-frame size/RGBA checks when available, but is not a
project dependency (this is a dev-only tool, not shipped with the game) --
those specific checks are skipped with a warning if Pillow isn't installed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


def load_animations(pack_dir: Path) -> dict:
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"ERREUR: {manifest_path} introuvable")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    animations = dict(manifest.get("animations", {}))
    for ext_path in sorted(pack_dir.glob("extension_manifest*.json")):
        extension = json.loads(ext_path.read_text(encoding="utf-8"))
        animations.update(extension.get("animations_to_add", {}))
    return manifest, animations


def validate_pack(pack_dir: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest, animations = load_animations(pack_dir)

    anchor = manifest.get("anchor")
    if not anchor or "x" not in anchor or "y" not in anchor:
        errors.append("anchor manquant ou incomplet (attendu {'x': .., 'y': ..})")

    if not animations:
        errors.append("aucune animation declaree (manifest.json + extension_manifest*.json)")

    if Image is None:
        warnings.append("Pillow non installe: verification taille/RGBA des frames ignoree")

    for name, data in animations.items():
        frames = data.get("frames")
        if not frames:
            errors.append(f"{name}: aucune frame listee")
            continue
        fps = data.get("fps")
        if not isinstance(fps, (int, float)) or fps <= 0:
            errors.append(f"{name}: fps invalide ({fps!r})")
        if not isinstance(data.get("loop"), bool):
            errors.append(f"{name}: loop doit etre un booleen (trouve {data.get('loop')!r})")

        sizes: set[tuple[int, int]] = set()
        for rel_path in frames:
            if Path(rel_path).is_absolute():
                errors.append(f"{name}: chemin absolu interdit ({rel_path})")
                continue
            frame_path = pack_dir / rel_path
            if not frame_path.exists():
                errors.append(f"{name}: frame manquante sur disque: {rel_path}")
                continue
            if Image is not None:
                try:
                    with Image.open(frame_path) as img:
                        if img.mode != "RGBA":
                            warnings.append(f"{name}: {rel_path} n'est pas en RGBA (mode={img.mode})")
                        sizes.add(img.size)
                except Exception as exc:  # noqa: BLE001 - a bad frame is a validation error, not a crash
                    errors.append(f"{name}: {rel_path} illisible comme image ({exc})")
        if len(sizes) > 1:
            errors.append(f"{name}: tailles de frame incoherentes entre elles: {sorted(sizes)}")

    return errors, warnings, animations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pack_dir", type=Path, help="dossier du pack, ex: assets/fighters/ld/rose_kunoichi")
    parser.add_argument("--reference", type=Path, default=None,
                         help="pack de reference pour lister les cles d'animation manquantes "
                              "(ex: assets/fighters/ld/rose_kunoichi pour evaluer un pack hd/v2)")
    args = parser.parse_args()

    if not args.pack_dir.is_dir():
        print(f"ERREUR: {args.pack_dir} n'est pas un dossier")
        return 1

    errors, warnings, animations = validate_pack(args.pack_dir)

    if args.reference:
        if not args.reference.is_dir():
            print(f"ERREUR: --reference {args.reference} n'est pas un dossier")
            return 1
        _, _, ref_animations = validate_pack(args.reference)
        missing = sorted(set(ref_animations) - set(animations))
        if missing:
            warnings.append(
                f"cles absentes par rapport a {args.reference}: {missing} "
                "(repli automatique sur 'idle' en jeu, voir CONTRACT.md)"
            )

    for warning in warnings:
        print(f"AVERTISSEMENT: {warning}")
    for error in errors:
        print(f"ERREUR: {error}")

    print(f"\n{args.pack_dir}: {len(animations)} animation(s), {len(errors)} erreur(s), {len(warnings)} avertissement(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

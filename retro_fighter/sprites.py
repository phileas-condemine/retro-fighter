"""Loads the sprite packs under assets/fighters/ and plays their animations.

Each pack (see assets/fighters/<id>/manifest.json) is a set of named animation
clips authored facing right. A fighter facing left is drawn by flipping the
current frame at blit time (based on Fighter.facing) rather than keeping a
separate mirrored copy on disk, so a character crossing sides (e.g. via the
double jump) is always mirrored correctly no matter which side it ends up on.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FIGHTERS_DIR = ASSETS_DIR / "fighters"
PROJECTILES_DIR = ASSETS_DIR / "projectiles"


@dataclass
class AnimationClip:
    frames: list[pygame.Surface]
    fps: int
    loop: bool

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def frame_at(self, elapsed_ticks: int, tick_rate: int) -> pygame.Surface:
        elapsed_seconds = elapsed_ticks / tick_rate
        index = int(elapsed_seconds * self.fps)
        if self.loop:
            index %= self.frame_count
        else:
            index = min(index, self.frame_count - 1)
        return self.frames[index]


class FighterSpriteSet:
    """A loaded sprite pack for one fighter id (e.g. "rose_kunoichi")."""

    def __init__(self, fighter_id: str) -> None:
        root = FIGHTERS_DIR / fighter_id
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.anchor = (manifest["anchor"]["x"], manifest["anchor"]["y"])
        animation_sources = dict(manifest["animations"])

        # Extension packs (crouch, ranged attack, salto, crouch attacks, ...)
        # each ship as a patch: their own manifest just adds animations on top
        # of the base pack. There can be more than one (extension_manifest.json,
        # extension_manifest_<name>.json, ...); merge them all, sorted for a
        # deterministic order if two ever defined the same key.
        for extension_path in sorted(root.glob("extension_manifest*.json")):
            extension = json.loads(extension_path.read_text(encoding="utf-8"))
            animation_sources.update(extension["animations_to_add"])

        self.animations: dict[str, AnimationClip] = {}
        for name, data in animation_sources.items():
            frames = [pygame.image.load(str(root / path)).convert_alpha() for path in data["frames"]]
            self.animations[name] = AnimationClip(frames=frames, fps=data["fps"], loop=data["loop"])
        self._flipped_cache: dict[int, pygame.Surface] = {}

    def get_frame(self, anim_key: str, elapsed_ticks: int, tick_rate: int, flip: bool) -> pygame.Surface:
        clip = self.animations.get(anim_key, self.animations["idle"])
        frame = clip.frame_at(elapsed_ticks, tick_rate)
        if not flip:
            return frame
        flipped = self._flipped_cache.get(id(frame))
        if flipped is None:
            flipped = pygame.transform.flip(frame, True, False)
            self._flipped_cache[id(frame)] = flipped
        return flipped


class ProjectileSprite:
    """A loaded projectile pack (a single looping spin animation)."""

    def __init__(self, projectile_id: str) -> None:
        root = PROJECTILES_DIR / projectile_id
        manifest = json.loads((root / "projectile_manifest.json").read_text(encoding="utf-8"))
        frames = [pygame.image.load(str(root / path)).convert_alpha() for path in manifest["frames"]]
        self.clip = AnimationClip(frames=frames, fps=manifest["fps"], loop=manifest["loop"])
        self._flipped_cache: dict[int, pygame.Surface] = {}

    def get_frame(self, elapsed_ticks: int, tick_rate: int, flip: bool) -> pygame.Surface:
        frame = self.clip.frame_at(elapsed_ticks, tick_rate)
        if not flip:
            return frame
        flipped = self._flipped_cache.get(id(frame))
        if flipped is None:
            flipped = pygame.transform.flip(frame, True, False)
            self._flipped_cache[id(frame)] = flipped
        return flipped

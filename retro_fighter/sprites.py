"""Loads the sprite packs under assets/fighters/ and plays their animations.

Each pack (see assets/fighters/<variant>/<id>/manifest.json, variant being
"ld" or "hd") is a set of named animation clips authored facing right. A
fighter facing left is drawn by flipping the
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


def _crossfade(frame_a: pygame.Surface, frame_b: pygame.Surface, t: float) -> pygame.Surface:
    """Alpha-dissolve from frame_a to frame_b. Packs with only 2-3 keyframes
    per animation (especially the early HD packs) look like a hard slideshow
    without this; a cross-fade doesn't add real in-between motion, but it
    softens the cut enough to read as an animation rather than a snap."""
    blended = frame_a.copy()
    ghost = frame_b.copy()
    ghost.set_alpha(round(t * 255))
    blended.blit(ghost, (0, 0))
    return blended


@dataclass
class AnimationClip:
    frames: list[pygame.Surface]
    fps: int
    loop: bool

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def frame_at(self, elapsed_ticks: int, tick_rate: int) -> tuple[pygame.Surface, bool]:
        """Returns (surface, is_blended). is_blended is False when the
        surface is one of the pack's own persistent frames (safe to cache by
        id()), True when it's a freshly-allocated cross-fade (must not be
        cached — see FighterSpriteSet.get_frame)."""
        elapsed_seconds = elapsed_ticks / tick_rate
        position = elapsed_seconds * self.fps
        index = int(position)
        blend_t = position - index

        if self.loop:
            index_a = index % self.frame_count
            index_b = (index_a + 1) % self.frame_count
        else:
            index_a = min(index, self.frame_count - 1)
            index_b = min(index + 1, self.frame_count - 1)

        if index_a == index_b or blend_t <= 0.0:
            return self.frames[index_a], False
        return _crossfade(self.frames[index_a], self.frames[index_b], blend_t), True


class FighterSpriteSet:
    """A loaded sprite pack for one fighter id (e.g. "rose_kunoichi").

    `variant` selects between the hand-drawn "ld" (low definition) pack
    that ships with the game and an optional "hd" (VLM-generated,
    higher-fidelity) alternative under assets/fighters/hd/<fighter_id>/.
    The HD packs are an early proof of concept and don't cover every
    animation yet (e.g. no standing low punch/kick/block) — any animation
    key missing from a pack's manifest falls back to "idle" below, exactly
    like a base LD pack missing an extension would.
    """

    def __init__(self, fighter_id: str, variant: str = "ld") -> None:
        root = FIGHTERS_DIR / variant / fighter_id
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
        frame, blended = clip.frame_at(elapsed_ticks, tick_rate)
        if not flip:
            return frame
        if blended:
            # Freshly-allocated cross-fade surface: flip it directly rather
            # than caching by id(), which would leak (a new id() every call)
            # and could even collide with an unrelated future surface once
            # this one is garbage-collected.
            return pygame.transform.flip(frame, True, False)
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
        frame, blended = self.clip.frame_at(elapsed_ticks, tick_rate)
        if not flip:
            return frame
        if blended:
            return pygame.transform.flip(frame, True, False)
        flipped = self._flipped_cache.get(id(frame))
        if flipped is None:
            flipped = pygame.transform.flip(frame, True, False)
            self._flipped_cache[id(frame)] = flipped
        return flipped

"""Loads the sound pack under assets/audio/ and plays it.

Two layers, mixed at playback time:
- per-character voice lines (assets/audio/fighters/<audio_id>/ready_to_use/
  and voice_only/), several variations per gameplay event picked at random;
- shared "common" sounds (impacts, whooshes, projectile SFX) under
  assets/audio/fighters/common/, layered under the voice so every character
  gets consistent hit/whoosh feedback even where a real voice line doesn't
  exist yet for that event.

The mapping (assets/audio/pygame_audio_mapping.json) is a plain "common" /
"fighters" split following the retro_fighter_real_audio_pack_v3 convention.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

AUDIO_ROOT = Path(__file__).resolve().parent.parent / "assets" / "audio"

# The sprite pack's fighter_id ("shinobi") doesn't match this audio pack's
# own character folder name ("shinobi_male").
AUDIO_CHARACTER_ALIASES = {"shinobi": "shinobi_male"}


def _load_sounds(paths: list[str]) -> list[pygame.mixer.Sound]:
    return [pygame.mixer.Sound(str(AUDIO_ROOT / path.removeprefix("assets/audio/"))) for path in paths]


class SoundBank:
    """Common + per-character event sounds loaded from pygame_audio_mapping.json."""

    def __init__(self) -> None:
        mapping = json.loads((AUDIO_ROOT / "pygame_audio_mapping.json").read_text(encoding="utf-8"))
        self.common: dict[str, list[pygame.mixer.Sound]] = {
            event: _load_sounds(paths) for event, paths in mapping.get("common", {}).items()
        }
        self.fighters: dict[str, dict[str, list[pygame.mixer.Sound]]] = {
            character_id: {event: _load_sounds(paths) for event, paths in events.items()}
            for character_id, events in mapping.get("fighters", {}).items()
        }

    def play(self, fighter_id: str, event: str, volume: float = 0.75) -> None:
        character_id = AUDIO_CHARACTER_ALIASES.get(fighter_id, fighter_id)
        candidates = self.fighters.get(character_id, {}).get(event, [])
        if candidates:
            sound = random.choice(candidates)
            sound.set_volume(volume)
            sound.play()

    def play_common(self, event: str, volume: float = 0.6) -> None:
        candidates = self.common.get(event, [])
        if candidates:
            sound = random.choice(candidates)
            sound.set_volume(volume)
            sound.play()

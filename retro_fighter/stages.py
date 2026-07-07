"""Arena/background loading for Retro Fighter.

Drop this file into: retro_fighter/stages.py
Copy assets/backgrounds/ from the extension pack into the repository root.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pygame

from .config import WINDOW_HEIGHT, WINDOW_WIDTH


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARENA_MANIFEST = PROJECT_ROOT / "assets" / "backgrounds" / "arena_manifest.json"


@dataclass(frozen=True)
class ArenaDefinition:
    id: str
    name: str
    file: str
    theme: str = ""
    suggested_music: str | None = None


class StageBackgrounds:
    """Loads and draws arena backgrounds from assets/backgrounds/arena_manifest.json.

    The class is deliberately defensive: if the manifest or a file is missing,
    draw() returns False and the old procedural background can be used as a fallback.
    """

    def __init__(self, manifest_path: Path = DEFAULT_ARENA_MANIFEST) -> None:
        self.manifest_path = manifest_path
        self.arenas: list[ArenaDefinition] = []
        self._cache: dict[str, pygame.Surface] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if not self.manifest_path.exists():
            return
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        self.arenas = []
        for item in data.get("arenas", []):
            try:
                self.arenas.append(
                    ArenaDefinition(
                        id=item["id"],
                        name=item.get("name", item["id"]),
                        file=item["file"],
                        theme=item.get("theme", ""),
                        suggested_music=item.get("suggested_music"),
                    )
                )
            except KeyError:
                continue

    def __len__(self) -> int:
        return len(self.arenas)

    def normalize_index(self, index: int) -> int:
        if not self.arenas:
            return 0
        return index % len(self.arenas)

    def get_name(self, index: int) -> str:
        if not self.arenas:
            return "Décor prototype"
        return self.arenas[self.normalize_index(index)].name

    def get_id(self, index: int) -> str:
        if not self.arenas:
            return "prototype"
        return self.arenas[self.normalize_index(index)].id

    def _load_surface(self, arena: ArenaDefinition) -> pygame.Surface | None:
        if arena.id in self._cache:
            return self._cache[arena.id]

        image_path = PROJECT_ROOT / arena.file
        if not image_path.exists():
            return None

        try:
            surface = pygame.image.load(str(image_path)).convert()
        except pygame.error:
            return None

        if surface.get_size() != (WINDOW_WIDTH, WINDOW_HEIGHT):
            surface = pygame.transform.smoothscale(surface, (WINDOW_WIDTH, WINDOW_HEIGHT))

        self._cache[arena.id] = surface
        return surface

    def draw(self, screen: pygame.Surface, index: int) -> bool:
        """Draws the selected arena. Returns True when an arena was drawn."""
        if not self.arenas:
            return False

        arena = self.arenas[self.normalize_index(index)]
        surface = self._load_surface(arena)
        if surface is None:
            return False

        screen.blit(surface, (0, 0))
        return True

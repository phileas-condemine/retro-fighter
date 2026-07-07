"""Input abstractions shared by human and AI controllers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from .attacks import AttackKind, HeightLevel
from .config import Controls


@dataclass
class Command:
    move_axis: int = 0  # -1 left, +1 right
    aim_level: HeightLevel = "mid"
    attack: Optional[AttackKind] = None  # "punch", "kick", or None
    block: bool = False
    jump: bool = False
    ranged_attack: bool = False


def level_from_vertical(up: bool, down: bool) -> HeightLevel:
    if up and not down:
        return "high"
    if down and not up:
        return "low"
    return "mid"


class HumanController:
    """Translate keyboard state into one-frame combat commands."""

    def __init__(self, controls: Controls) -> None:
        self.controls = controls

    def read(self, events: list[pygame.event.Event], keys: pygame.key.ScancodeWrapper) -> Command:
        move_axis = 0
        if keys[self.controls.left]:
            move_axis -= 1
        if keys[self.controls.right]:
            move_axis += 1
        move_axis = max(-1, min(1, move_axis))

        up = keys[self.controls.up]
        down = keys[self.controls.down]
        level = level_from_vertical(up, down)
        attack = None
        jump = False
        ranged_attack = False

        for event in events:
            if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
                continue
            if event.key == self.controls.punch:
                attack = "punch"
            elif event.key == self.controls.kick:
                attack = "kick"
            elif event.key == self.controls.jump:
                jump = True
            elif event.key == self.controls.ranged:
                ranged_attack = True

        return Command(
            move_axis=move_axis,
            aim_level=level,
            attack=attack,
            block=bool(keys[self.controls.block]),
            jump=jump,
            ranged_attack=ranged_attack,
        )

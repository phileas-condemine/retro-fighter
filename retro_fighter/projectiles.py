"""Ranged attack data, in the same data-driven spirit as attacks.py.

Gameplay numbers (damage, speed, timing) live here as plain Python, mirroring
attacks.py, rather than being parsed from the asset pack's JSON at runtime —
the JSON stays purely descriptive of frames/fps for the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .fighter import Fighter


@dataclass(frozen=True)
class ProjectileDefinition:
    projectile_id: str
    display_name: str
    damage: int
    speed_px_per_second: float
    hitbox_w: int
    hitbox_h: int
    charge_frames: int  # RANGED_ATTACK charge phase duration, in simulation frames
    throw_frames: int  # RANGED_ATTACK throw/recovery phase duration, in simulation frames
    spawn_frame: int  # frame within the throw phase at which the projectile spawns
    spawn_offset_x: int  # from the thrower's anchor, mirrored by facing
    spawn_offset_y: int  # from the thrower's anchor (negative = up, shoulder line)

    @property
    def total_frames(self) -> int:
        return self.charge_frames + self.throw_frames


PROJECTILE_DEFS: Dict[str, ProjectileDefinition] = {
    "shuriken": ProjectileDefinition(
        projectile_id="shuriken",
        display_name="Shuriken",
        damage=8,
        speed_px_per_second=560,
        hitbox_w=34,
        hitbox_h=20,
        charge_frames=24,
        throw_frames=26,
        spawn_frame=13,
        spawn_offset_x=88,
        spawn_offset_y=-104,
    ),
    "rose_energy_ball": ProjectileDefinition(
        projectile_id="rose_energy_ball",
        display_name="Boule d'énergie",
        damage=10,
        speed_px_per_second=455,
        hitbox_w=42,
        hitbox_h=36,
        charge_frames=24,
        throw_frames=26,
        spawn_frame=13,
        spawn_offset_x=88,
        spawn_offset_y=-104,
    ),
}

# Which projectile each fighter throws.
FIGHTER_PROJECTILE_ID: Dict[str, str] = {
    "shinobi": "shuriken",
    "rose_kunoichi": "rose_energy_ball",
}


@dataclass
class ActiveProjectile:
    """A projectile currently in flight."""

    definition: ProjectileDefinition
    x: float
    y: float
    facing: int
    owner: "Fighter"
    elapsed: int = 0
    # Set once the combat log has recorded an outcome (dodge, hit, block) so
    # a projectile that dodges early and keeps flying off-screen doesn't get
    # logged a second time as a miss.
    logged: bool = False

"""Attack definitions for the combat prototype.

The important idea is that attacks are data-driven. To balance the game, edit the
numbers below instead of rewriting the engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

HeightLevel = str  # "high", "mid", "low"
AttackKind = str  # "punch", "kick"


@dataclass(frozen=True)
class AttackDefinition:
    kind: AttackKind
    level: HeightLevel
    damage: int
    range_px: int
    startup_frames: int
    active_frames: int
    recovery_frames: int
    blockstun_frames: int
    hitstun_frames: int
    knockback_px: float
    label: str

    @property
    def total_frames(self) -> int:
        return self.startup_frames + self.active_frames + self.recovery_frames

    def is_active(self, frame: int) -> bool:
        return self.startup_frames <= frame < self.startup_frames + self.active_frames


# High/mid/low correspond to where the active hitbox appears on the opponent body.
# Punches are faster but shorter and less damaging.
# Kicks are slower but longer and stronger.
ATTACKS: Dict[Tuple[AttackKind, HeightLevel], AttackDefinition] = {
    ("punch", "high"): AttackDefinition(
        kind="punch",
        level="high",
        damage=8,
        range_px=66,
        startup_frames=4,
        active_frames=4,
        recovery_frames=11,
        blockstun_frames=9,
        hitstun_frames=16,
        knockback_px=11,
        label="Direct visage",
    ),
    ("punch", "mid"): AttackDefinition(
        kind="punch",
        level="mid",
        damage=9,
        range_px=70,
        startup_frames=5,
        active_frames=4,
        recovery_frames=11,
        blockstun_frames=9,
        hitstun_frames=16,
        knockback_px=12,
        label="Direct corps",
    ),
    ("punch", "low"): AttackDefinition(
        kind="punch",
        level="low",
        damage=7,
        range_px=62,
        startup_frames=5,
        active_frames=4,
        recovery_frames=12,
        blockstun_frames=8,
        hitstun_frames=16,
        knockback_px=9,
        label="Coup bas rapide",
    ),
    ("kick", "high"): AttackDefinition(
        kind="kick",
        level="high",
        damage=13,
        range_px=91,
        startup_frames=9,
        active_frames=5,
        recovery_frames=21,
        blockstun_frames=14,
        hitstun_frames=26,
        knockback_px=22,
        label="High kick",
    ),
    ("kick", "mid"): AttackDefinition(
        kind="kick",
        level="mid",
        damage=12,
        range_px=96,
        startup_frames=8,
        active_frames=5,
        recovery_frames=20,
        blockstun_frames=13,
        hitstun_frames=26,
        knockback_px=21,
        label="Front kick",
    ),
    ("kick", "low"): AttackDefinition(
        kind="kick",
        level="low",
        damage=10,
        range_px=86,
        startup_frames=8,
        active_frames=5,
        recovery_frames=20,
        blockstun_frames=12,
        hitstun_frames=26,
        knockback_px=18,
        label="Balayage",
    ),
}


HEIGHT_LABELS = {
    "high": "haut",
    "mid": "milieu",
    "low": "bas",
}

# Relative vertical bands within the fighter hurtbox.
# Values are fractions from body top to body bottom.
HEIGHT_BANDS = {
    "high": (0.08, 0.38),
    "mid": (0.36, 0.72),
    "low": (0.69, 0.96),
}

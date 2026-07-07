"""Global configuration for Retro Fighter."""
from __future__ import annotations

from dataclasses import dataclass


WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 576
FPS = 60
TITLE = "Retro Fighter - Python/Pygame Prototype"

GROUND_Y = 472
LEFT_BOUND = 48
RIGHT_BOUND = WINDOW_WIDTH - 48

MAX_HEALTH = 100
ROUND_TIME_SECONDS = 99

GRAVITY = 0.75
JUMP_SPEED = -14.2
WALK_SPEED = 4.2
AIR_CONTROL_SPEED = 2.0
# The salto covers ground much faster than a regular jump's air control, so
# a double jump reliably carries a fighter across the opponent instead of
# barely drifting past them.
DOUBLE_JUMP_AIR_CONTROL_SPEED = 6.5
BODY_WIDTH = 54
BODY_HEIGHT = 132

BODY_PUSHBACK = 1.8

# Getting hit always cancels whatever the defender was doing and locks them
# out of attacking for a fixed 0.5s, regardless of which move landed. This
# keeps the "first hit wins" trade rule simple and predictable.
HITSTUN_FRAMES = round(FPS * 0.5)

# Crouching (hold DOWN while grounded) halves the hurtbox height, anchored at
# the feet, which lets it duck under high melee attacks and shoulder-level
# projectiles without any special-case collision code.
CROUCH_HEIGHT_MULTIPLIER = 0.50
CROUCH_WALK_SPEED_MULTIPLIER = 0.42

# The salto (second jump) plays its own animation for a fixed duration (its
# own counter, independent of state_timer which HITSTUN/BLOCKSTUN already use
# as a countdown), then falls back to the regular jump pose for the rest of
# the hang time/descent.
DOUBLE_JUMP_POSE_FRAMES = round(FPS * 6 / 16)  # matches double_jump_salto's 6 frames @ 16 fps

# How far above the ground a salto needs to be to dodge a shoulder-height
# projectile. Unlike crouching, this isn't derived from hurtbox geometry
# alone (the hurtbox still reaches down to the feet mid-air) — it is an
# explicit gameplay rule so the salto avoids the projectile deliberately,
# not through incidental hitbox overlap.
PROJECTILE_AVOID_Y_DELTA = 90

# UI/background colors, centralized here. Fighters themselves are drawn from
# the sprite packs under assets/fighters/.
COLOR_BG = (18, 19, 27)
COLOR_FLOOR = (39, 43, 54)
COLOR_FLOOR_LINE = (79, 88, 112)
COLOR_TEXT = (238, 238, 238)
COLOR_MUTED = (160, 166, 185)
COLOR_RED = (230, 66, 66)
COLOR_GREEN = (75, 218, 117)
COLOR_BLUE = (87, 151, 246)
COLOR_YELLOW = (241, 203, 83)
COLOR_PURPLE = (172, 112, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_SHADOW = (0, 0, 0)
COLOR_HITBOX = (255, 70, 70)
COLOR_HURTBOX = (80, 160, 255)


@dataclass(frozen=True)
class Controls:
    """Keyboard layout for the human player."""

    left: int
    right: int
    up: int
    down: int
    punch: int
    kick: int
    block: int
    jump: int
    ranged: int


AI_MODES = ("sparring", "easy", "medium", "hard")
AI_MODE_LABELS = {
    "sparring": "Sparring - l'ordinateur ne fait rien",
    "easy": "Facile - lent, erreurs fréquentes",
    "medium": "Moyen - distance, blocages partiels",
    "hard": "Difficile - punitions, mix-ups, bons blocages",
}

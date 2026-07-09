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
# Shared by both the first jump and the double-jump/salto (Fighter.start_jump
# sets vel_y = JUMP_SPEED for each), so raising this makes both arcs higher
# at once. Peak height is JUMP_SPEED^2 / (2*GRAVITY) -- -15.5 clears about
# 160px vs -14.2's 134px, a noticeably higher hop without floating.
JUMP_SPEED = -15.5
WALK_SPEED = 4.2
AIR_CONTROL_SPEED = 2.0
# The salto covers ground much faster than a regular jump's air control, so
# a double jump reliably carries a fighter across the opponent instead of
# barely drifting past them.
DOUBLE_JUMP_AIR_CONTROL_SPEED = 6.5
BODY_WIDTH = 54
BODY_HEIGHT = 132

# Dash: double-tap Left/Right for a short, committed burst of horizontal
# speed (about 4x walk speed) — a gap closer/escape tool distinct from
# regular walking. DASH_INPUT_WINDOW_FRAMES is how quickly the second tap
# must follow the first to count as a double-tap; DASH_COOLDOWN_FRAMES
# prevents chaining dashes back to back. Total travel distance is roughly
# DASH_SPEED * DASH_DURATION_FRAMES (~187px, up from ~150px) -- covers more
# ground per dash both grounded and airborne, since Fighter.start_dash
# reuses the same speed/duration for the air-dash burst.
DASH_SPEED = 17.0
DASH_DURATION_FRAMES = round(FPS * 0.18)
DASH_COOLDOWN_FRAMES = round(FPS * 0.5)
DASH_INPUT_WINDOW_FRAMES = round(FPS * 0.25)
# Also usable mid-air (from JUMP or DOUBLE_JUMP/salto) as a horizontal burst
# layered on top of the current jump arc -- see Fighter.start_dash.

# Kinetic-blur trail: a handful of alpha-fading afterimage copies of the
# sprite, captured every frame while dashing (grounded or airborne), drawn
# behind the live frame. DASH_TRAIL_MAX_COPIES caps how many are alive at
# once (older ones are dropped once decayed past 0 alpha, or once the count
# exceeds this); DASH_TRAIL_ALPHA_DECAY is how much surface alpha each ghost
# loses per frame, so an individual ghost fades out over
# DASH_TRAIL_INITIAL_ALPHA / DASH_TRAIL_ALPHA_DECAY frames regardless of
# whether the dash itself is still going.
DASH_TRAIL_MAX_COPIES = 4
DASH_TRAIL_INITIAL_ALPHA = 130
DASH_TRAIL_ALPHA_DECAY = 32

BODY_PUSHBACK = 1.8

# Getting hit always cancels whatever the defender was doing. Melee attacks
# each define their own hitstun_frames (attacks.py) so kicks lock the
# defender out for longer than punches; this global value now only covers
# projectile hits, which don't have a per-move definition of their own.
HITSTUN_FRAMES = round(FPS * 0.5)

# Stamina/endurance: spent by attacking and by absorbing a blocked hit,
# regenerated only while neutral (not mid-attack, not stunned). It doesn't
# gate actions outright — instead, low stamina proportionally lengthens the
# fatigued fighter's own attack recovery (see Fighter.start_attack), so an
# all-out attacker eventually slows down and gives a cornered opponent a
# real window to escape or punish instead of being comboed indefinitely.
# Heuristic starting values, meant to be tuned from combat log data like the
# attack numbers in attacks.py.
MAX_STAMINA = 100.0
STAMINA_COST_PUNCH = 6.0
STAMINA_COST_KICK = 16.0
STAMINA_COST_BLOCK = 8.0
STAMINA_COST_RANGED = 12.0
STAMINA_REGEN_PER_FRAME = 0.35
# At 0 stamina, an attack's recovery_frames are multiplied by (1 + this);
# at full stamina, no penalty. Scales linearly with current stamina between.
FATIGUE_MAX_RECOVERY_PENALTY = 1.0

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
    """Keyboard layout for the human player.

    `punch` accepts multiple keycodes so both AZERTY (Q) and QWERTY (A) map
    to the same physical key next to S/D/F — those three are already on the
    same physical keys on both layouts, only the leftmost one (Q vs A) differs.
    """

    left: int
    right: int
    up: int
    down: int
    punch: tuple[int, ...]
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

"""State names used by the finite-state machine."""
from __future__ import annotations

from enum import Enum


class FighterState(str, Enum):
    IDLE = "idle"
    WALK = "walk"
    JUMP = "jump"
    ATTACK = "attack"
    BLOCK = "block"
    BLOCKSTUN = "blockstun"
    HITSTUN = "hitstun"
    KO = "ko"
    # Values match the extension pack's animation keys directly, so the
    # renderer's generic fallback (fighter.state.value) resolves them without
    # special-casing, exactly like idle/walk/jump/hitstun/ko above.
    CROUCH = "crouch_idle"
    CROUCH_WALK = "crouch_walk"
    DOUBLE_JUMP = "double_jump_salto"
    RANGED_ATTACK = "ranged_attack"
    # No dedicated sprite; the renderer plays the "walk" animation faster
    # while this state is active (see Renderer.animation_key).
    DASH = "dash"

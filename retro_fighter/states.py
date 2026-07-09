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
    # A landed grab: no sprite of its own either, the renderer reuses the
    # "ko" pose/animation (Renderer.animation_key) since a knocked-down
    # fighter looks the same either way; unlike KO the round doesn't end,
    # state_timer just counts down (Fighter.update_stun) back to IDLE.
    KNOCKDOWN = "knockdown"

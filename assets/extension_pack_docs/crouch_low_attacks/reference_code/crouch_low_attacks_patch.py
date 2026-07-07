"""
Retro Fighter — crouch low attacks patch

À intégrer dans ton système de résolution d'animation / attaque.
Ce fichier est volontairement autonome et indicatif.
"""

from __future__ import annotations


def is_crouching_state(state: str) -> bool:
    return state in {"CROUCH", "CROUCH_WALK", "BLOCK_LOW"}


def resolve_attack_animation(fighter, attack) -> str:
    """Return the animation name for a fighter attack.

    Expected attack fields:
    - attack.kind: "punch" or "kick"
    - attack.height: "high", "mid", "low"

    Expected fighter fields:
    - fighter.state, or fighter.is_crouching
    """
    is_crouching = bool(getattr(fighter, "is_crouching", False))
    state = getattr(fighter, "state", None)
    if state is not None:
        is_crouching = is_crouching or is_crouching_state(str(state))

    if is_crouching and attack.height == "low":
        if attack.kind == "punch":
            return "crouch_punch_low"
        if attack.kind == "kick":
            return "crouch_kick_low"

    return f"{attack.kind}_{attack.height}"


CROUCH_LOW_ATTACKS = {
    "crouch_punch_low": {
        "kind": "punch",
        "height": "low",
        "damage": 5,
        "startup_frames": 2,
        "active_frames": [2, 3],
        "recovery_frames": 1,
        "hitbox": {"x_offset": 34, "y_offset": -55, "width": 52, "height": 24},
        "hurtbox": {"height_multiplier": 0.50, "width_multiplier": 1.08},
    },
    "crouch_kick_low": {
        "kind": "kick",
        "height": "low",
        "damage": 8,
        "startup_frames": 3,
        "active_frames": [3, 4],
        "recovery_frames": 2,
        "hitbox": {"x_offset": 50, "y_offset": -20, "width": 70, "height": 20},
        "hurtbox": {"height_multiplier": 0.50, "width_multiplier": 1.18},
    },
}

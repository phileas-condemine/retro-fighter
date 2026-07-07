"""Computer-controlled opponent behavior."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .attacks import HeightLevel
from .fighter import Fighter
from .input_manager import Command
from .states import FighterState


@dataclass
class AIDifficultyConfig:
    reaction_frames: int
    attack_chance: float
    block_chance: float
    correct_block_chance: float
    jump_chance: float
    ideal_distance: int
    mistake_chance: float
    cooldown_min: int
    cooldown_max: int
    ranged_chance: float


DIFFICULTY = {
    "sparring": AIDifficultyConfig(999, 0.0, 0.0, 0.0, 0.0, 95, 1.0, 90, 140, 0.0),
    "easy": AIDifficultyConfig(28, 0.30, 0.22, 0.38, 0.04, 88, 0.48, 42, 86, 0.05),
    "medium": AIDifficultyConfig(14, 0.52, 0.55, 0.68, 0.08, 92, 0.22, 24, 55, 0.12),
    "hard": AIDifficultyConfig(6, 0.76, 0.78, 0.88, 0.11, 97, 0.08, 12, 32, 0.18),
}

RANGED_COOLDOWN_MIN = 90
RANGED_COOLDOWN_MAX = 150
RANGED_MIN_DISTANCE = 180


class AIController:
    """Small rule-based fighting AI.

    The AI has no hidden combat advantages. Higher difficulties simply react more
    often, choose better spacing, block more accurately, and punish whiffed moves.
    """

    def __init__(self, mode: str = "medium") -> None:
        self.mode = mode
        self.rng = random.Random()
        self.next_decision_frame = 0
        self.attack_cooldown = 0
        self.ranged_cooldown = 0
        self.last_command = Command()
        self.preferred_level: HeightLevel = "mid"

    @property
    def config(self) -> AIDifficultyConfig:
        return DIFFICULTY[self.mode]

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.next_decision_frame = 0
        self.attack_cooldown = 0
        self.ranged_cooldown = 0
        self.last_command = Command()

    def read(self, frame: int, me: Fighter, opponent: Fighter) -> Command:
        if self.mode == "sparring" or me.is_ko:
            return Command()

        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        self.ranged_cooldown = max(0, self.ranged_cooldown - 1)
        cfg = self.config

        # During stun/attack, the command mostly matters for air control after an attack.
        if me.state in {FighterState.HITSTUN, FighterState.BLOCKSTUN, FighterState.ATTACK, FighterState.RANGED_ATTACK}:
            return Command(move_axis=0, aim_level=self.preferred_level)

        if frame < self.next_decision_frame:
            return self.last_command

        self.next_decision_frame = frame + cfg.reaction_frames
        command = self.decide(me, opponent, cfg)
        self.last_command = command
        return command

    def decide(self, me: Fighter, opponent: Fighter, cfg: AIDifficultyConfig) -> Command:
        distance = abs(opponent.x - me.x)
        direction_to_opponent = 1 if opponent.x > me.x else -1
        command = Command()

        if self.detect_incoming_projectile(opponent) and me.on_ground and self.rng.random() < cfg.block_chance:
            # Duck under the shoulder-height projectile rather than block it.
            return Command(move_axis=0, aim_level="low")

        incoming_level = self.detect_incoming_attack(opponent, distance)
        if incoming_level and me.on_ground and self.rng.random() < cfg.block_chance:
            block_level = incoming_level if self.rng.random() < cfg.correct_block_chance else self.random_level(exclude=incoming_level)
            return Command(move_axis=0, aim_level=block_level, block=True)

        # Punish when the opponent is recovering close enough.
        if opponent.state == FighterState.ATTACK and opponent.attack and opponent.attack.definition.recovery_frames > 0:
            if opponent.attack.frame > opponent.attack.definition.startup_frames + opponent.attack.definition.active_frames:
                if distance < 116 and self.attack_cooldown == 0:
                    return self.choose_attack(distance, cfg, punish=True)

        if self.rng.random() < cfg.jump_chance and me.on_ground and distance < 80:
            return Command(move_axis=-direction_to_opponent, jump=True)

        ideal = cfg.ideal_distance
        if distance > ideal + 22:
            command.move_axis = direction_to_opponent
        elif distance < ideal - 28:
            command.move_axis = -direction_to_opponent
        else:
            # Strafe a little to look less static.
            if self.rng.random() < 0.20:
                command.move_axis = self.rng.choice([-1, 0, 1])

        if self.ranged_cooldown == 0 and distance > RANGED_MIN_DISTANCE and me.on_ground and self.rng.random() < cfg.ranged_chance:
            self.ranged_cooldown = self.rng.randint(RANGED_COOLDOWN_MIN, RANGED_COOLDOWN_MAX)
            return Command(move_axis=command.move_axis, ranged_attack=True)

        in_punch_range = distance < 86
        in_kick_range = distance < 126
        if self.attack_cooldown == 0 and in_kick_range and self.rng.random() < cfg.attack_chance:
            command = self.choose_attack(distance, cfg, punish=False)

        return command

    def choose_attack(self, distance: float, cfg: AIDifficultyConfig, punish: bool) -> Command:
        if punish:
            kind = "kick" if distance > 76 else self.rng.choice(["punch", "kick"])
            level = self.pick_mixup_level(cfg, favor="mid")
        else:
            if distance < 72:
                kind = "punch" if self.rng.random() < 0.62 else "kick"
            else:
                kind = "kick" if self.rng.random() < 0.78 else "punch"
            level = self.pick_mixup_level(cfg)

        if self.rng.random() < cfg.mistake_chance:
            # Mistakes include whiffing at the wrong level or using a short attack from far away.
            if distance > 84 and self.rng.random() < 0.50:
                kind = "punch"
            level = self.random_level()

        self.attack_cooldown = self.rng.randint(cfg.cooldown_min, cfg.cooldown_max)
        self.preferred_level = level
        return Command(attack=kind, aim_level=level)

    def detect_incoming_attack(self, opponent: Fighter, distance: float) -> Optional[HeightLevel]:
        if opponent.state != FighterState.ATTACK or not opponent.attack:
            return None
        definition = opponent.attack.definition
        soon_active = definition.startup_frames - 2 <= opponent.attack.frame <= definition.startup_frames + definition.active_frames
        reaches = distance <= definition.range_px + 42
        if soon_active and reaches:
            return opponent.attack.effective_level
        return None

    def detect_incoming_projectile(self, opponent: Fighter) -> bool:
        if opponent.state != FighterState.RANGED_ATTACK or not opponent.ranged_attack:
            return False
        return not opponent.ranged_attack.is_charging  # the throw is happening, projectile about to fly

    def pick_mixup_level(self, cfg: AIDifficultyConfig, favor: Optional[HeightLevel] = None) -> HeightLevel:
        if favor and self.rng.random() < 0.55:
            return favor
        if self.mode == "hard":
            return self.rng.choices(["high", "mid", "low"], weights=[0.30, 0.42, 0.28], k=1)[0]
        if self.mode == "medium":
            return self.rng.choices(["high", "mid", "low"], weights=[0.22, 0.55, 0.23], k=1)[0]
        return self.rng.choices(["high", "mid", "low"], weights=[0.15, 0.70, 0.15], k=1)[0]

    def random_level(self, exclude: Optional[HeightLevel] = None) -> HeightLevel:
        levels = ["high", "mid", "low"]
        if exclude and exclude in levels and len(levels) > 1:
            levels.remove(exclude)
        return self.rng.choice(levels)

"""Fighter entity and combat finite-state machine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from .attacks import ATTACKS, HEIGHT_BANDS, AttackDefinition, HeightLevel, HEIGHT_LABELS
from .config import (
    AIR_CONTROL_SPEED,
    BODY_HEIGHT,
    BODY_WIDTH,
    CROUCH_HEIGHT_MULTIPLIER,
    CROUCH_WALK_SPEED_MULTIPLIER,
    DASH_COOLDOWN_FRAMES,
    DASH_DURATION_FRAMES,
    DASH_SPEED,
    DOUBLE_JUMP_AIR_CONTROL_SPEED,
    DOUBLE_JUMP_POSE_FRAMES,
    FATIGUE_MAX_RECOVERY_PENALTY,
    GRAVITY,
    GROUND_Y,
    HITSTUN_FRAMES,
    JUMP_SPEED,
    LEFT_BOUND,
    MAX_HEALTH,
    MAX_STAMINA,
    RIGHT_BOUND,
    STAMINA_COST_BLOCK,
    STAMINA_COST_KICK,
    STAMINA_COST_PUNCH,
    STAMINA_COST_RANGED,
    STAMINA_REGEN_PER_FRAME,
    WALK_SPEED,
)
from .input_manager import Command
from .projectiles import FIGHTER_PROJECTILE_ID, PROJECTILE_DEFS, ProjectileDefinition
from .states import FighterState


@dataclass
class ActiveAttack:
    definition: AttackDefinition
    effective_level: HeightLevel
    started_crouching: bool = False
    frame: int = 0
    already_hit: bool = False
    # Set once the combat log has recorded an outcome for this attack (hit,
    # blocked, dodged, whiffed, or interrupted) so Game doesn't log the same
    # attempt twice across the frames it stays active/recovering.
    logged: bool = False
    # Fatigue penalty (see Fighter.start_attack), frozen at the moment the
    # attack starts: extra recovery frames tacked onto the definition's own,
    # proportional to how tired the attacker already was.
    extra_recovery_frames: int = 0

    @property
    def is_active(self) -> bool:
        return self.definition.is_active(self.frame)

    @property
    def is_finished(self) -> bool:
        return self.frame >= self.definition.total_frames + self.extra_recovery_frames


@dataclass
class ActiveRangedAttack:
    definition: ProjectileDefinition
    frame: int = 0

    @property
    def is_charging(self) -> bool:
        return self.frame < self.definition.charge_frames

    @property
    def throw_frame(self) -> int:
        return self.frame - self.definition.charge_frames

    @property
    def is_finished(self) -> bool:
        return self.frame >= self.definition.total_frames


@dataclass
class HitResult:
    landed: bool
    blocked: bool
    damage: int
    message: str


class Fighter:
    """Runtime object for one character.

    Coordinates use x as body center and y as foot position. This makes jumping
    and floor alignment simple.
    """

    def __init__(self, name: str, x: float, color: tuple[int, int, int], fighter_id: str, is_human: bool = False) -> None:
        self.name = name
        self.x = x
        self.y = float(GROUND_Y)
        self.color = color
        self.fighter_id = fighter_id
        self.is_human = is_human

        self.facing = 1
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.health = MAX_HEALTH
        self.stamina = MAX_STAMINA
        self.state = FighterState.IDLE
        self.state_timer = 0
        self.attack: Optional[ActiveAttack] = None
        self.ranged_attack: Optional[ActiveRangedAttack] = None
        self.block_level: HeightLevel = "mid"
        self.last_attack_label = ""
        self.combo_counter = 0
        self.rounds_won = 0
        self.jumps_used = 0
        self.double_jump_frame = 0
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_direction = 0
        # One-frame flags the game reads to trigger sound effects / spawn projectiles.
        self.attack_started_this_frame = False
        self.jump_started_this_frame = False
        self.ranged_attack_started_this_frame = False
        self.landed_this_frame = False
        self.projectile_spawn_pending = False
        self.dash_started_this_frame = False

    @property
    def on_ground(self) -> bool:
        return self.y >= GROUND_Y - 0.1

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self.x - BODY_WIDTH / 2),
            round(self.y - BODY_HEIGHT),
            BODY_WIDTH,
            BODY_HEIGHT,
        )

    @property
    def hurtbox(self) -> pygame.Rect:
        rect = self.rect.copy()
        rect.inflate_ip(-12, -8)
        # A crouch-initiated punch/kick (started_crouching, see start_attack)
        # keeps the crouched pose throughout the attack (Renderer.animation_key
        # plays crouch_punch_low/crouch_kick_low) — the hurtbox must stay
        # crouched along with it, otherwise the body silently "stands back up"
        # hitbox-wise for the attack's duration and dodges (crouch under a
        # high melee attack or a shoulder-height projectile) fail even though
        # the character never visibly left the crouched stance.
        is_crouched = self.state in (FighterState.CROUCH, FighterState.CROUCH_WALK) or (
            self.state == FighterState.ATTACK and self.attack is not None and self.attack.started_crouching
        )
        if is_crouched:
            # Feet stay put; only the top comes down. This is also what lets a
            # crouch duck under high melee attacks and shoulder-height
            # projectiles without any extra collision rule.
            new_height = round(rect.height * CROUCH_HEIGHT_MULTIPLIER)
            rect.top = rect.bottom - new_height
            rect.height = new_height
        return rect

    @property
    def is_ko(self) -> bool:
        return self.health <= 0 or self.state == FighterState.KO

    def reset(self, x: float) -> None:
        self.x = x
        self.y = float(GROUND_Y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.health = MAX_HEALTH
        self.stamina = MAX_STAMINA
        self.state = FighterState.IDLE
        self.state_timer = 0
        self.attack = None
        self.ranged_attack = None
        self.block_level = "mid"
        self.last_attack_label = ""
        self.combo_counter = 0
        self.jumps_used = 0
        self.double_jump_frame = 0
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_direction = 0

    def update_facing(self, opponent: "Fighter") -> None:
        if opponent.x >= self.x:
            self.facing = 1
        else:
            self.facing = -1

    def can_start_action(self) -> bool:
        return self.state in {
            FighterState.IDLE,
            FighterState.WALK,
            FighterState.JUMP,
            FighterState.DOUBLE_JUMP,
            FighterState.BLOCK,
            FighterState.CROUCH,
            FighterState.CROUCH_WALK,
        }

    def start_attack(self, kind: str, level: HeightLevel) -> None:
        if not self.can_start_action():
            return
        if self.state == FighterState.BLOCK and not self.on_ground:
            return
        definition = ATTACKS[(kind, level)]
        # Airborne attacks always aim for the head, no matter the vertical input.
        effective_level = level if self.on_ground else "high"
        started_crouching = self.state in (FighterState.CROUCH, FighterState.CROUCH_WALK)
        # Fatigue: how tired the attacker already is (before this attack's own
        # cost below) proportionally lengthens its recovery tail. At full
        # stamina this is 0; at 0 stamina, recovery_frames is doubled
        # (FATIGUE_MAX_RECOVERY_PENALTY=1.0) — an exhausted attacker slows
        # down and gives whoever they're pressuring, even cornered, a real
        # window to escape or counter.
        stamina_fraction = self.stamina / MAX_STAMINA
        extra_recovery = round(definition.recovery_frames * FATIGUE_MAX_RECOVERY_PENALTY * (1.0 - stamina_fraction))
        self.attack = ActiveAttack(
            definition=definition,
            effective_level=effective_level,
            started_crouching=started_crouching,
            extra_recovery_frames=extra_recovery,
        )
        self.state = FighterState.ATTACK
        self.state_timer = 0
        self.last_attack_label = definition.label
        self.attack_started_this_frame = True
        self.stamina = max(0.0, self.stamina - (STAMINA_COST_KICK if kind == "kick" else STAMINA_COST_PUNCH))
        # Small forward commitment: it makes kicks feel weightier.
        if kind == "kick" and self.on_ground:
            self.x += 2.0 * self.facing

    def start_ranged_attack(self) -> None:
        if not self.can_start_action():
            return
        if self.state == FighterState.BLOCK and not self.on_ground:
            return
        definition = PROJECTILE_DEFS[FIGHTER_PROJECTILE_ID[self.fighter_id]]
        self.ranged_attack = ActiveRangedAttack(definition=definition)
        self.state = FighterState.RANGED_ATTACK
        self.state_timer = 0
        self.ranged_attack_started_this_frame = True
        self.stamina = max(0.0, self.stamina - STAMINA_COST_RANGED)

    def start_jump(self) -> None:
        grounded_jump_states = {
            FighterState.IDLE,
            FighterState.WALK,
            FighterState.BLOCK,
            FighterState.CROUCH,
            FighterState.CROUCH_WALK,
        }
        if self.on_ground and self.state in grounded_jump_states:
            self.vel_y = JUMP_SPEED
            self.state = FighterState.JUMP
            self.state_timer = 0
            self.jumps_used = 1
            self.jump_started_this_frame = True
        elif not self.on_ground and self.state == FighterState.JUMP and self.jumps_used < 2:
            # Double jump: a salto pose for a fixed duration, then falls back
            # to the regular jump pose. Enough extra height and airtime to
            # clear an opponent (or a shoulder-height projectile) and land on
            # the other side, swapping sides.
            self.vel_y = JUMP_SPEED
            self.state = FighterState.DOUBLE_JUMP
            self.double_jump_frame = 0
            self.jumps_used = 2
            self.jump_started_this_frame = True

    def start_dash(self, direction: int) -> None:
        if self.dash_cooldown > 0:
            return
        if self.on_ground:
            if self.state not in (FighterState.IDLE, FighterState.WALK):
                return
        else:
            # Air dash: a horizontal burst mid-jump or mid-salto. It only
            # overrides vel_x -- vel_y (and gravity, via apply_physics) keeps
            # running underneath it, so it reads as a burst layered on top of
            # the current arc rather than a mid-air stop.
            if self.state not in (FighterState.JUMP, FighterState.DOUBLE_JUMP):
                return
        self.state = FighterState.DASH
        self.state_timer = 0
        self.dash_timer = DASH_DURATION_FRAMES
        self.dash_direction = direction
        self.vel_x = float(direction) * DASH_SPEED
        self.dash_started_this_frame = True

    def update_dash(self, command: Command) -> None:
        self.dash_timer -= 1
        self.vel_x = float(self.dash_direction) * DASH_SPEED
        if self.dash_timer <= 0:
            self.dash_cooldown = DASH_COOLDOWN_FRAMES
            if self.on_ground:
                self.state = FighterState.WALK if command.move_axis != 0 else FighterState.IDLE
            else:
                # Still airborne when the burst ends (started the dash mid-jump
                # or landed just after it did not happen) -- fall back to the
                # regular jump/fall pose instead of a grounded one.
                self.state = FighterState.JUMP
            self.state_timer = 0

    def get_attack_hitbox(self) -> Optional[pygame.Rect]:
        if not self.attack or not self.attack.is_active:
            return None

        body = self.rect
        definition = self.attack.definition
        top_frac, bottom_frac = HEIGHT_BANDS[self.attack.effective_level]
        y = body.top + round(BODY_HEIGHT * top_frac)
        height = max(12, round(BODY_HEIGHT * (bottom_frac - top_frac)))
        width = definition.range_px

        if self.facing == 1:
            x = body.right - 4
        else:
            x = body.left - width + 4

        return pygame.Rect(x, y, width, height)

    def update(self, command: Command, opponent: "Fighter") -> None:
        self.attack_started_this_frame = False
        self.jump_started_this_frame = False
        self.ranged_attack_started_this_frame = False
        self.landed_this_frame = False
        self.projectile_spawn_pending = False
        self.dash_started_this_frame = False

        if self.is_ko:
            self.state = FighterState.KO
            self.vel_x = 0.0
            self.apply_physics()
            return

        self.update_facing(opponent)

        # Stamina only regenerates while neutral — not mid-attack/mid-throw,
        # not stunned. Holding a block stance without getting hit counts as
        # neutral (only absorbing an actual hit costs stamina, see
        # receive_attack/receive_projectile_hit).
        if self.state not in (FighterState.ATTACK, FighterState.RANGED_ATTACK, FighterState.HITSTUN, FighterState.BLOCKSTUN):
            self.stamina = min(MAX_STAMINA, self.stamina + STAMINA_REGEN_PER_FRAME)

        if self.state in {FighterState.HITSTUN, FighterState.BLOCKSTUN}:
            self.update_stun()
            self.apply_physics()
            return

        self.state_timer += 1

        if self.state == FighterState.ATTACK:
            self.update_attack(command)
            self.apply_physics()
            return

        if self.state == FighterState.RANGED_ATTACK:
            self.update_ranged_attack()
            self.apply_physics()
            return

        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        if command.dash:
            self.start_dash(command.dash)

        if self.state == FighterState.DASH:
            self.update_dash(command)
            self.apply_physics()
            return

        if command.jump:
            self.start_jump()

        if command.attack:
            self.start_attack(command.attack, command.aim_level)
            self.apply_physics()
            return

        if command.ranged_attack:
            self.start_ranged_attack()
            self.apply_physics()
            return

        if command.block and self.on_ground:
            self.state = FighterState.BLOCK
            self.block_level = command.aim_level
            self.vel_x = 0.0
            self.apply_physics()
            return

        self.block_level = command.aim_level

        if self.on_ground and command.aim_level == "low":
            # Holding DOWN alone (no attack/block) crouches instead of idling.
            if command.move_axis != 0:
                self.state = FighterState.CROUCH_WALK
                self.vel_x = float(command.move_axis) * WALK_SPEED * CROUCH_WALK_SPEED_MULTIPLIER
            else:
                self.state = FighterState.CROUCH
                self.vel_x = 0.0
            self.apply_physics()
            return

        self.update_movement(command.move_axis)
        self.apply_physics()

    def update_movement(self, move_axis: int) -> None:
        if self.on_ground:
            speed = WALK_SPEED
        elif self.state == FighterState.DOUBLE_JUMP:
            speed = DOUBLE_JUMP_AIR_CONTROL_SPEED
        else:
            speed = AIR_CONTROL_SPEED
        self.vel_x = float(move_axis) * speed

        if not self.on_ground:
            if self.state == FighterState.DOUBLE_JUMP:
                self.double_jump_frame += 1
                if self.double_jump_frame >= DOUBLE_JUMP_POSE_FRAMES:
                    self.state = FighterState.JUMP
            elif self.state != FighterState.JUMP:
                self.state = FighterState.JUMP
        elif move_axis != 0:
            self.state = FighterState.WALK
        else:
            self.state = FighterState.IDLE

    def update_attack(self, command: Command) -> None:
        # An attack can continue while airborne. Movement is limited during attacks.
        if self.attack:
            self.attack.frame += 1
            if self.attack.is_finished:
                self.attack = None
                self.state = FighterState.JUMP if not self.on_ground else FighterState.IDLE
                self.state_timer = 0
        if self.on_ground:
            self.vel_x *= 0.52
        else:
            self.vel_x = max(-AIR_CONTROL_SPEED, min(AIR_CONTROL_SPEED, self.vel_x + 0.2 * command.move_axis))

    def update_ranged_attack(self) -> None:
        if not self.ranged_attack:
            self.state = FighterState.IDLE
            return
        self.ranged_attack.frame += 1
        if not self.ranged_attack.is_charging and self.ranged_attack.throw_frame == self.ranged_attack.definition.spawn_frame:
            self.projectile_spawn_pending = True
        if self.ranged_attack.is_finished:
            self.ranged_attack = None
            self.state = FighterState.JUMP if not self.on_ground else FighterState.IDLE
            self.state_timer = 0
        if self.on_ground:
            self.vel_x *= 0.52

    def update_stun(self) -> None:
        if self.state_timer <= 0:
            self.state = FighterState.JUMP if not self.on_ground else FighterState.IDLE
            return
        self.state_timer -= 1
        self.vel_x *= 0.82
        if self.state_timer <= 0:
            self.state = FighterState.JUMP if not self.on_ground else FighterState.IDLE

    def apply_physics(self) -> None:
        self.x += self.vel_x
        self.x = max(LEFT_BOUND, min(RIGHT_BOUND, self.x))

        if not self.on_ground or self.vel_y < 0:
            self.vel_y += GRAVITY
            self.y += self.vel_y
            if self.y >= GROUND_Y:
                self.y = float(GROUND_Y)
                self.vel_y = 0.0
                self.jumps_used = 0
                if self.state in (FighterState.JUMP, FighterState.DOUBLE_JUMP):
                    self.state = FighterState.IDLE
                self.landed_this_frame = True
        else:
            self.vel_y = 0.0
            self.jumps_used = 0

    def receive_attack(self, attacker: "Fighter", attack: AttackDefinition, hit_level: HeightLevel) -> HitResult:
        if self.is_ko:
            return HitResult(False, False, 0, "")

        blocked = self.state == FighterState.BLOCK and self.block_level == hit_level
        if blocked:
            self.state = FighterState.BLOCKSTUN
            self.state_timer = attack.blockstun_frames
            self.vel_x = attacker.facing * attack.knockback_px * 0.25
            self.stamina = max(0.0, self.stamina - STAMINA_COST_BLOCK)
            message = f"{self.name} bloque {HEIGHT_LABELS[hit_level]} (0 dégât)"
            return HitResult(True, True, 0, message)

        damage = min(self.health, attack.damage)
        self.health -= damage
        self.attack = None
        self.ranged_attack = None
        self.state = FighterState.HITSTUN
        self.state_timer = attack.hitstun_frames
        self.vel_x = attacker.facing * attack.knockback_px
        if hit_level == "low":
            self.vel_y = min(self.vel_y, -2.2)
        message = (
            f"{attacker.name}: {attack.label} {HEIGHT_LABELS[hit_level]} "
            f"-> {damage} dégâts"
        )
        if self.health <= 0:
            self.health = 0
            self.state = FighterState.KO
            message += f" | {self.name} KO"
        return HitResult(True, False, damage, message)

    def receive_projectile_hit(self, attacker: "Fighter", damage: int) -> HitResult:
        if self.is_ko:
            return HitResult(False, False, 0, "")

        blocked = self.state == FighterState.BLOCK and self.block_level in ("high", "mid")
        if blocked:
            self.stamina = max(0.0, self.stamina - STAMINA_COST_BLOCK)
            message = f"{self.name} bloque le projectile (0 dégât)"
            return HitResult(True, True, 0, message)

        dealt = min(self.health, damage)
        self.health -= dealt
        self.attack = None
        self.ranged_attack = None
        self.state = FighterState.HITSTUN
        self.state_timer = HITSTUN_FRAMES
        self.vel_x = attacker.facing * 14.0
        message = f"{attacker.name}: projectile -> {dealt} dégâts"
        if self.health <= 0:
            self.health = 0
            self.state = FighterState.KO
            message += f" | {self.name} KO"
        return HitResult(True, False, dealt, message)

    def force_push(self, amount: float) -> None:
        self.x += amount
        self.x = max(LEFT_BOUND, min(RIGHT_BOUND, self.x))

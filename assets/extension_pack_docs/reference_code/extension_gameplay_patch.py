"""
Retro Fighter extension patch: crouch, shoulder-level projectiles, double-jump salto.

This file is intentionally engine-agnostic. Copy the pieces that match your current
classes. It assumes your Fighter already has x/y, facing, state, velocity and an
animation resolver.
"""
from dataclasses import dataclass
from enum import Enum, auto

class FighterState(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    ATTACK = auto()
    BLOCK = auto()
    HITSTUN = auto()
    KO = auto()
    CROUCH = auto()
    CROUCH_WALK = auto()
    RANGED_STARTUP = auto()
    RANGED_ACTIVE_RECOVERY = auto()
    DOUBLE_JUMP = auto()

@dataclass
class ProjectileSpec:
    projectile_id: str
    damage: int
    speed_px_per_second: float
    spawn_offset_x: int = 88
    spawn_offset_y: int = -104  # shoulder line relative to fighter anchor/feet
    hitbox_w: int = 38
    hitbox_h: int = 24
    hit_height: str = "shoulder"
    destroy_on_hit: bool = True
    destroy_on_block: bool = True

@dataclass
class Projectile:
    projectile_id: str
    x: float
    y: float
    vx: float
    owner_id: str
    damage: int
    hitbox_w: int
    hitbox_h: int
    hit_height: str = "shoulder"
    alive: bool = True

    @property
    def rect(self):
        # Replace with pygame.Rect in your codebase.
        return (self.x - self.hitbox_w / 2, self.y - self.hitbox_h / 2, self.hitbox_w, self.hitbox_h)

PROJECTILE_SPECS = {
    "shinobi": ProjectileSpec(
        projectile_id="shuriken",
        damage=8,
        speed_px_per_second=560,
        hitbox_w=34,
        hitbox_h=20,
    ),
    "rose_kunoichi": ProjectileSpec(
        projectile_id="rose_energy_ball",
        damage=10,
        speed_px_per_second=455,
        hitbox_w=42,
        hitbox_h=36,
    ),
}

CROUCH_HEIGHT_MULTIPLIER = 0.50
CROUCH_WALK_SPEED_MULTIPLIER = 0.42
RANGED_SPAWN_FRAME = 3


def resolve_animation(fighter):
    """Add these cases to your existing animation resolver."""
    if fighter.state == FighterState.CROUCH:
        return "crouch_idle"
    if fighter.state == FighterState.CROUCH_WALK:
        return "crouch_walk"
    if fighter.state == FighterState.RANGED_STARTUP:
        return "ranged_charge"
    if fighter.state == FighterState.RANGED_ACTIVE_RECOVERY:
        return "ranged_throw"
    if fighter.state == FighterState.DOUBLE_JUMP:
        return "double_jump_salto"
    return None


def update_crouch_state(fighter, input_state):
    """Call before regular walk/jump/attack resolution while fighter is grounded."""
    if not fighter.is_grounded or fighter.state in (FighterState.HITSTUN, FighterState.KO):
        return False

    if input_state.down:
        if input_state.left or input_state.right:
            fighter.state = FighterState.CROUCH_WALK
            direction = -1 if input_state.left else 1
            fighter.vx = direction * fighter.walk_speed * CROUCH_WALK_SPEED_MULTIPLIER
        else:
            fighter.state = FighterState.CROUCH
            fighter.vx = 0
        fighter.hurtbox_height = fighter.base_hurtbox_height * CROUCH_HEIGHT_MULTIPLIER
        fighter.hurtbox_bottom_locked = True
        return True

    fighter.hurtbox_height = fighter.base_hurtbox_height
    fighter.hurtbox_bottom_locked = False
    return False


def start_ranged_attack(fighter):
    if fighter.state in (FighterState.HITSTUN, FighterState.KO):
        return False
    if not getattr(fighter, "can_act", True):
        return False
    fighter.state = FighterState.RANGED_STARTUP
    fighter.animation_frame_index = 0
    fighter.pending_projectile_spawned = False
    return True


def spawn_projectile_if_needed(fighter, projectiles):
    """Call during ranged_throw update after animation frame is advanced."""
    if fighter.state != FighterState.RANGED_ACTIVE_RECOVERY:
        return
    if fighter.pending_projectile_spawned:
        return
    if fighter.animation_frame_index < RANGED_SPAWN_FRAME:
        return

    spec = PROJECTILE_SPECS[fighter.fighter_id]
    facing_sign = 1 if fighter.facing == "right" else -1
    spawn_x = fighter.x + facing_sign * spec.spawn_offset_x
    spawn_y = fighter.ground_y + spec.spawn_offset_y
    vx = facing_sign * spec.speed_px_per_second
    projectiles.append(Projectile(
        projectile_id=spec.projectile_id,
        x=spawn_x,
        y=spawn_y,
        vx=vx,
        owner_id=fighter.fighter_id,
        damage=spec.damage,
        hitbox_w=spec.hitbox_w,
        hitbox_h=spec.hitbox_h,
        hit_height=spec.hit_height,
    ))
    fighter.pending_projectile_spawned = True


def update_projectiles(projectiles, dt, stage_bounds):
    left, right = stage_bounds
    for p in projectiles:
        if not p.alive:
            continue
        p.x += p.vx * dt
        if p.x < left - 100 or p.x > right + 100:
            p.alive = False
    projectiles[:] = [p for p in projectiles if p.alive]


def projectile_hits_fighter(projectile, target):
    """Use your pygame.Rect collision here. Key rule: crouch should miss shoulder projectile."""
    if target.state in (FighterState.CROUCH, FighterState.CROUCH_WALK):
        return False
    if target.state == FighterState.DOUBLE_JUMP and target.y < target.ground_y - 90:
        return False
    # Replace this with target.hurtbox.colliderect(projectile.rect)
    return True


def start_double_jump(fighter):
    if fighter.is_grounded:
        return False
    if getattr(fighter, "double_jump_used", False):
        return False
    fighter.double_jump_used = True
    fighter.state = FighterState.DOUBLE_JUMP
    fighter.animation_frame_index = 0
    fighter.vy = -520
    return True

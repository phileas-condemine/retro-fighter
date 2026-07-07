"""Main game loop and match rules."""
from __future__ import annotations

from typing import Optional

import pygame

from .ai import AIController
from .audio import SoundBank
from .config import (
    AI_MODE_LABELS,
    AI_MODES,
    BODY_PUSHBACK,
    BODY_WIDTH,
    COLOR_BLUE,
    COLOR_RED,
    Controls,
    FPS,
    GROUND_Y,
    LEFT_BOUND,
    PROJECTILE_AVOID_Y_DELTA,
    RIGHT_BOUND,
    ROUND_TIME_SECONDS,
    TITLE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .fighter import Fighter
from .input_manager import HumanController
from .projectiles import ActiveProjectile
from .renderer import Renderer
from .states import FighterState


# Which "common" layer sounds (assets/audio/fighters/common/) accompany each
# projectile's charge/throw/hit, keyed by ProjectileDefinition.projectile_id.
PROJECTILE_COMMON_SOUNDS = {
    "shuriken": {"draw": "shuriken_draw", "throw": "shuriken_throw", "hit": "shuriken_hit"},
    "rose_energy_ball": {"draw": "rose_energy_charge", "throw": "rose_energy_throw", "hit": "rose_energy_hit"},
}


class Game:
    def __init__(self) -> None:
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        except pygame.error:
            pass
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        self.sounds: Optional[SoundBank] = None
        try:
            self.sounds = SoundBank()
        except pygame.error:
            pass  # No audio device available; play silently.

        controls = Controls(
            left=pygame.K_LEFT,
            right=pygame.K_RIGHT,
            up=pygame.K_UP,
            down=pygame.K_DOWN,
            punch=pygame.K_j,
            kick=pygame.K_k,
            block=pygame.K_l,
            jump=pygame.K_SPACE,
            ranged=pygame.K_u,
        )
        self.human_controller = HumanController(controls)
        self.ai_controller = AIController("medium")

        self.player = Fighter("PLAYER", x=260, color=COLOR_BLUE, fighter_id="rose_kunoichi", is_human=True)
        self.enemy = Fighter("CPU", x=764, color=COLOR_RED, fighter_id="shinobi", is_human=False)
        self.projectiles: list[ActiveProjectile] = []
        self.frame = 0
        self.round_start_frame = 0
        self.round_time_remaining = float(ROUND_TIME_SECONDS)
        self.round_over = False
        self.paused = False
        self.debug_hitboxes = False
        self.messages: list[str] = []
        self.ai_mode = "medium"
        self.in_menu = True
        self.menu_index = 2

    def run(self) -> None:
        """Desktop entrypoint: blocking loop around tick()."""
        while self.tick():
            pass
        pygame.quit()

    def tick(self) -> bool:
        """Runs a single frame. Returns False once the game should quit.

        Split out from run() so a web build (Pygbag) can drive the same
        per-frame logic from its own async loop (`while game.tick(): await
        asyncio.sleep(0)`) without a second, diverging copy of this code —
        see main.py.
        """
        dt_ms = self.clock.tick(FPS)
        events = pygame.event.get()
        running = True
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        if self.in_menu:
            running = self.handle_menu(events, running)
            self.renderer.draw_menu(self.menu_index)
            pygame.display.flip()
            return running

        running = self.handle_global_events(events, running)
        if not self.paused and not self.round_over:
            self.update(events, dt_ms)
        self.renderer.draw(self)
        pygame.display.flip()
        return running

    def handle_menu(self, events: list[pygame.event.Event], running: bool) -> bool:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(AI_MODES)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(AI_MODES)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start_match(AI_MODES[self.menu_index])
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.start_match("sparring")
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.start_match("easy")
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.start_match("medium")
            elif event.key in (pygame.K_4, pygame.K_KP4):
                self.start_match("hard")
        return running

    def handle_global_events(self, events: list[pygame.event.Event], running: bool) -> bool:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_p:
                self.paused = not self.paused
            elif event.key == pygame.K_h:
                self.debug_hitboxes = not self.debug_hitboxes
            elif event.key == pygame.K_r:
                self.reset_round()
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.start_match("sparring")
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.start_match("easy")
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.start_match("medium")
            elif event.key in (pygame.K_4, pygame.K_KP4):
                self.start_match("hard")
            elif event.key == pygame.K_m:
                current = AI_MODES.index(self.ai_mode)
                self.start_match(AI_MODES[(current + 1) % len(AI_MODES)])
        return running

    def start_match(self, ai_mode: str) -> None:
        self.ai_mode = ai_mode
        self.ai_controller.set_mode(ai_mode)
        self.in_menu = False
        self.paused = False
        self.reset_round()
        self.messages.append(AI_MODE_LABELS[ai_mode])

    def reset_round(self) -> None:
        self.player.reset(260)
        self.enemy.reset(764)
        self.player.update_facing(self.enemy)
        self.enemy.update_facing(self.player)
        self.projectiles = []
        self.round_start_frame = self.frame
        self.round_time_remaining = float(ROUND_TIME_SECONDS)
        self.round_over = False
        self.messages = [f"Nouveau round - IA {self.ai_mode}"]

    def update(self, events: list[pygame.event.Event], dt_ms: int) -> None:
        del dt_ms  # The simulation is deterministic at FPS frames per second.
        self.frame += 1
        self.round_time_remaining = ROUND_TIME_SECONDS - (self.frame - self.round_start_frame) / FPS

        keys = pygame.key.get_pressed()
        player_command = self.human_controller.read(events, keys)
        ai_command = self.ai_controller.read(self.frame, self.enemy, self.player)

        self.player.update(player_command, self.enemy)
        self.enemy.update(ai_command, self.player)
        self.play_action_sounds(self.player)
        self.play_action_sounds(self.enemy)
        self.spawn_projectiles()
        self.update_projectiles()
        self.resolve_body_collision()
        self.apply_hits()
        self.check_round_over()

    def play_sound(self, fighter_id: str, event: str, volume: float = 0.75) -> None:
        if self.sounds:
            self.sounds.play(fighter_id, event, volume)

    def play_common(self, event: str, volume: float = 0.6) -> None:
        if self.sounds:
            self.sounds.play_common(event, volume)

    def play_action_sounds(self, fighter: Fighter) -> None:
        if fighter.jump_started_this_frame:
            if fighter.state == FighterState.DOUBLE_JUMP:
                self.play_sound(fighter.fighter_id, "double_jump")
                self.play_common("double_jump_whoosh", volume=0.45)
            else:
                self.play_sound(fighter.fighter_id, "jump")
                self.play_common("jump_whoosh", volume=0.4)
        if fighter.landed_this_frame:
            self.play_sound(fighter.fighter_id, "landing", volume=0.6)
            self.play_common("landing", volume=0.5)
        if fighter.attack_started_this_frame and fighter.attack:
            self.play_sound(fighter.fighter_id, fighter.attack.definition.kind)
            self.play_common("attack_whoosh", volume=0.35)
        if fighter.ranged_attack_started_this_frame and fighter.ranged_attack:
            self.play_sound(fighter.fighter_id, "projectile_throw")
            draw_event = PROJECTILE_COMMON_SOUNDS[fighter.ranged_attack.definition.projectile_id]["draw"]
            self.play_common(draw_event, volume=0.4)

    def spawn_projectiles(self) -> None:
        for fighter in (self.player, self.enemy):
            if not fighter.projectile_spawn_pending or not fighter.ranged_attack:
                continue
            definition = fighter.ranged_attack.definition
            self.projectiles.append(ActiveProjectile(
                definition=definition,
                x=fighter.x + fighter.facing * definition.spawn_offset_x,
                y=fighter.y + definition.spawn_offset_y,
                facing=fighter.facing,
                owner=fighter,
            ))
            throw_event = PROJECTILE_COMMON_SOUNDS[definition.projectile_id]["throw"]
            self.play_common(throw_event, volume=0.5)

    def update_projectiles(self) -> None:
        survivors: list[ActiveProjectile] = []
        for projectile in self.projectiles:
            projectile.elapsed += 1
            projectile.x += projectile.facing * projectile.definition.speed_px_per_second / FPS

            if projectile.x < LEFT_BOUND - 80 or projectile.x > RIGHT_BOUND + 80:
                continue  # flew off-stage

            target = self.enemy if projectile.owner is self.player else self.player
            hitbox = pygame.Rect(0, 0, projectile.definition.hitbox_w, projectile.definition.hitbox_h)
            hitbox.center = (round(projectile.x), round(projectile.y))

            if not hitbox.colliderect(target.hurtbox):
                survivors.append(projectile)
                continue

            if target.state == FighterState.DOUBLE_JUMP and target.y <= GROUND_Y - PROJECTILE_AVOID_Y_DELTA:
                survivors.append(projectile)  # salto high enough: dodged
                continue

            result = target.receive_projectile_hit(projectile.owner, projectile.definition.damage)
            if result.message:
                self.add_message(result.message)
            if result.landed:
                self.play_sound(target.fighter_id, "block" if result.blocked else "hurt")
                if result.blocked:
                    self.play_common("block_impact", volume=0.5)
                else:
                    hit_event = PROJECTILE_COMMON_SOUNDS[projectile.definition.projectile_id]["hit"]
                    self.play_common(hit_event, volume=0.5)
            # Hit or blocked: either way the projectile is spent.

        self.projectiles = survivors

    def resolve_body_collision(self) -> None:
        # Body blocking only applies on the ground. A jump (especially the
        # salto/double jump) is meant to let a fighter clear the opponent and
        # land on the other side; requiring the full body rects to stop
        # overlapping vertically (132px) left only a couple of pixels of
        # margin over the salto's worst-case apex, and every frame spent
        # still airborne-but-not-high-enough kept shoving the fighters apart
        # before they could ever cross. Skipping the push entirely while
        # either fighter is off the ground makes crossing over reliable
        # regardless of exact jump timing/height.
        if not self.player.on_ground or not self.enemy.on_ground:
            return

        p_rect = self.player.rect
        e_rect = self.enemy.rect
        if not p_rect.colliderect(e_rect):
            return
        if self.enemy.x == self.player.x:
            direction = 1
        else:
            direction = 1 if self.enemy.x > self.player.x else -1
        overlap = BODY_WIDTH - abs(self.enemy.x - self.player.x)
        if overlap <= 0:
            return
        push = overlap / 2 + BODY_PUSHBACK
        self.player.force_push(-direction * push)
        self.enemy.force_push(direction * push)

    def apply_hits(self) -> None:
        candidates = []
        for attacker, defender in ((self.player, self.enemy), (self.enemy, self.player)):
            if not attacker.attack or attacker.attack.already_hit:
                continue
            hitbox = attacker.get_attack_hitbox()
            if hitbox and hitbox.colliderect(defender.hurtbox):
                candidates.append((attacker, defender, attacker.attack.definition, attacker.attack.effective_level))

        if not candidates:
            return

        # If both attacks connect on the same frame, both are applied. Otherwise,
        # the first active hit cancels the opponent's pending attack via hitstun.
        for attacker, defender, definition, hit_level in candidates:
            if attacker.attack:
                attacker.attack.already_hit = True
            result = defender.receive_attack(attacker, definition, hit_level)
            if result.message:
                self.add_message(result.message)
            if result.landed:
                self.play_sound(defender.fighter_id, "block" if result.blocked else "hurt")
                if result.blocked:
                    self.play_common("block_impact", volume=0.5)
                else:
                    impact_event = "kick_hit" if definition.kind == "kick" else "punch_hit"
                    self.play_common(impact_event, volume=0.55)

    def check_round_over(self) -> None:
        if self.round_over:
            return
        if self.player.is_ko or self.enemy.is_ko:
            self.round_over = True
            return
        if self.round_time_remaining <= 0:
            self.round_time_remaining = 0
            self.round_over = True
            if self.player.health > self.enemy.health:
                self.enemy.health = 0
            elif self.enemy.health > self.player.health:
                self.player.health = 0
            else:
                self.add_message("Temps écoulé : égalité")

    def add_message(self, message: str) -> None:
        self.messages.append(message)
        if len(self.messages) > 9:
            self.messages = self.messages[-9:]

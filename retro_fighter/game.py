"""Main game loop and match rules."""
from __future__ import annotations

import random
import sys
from typing import Optional

import pygame

from .ai import AIController
from .audio import SoundBank
from .combat_log import CombatLogger
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
    HITSTUN_FRAMES,
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
        # SCALED: without it, SDL creates the window at the literal logical
        # size (1024x576) with no upscaling, which looks tiny on a normal
        # desktop monitor — SCALED stretches it to fill the window while
        # keeping game code working in 1024x576 coordinates. Desktop-only:
        # under Pygbag (sys.platform == "emscripten"), web_template/default.tmpl's
        # own JS (rf_fit_canvas) already scales/letterboxes the canvas to fill
        # the browser tab. SCALED there does its own internal SDL-level
        # letterboxing on top of that, producing a second, smaller nested
        # letterbox instead of one clean fit.
        flags = 0 if sys.platform == "emscripten" else pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
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
            punch=(pygame.K_q, pygame.K_a),  # Q on AZERTY, A on QWERTY: same physical key
            kick=pygame.K_s,
            block=pygame.K_d,
            jump=pygame.K_SPACE,
            ranged=pygame.K_f,
        )
        self.human_controller = HumanController(controls)
        self.ai_controller = AIController("medium")
        # Demo mode ("Tab") swaps the human controller for a second AI
        # instance controlling the player fighter, at the same difficulty as
        # the opponent. A separate AIController instance is required (not a
        # shared one) since it tracks per-fighter cooldown/decision state
        # internally rather than taking it from the Fighter it controls.
        self.player_ai_controller = AIController("medium")
        self.demo_mode = False
        self.graphics_variant = "ld"  # "ld" -> "hd" -> "v2", cycled by the G key

        self.player = Fighter("PLAYER", x=260, color=COLOR_BLUE, fighter_id="rose_kunoichi", is_human=True)
        self.enemy = Fighter("CPU", x=764, color=COLOR_RED, fighter_id="shinobi", is_human=False)
        self.projectiles: list[ActiveProjectile] = []
        self.combat_log = CombatLogger()
        self._player_prev_state = self.player.state
        self._enemy_prev_state = self.enemy.state
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
            self.renderer.draw_menu(self.menu_index, self.demo_mode, self.graphics_variant)
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
            elif event.key == pygame.K_TAB:
                self.toggle_demo_mode()
            elif event.key == pygame.K_g:
                self.cycle_graphics_variant()
            elif event.key == pygame.K_c:
                self.swap_fighter()
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
            elif event.key == pygame.K_TAB:
                self.toggle_demo_mode()
            elif event.key == pygame.K_g:
                self.cycle_graphics_variant()
            elif event.key == pygame.K_c:
                self.swap_fighter()
        return running

    def start_match(self, ai_mode: str) -> None:
        self.ai_mode = ai_mode
        self.ai_controller.set_mode(ai_mode)
        self.player_ai_controller.set_mode(ai_mode)
        self.in_menu = False
        self.paused = False
        self.reset_round()
        self.messages.append(AI_MODE_LABELS[ai_mode])

    def toggle_demo_mode(self) -> None:
        self.demo_mode = not self.demo_mode
        self.player_ai_controller.set_mode(self.ai_mode)
        if not self.in_menu:
            self.reset_round()

    def cycle_graphics_variant(self) -> None:
        # Pure rendering swap (see Renderer.sprite_sets) — no round reset
        # needed, unlike demo mode which swaps controllers. "v2" only has
        # real art for some fighters so far (rose_kunoichi); Renderer.
        # draw_fighter falls back to hd/ld per-fighter for the rest.
        order = ["ld", "hd", "v2"]
        self.graphics_variant = order[(order.index(self.graphics_variant) + 1) % len(order)]
        self.renderer.set_graphics_variant(self.graphics_variant)

    def swap_fighter(self) -> None:
        # Swaps which character PLAYER/CPU are playing (e.g. PLAYER takes
        # Shinobi instead of Rose). Sprites, audio aliases, and projectile
        # choice are all looked up live off Fighter.fighter_id (see
        # assets/fighters/CONTRACT.md) with no fighter-specific branching
        # anywhere in the engine, so swapping just the id -- not colors,
        # names, or which Fighter instance is self.player -- is enough to
        # fully re-skin both sides.
        self.player.fighter_id, self.enemy.fighter_id = self.enemy.fighter_id, self.player.fighter_id
        # Same guard as toggle_demo_mode: reset_round() would otherwise
        # start+immediately finalize a real combat-log entry for a round
        # that was never actually played, spamming a stray log file every
        # time C is pressed on the pre-match menu. start_match() already
        # calls reset_round() unconditionally once a match begins, so the
        # swap still takes effect either way.
        if not self.in_menu:
            self.reset_round()

    def reset_round(self) -> None:
        # If a fight was in progress (e.g. R pressed mid-round), flush its log
        # before starting a fresh one instead of silently losing it.
        self._finalize_log("Round interrompu (reset manuel)")

        self.player.name = "CPU 1" if self.demo_mode else "PLAYER"
        self.enemy.name = "CPU 2" if self.demo_mode else "CPU"
        self.player.is_human = not self.demo_mode
        self.player.reset(260)
        self.enemy.reset(764)
        self.player.update_facing(self.enemy)
        self.enemy.update_facing(self.player)
        self.projectiles = []
        self.round_start_frame = self.frame
        self.round_time_remaining = float(ROUND_TIME_SECONDS)
        self.round_over = False
        # A fresh arena each time a fight starts (new match or R to reset).
        stage_count = len(self.renderer.stage_backgrounds)
        if stage_count > 0:
            self.renderer.set_stage_index(random.randrange(stage_count))
        self.messages = [f"Nouveau round - IA {self.ai_mode} - {self.renderer.stage_name()}"]

        self.combat_log.start(
            ai_mode=self.ai_mode,
            stage_name=self.renderer.stage_name(),
            demo_mode=self.demo_mode,
            player_name=self.player.name,
            enemy_name=self.enemy.name,
            player_fighter_id=self.player.fighter_id,
            enemy_fighter_id=self.enemy.fighter_id,
            round_start_frame=self.frame,
        )
        self._player_prev_state = self.player.state
        self._enemy_prev_state = self.enemy.state

    def _finalize_log(self, result_text: str) -> None:
        if not self.combat_log.meta:
            return
        duration_s = (self.frame - self.combat_log.round_start_frame) / FPS
        self.combat_log.write(result_text=result_text, duration_s=duration_s)
        self.combat_log.meta = {}
        self.combat_log.entries = []

    def update(self, events: list[pygame.event.Event], dt_ms: int) -> None:
        del dt_ms  # The simulation is deterministic at FPS frames per second.
        self.frame += 1
        self.round_time_remaining = ROUND_TIME_SECONDS - (self.frame - self.round_start_frame) / FPS

        if self.demo_mode:
            player_command = self.player_ai_controller.read(self.frame, self.player, self.enemy)
        else:
            keys = pygame.key.get_pressed()
            player_command = self.human_controller.read(events, keys, self.frame)
        ai_command = self.ai_controller.read(self.frame, self.enemy, self.player)

        # Captured before update() so apply_hits()/the log can tell whether an
        # attack that was active this frame finished without ever being
        # logged (whiffed out of range, or interrupted by taking a hit).
        player_attack_before = self.player.attack
        enemy_attack_before = self.enemy.attack

        self.player.update(player_command, self.enemy)
        self.enemy.update(ai_command, self.player)
        self.play_action_sounds(self.player)
        self.play_action_sounds(self.enemy)
        self._player_prev_state = self.log_action_events(self.player, self.enemy, self._player_prev_state)
        self._enemy_prev_state = self.log_action_events(self.enemy, self.player, self._enemy_prev_state)
        self.spawn_projectiles()
        self.update_projectiles()
        self.resolve_body_collision()
        self.apply_hits()
        self._finalize_unresolved_attack(self.player, self.enemy, player_attack_before)
        self._finalize_unresolved_attack(self.enemy, self.player, enemy_attack_before)
        self.check_round_over()

    def log_action_events(self, fighter: Fighter, opponent: Fighter, prev_state: FighterState) -> FighterState:
        """Logs movement/crouch/jump/land transitions, reusing the same
        one-frame flags play_action_sounds() uses for the equivalent sounds.
        Returns the fighter's current state, to be passed back in as
        prev_state next frame."""
        state = fighter.state
        distance = abs(fighter.x - opponent.x)

        if fighter.jump_started_this_frame:
            action = "double_saut" if state == FighterState.DOUBLE_JUMP else "saut"
            self.combat_log.log(self.frame, fighter.name, action, distance)
        if fighter.landed_this_frame:
            self.combat_log.log(self.frame, fighter.name, "atterrissage", distance)
        if fighter.dash_started_this_frame:
            direction = "droite" if fighter.dash_direction > 0 else "gauche"
            self.combat_log.log(self.frame, fighter.name, "dash", distance, detail=f"direction={direction}")

        if state != prev_state:
            walk_states = (FighterState.WALK, FighterState.CROUCH_WALK)
            crouch_states = (FighterState.CROUCH, FighterState.CROUCH_WALK)
            was_walking = prev_state in walk_states
            is_walking = state in walk_states
            if is_walking and not was_walking:
                direction = "droite" if fighter.vel_x > 0 else "gauche" if fighter.vel_x < 0 else "?"
                self.combat_log.log(self.frame, fighter.name, "deplacement", distance, detail=f"direction={direction}")
            elif was_walking and not is_walking:
                self.combat_log.log(self.frame, fighter.name, "arret", distance)

            was_crouching = prev_state in crouch_states
            is_crouching = state in crouch_states
            if is_crouching and not was_crouching:
                self.combat_log.log(self.frame, fighter.name, "accroupi", distance)
            elif was_crouching and not is_crouching:
                self.combat_log.log(self.frame, fighter.name, "releve", distance)

        return state

    def _finalize_unresolved_attack(self, fighter: Fighter, opponent: Fighter, attack_ref) -> None:
        """Logs a melee attack that ended this frame without apply_hits()
        ever recording an outcome for it: either it never reached anyone
        (whiff, out of range) or the attacker got hit out of it first."""
        if attack_ref is None or fighter.attack is attack_ref or attack_ref.logged:
            return
        distance = abs(fighter.x - opponent.x)
        action = f"{attack_ref.definition.kind}_{attack_ref.effective_level}"
        if fighter.state == FighterState.HITSTUN:
            detail = f"{action} interrompue (touche subie)"
        else:
            detail = f"{action} manquee (hors de portee)"
        self.combat_log.log(self.frame, fighter.name, "attaque", distance, success=False, detail=detail)

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
        if fighter.dash_started_this_frame:
            self.play_common("jump_whoosh", volume=0.5)

    def spawn_projectiles(self) -> None:
        for fighter in (self.player, self.enemy):
            if not fighter.projectile_spawn_pending or not fighter.ranged_attack:
                continue
            opponent = self.enemy if fighter is self.player else self.player
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
            distance = abs(fighter.x - opponent.x)
            self.combat_log.log(self.frame, fighter.name, "tir_distance", distance,
                                 detail=f"{definition.display_name} stamina={fighter.stamina:.0f}")

    def update_projectiles(self) -> None:
        survivors: list[ActiveProjectile] = []
        for projectile in self.projectiles:
            projectile.elapsed += 1
            projectile.x += projectile.facing * projectile.definition.speed_px_per_second / FPS

            if projectile.x < LEFT_BOUND - 80 or projectile.x > RIGHT_BOUND + 80:
                if not projectile.logged:
                    distance = abs(projectile.owner.x - (self.enemy if projectile.owner is self.player else self.player).x)
                    self.combat_log.log(self.frame, projectile.owner.name, "tir_distance", distance,
                                         success=False, detail=f"{projectile.definition.display_name} manque (hors ecran)")
                continue  # flew off-stage

            target = self.enemy if projectile.owner is self.player else self.player
            hitbox = pygame.Rect(0, 0, projectile.definition.hitbox_w, projectile.definition.hitbox_h)
            hitbox.center = (round(projectile.x), round(projectile.y))
            distance = abs(projectile.owner.x - target.x)

            if not hitbox.colliderect(target.hurtbox):
                if not projectile.logged:
                    horizontal_overlap = hitbox.right > target.hurtbox.left and hitbox.left < target.hurtbox.right
                    if horizontal_overlap:
                        projectile.logged = True
                        self.combat_log.log(self.frame, projectile.owner.name, "tir_distance", distance, success=False,
                                             detail=f"{projectile.definition.display_name} esquive (accroupi)")
                        self.combat_log.log(self.frame, target.name, "esquive", distance,
                                             detail=f"{projectile.definition.display_name} (accroupi)")
                survivors.append(projectile)
                continue

            if target.state == FighterState.DOUBLE_JUMP and target.y <= GROUND_Y - PROJECTILE_AVOID_Y_DELTA:
                if not projectile.logged:
                    projectile.logged = True
                    self.combat_log.log(self.frame, projectile.owner.name, "tir_distance", distance, success=False,
                                         detail=f"{projectile.definition.display_name} esquive (salto)")
                    self.combat_log.log(self.frame, target.name, "esquive", distance,
                                         detail=f"{projectile.definition.display_name} (salto)")
                survivors.append(projectile)  # salto high enough: dodged
                continue

            result = target.receive_projectile_hit(projectile.owner, projectile.definition.damage)
            projectile.logged = True
            if result.landed:
                self.combat_log.log(self.frame, projectile.owner.name, "tir_distance", distance,
                                     success=not result.blocked, damage=0 if result.blocked else result.damage,
                                     detail=projectile.definition.display_name)
            if result.blocked:
                self.combat_log.log(self.frame, target.name, "blocage", distance, success=True,
                                     detail=f"{projectile.definition.display_name} stamina={target.stamina:.0f}")
            elif result.landed:
                self.combat_log.log(self.frame, target.name, "degats_recus", distance, damage=result.damage,
                                     detail=f"{projectile.definition.display_name} hitstun={HITSTUN_FRAMES / FPS:.2f}s")
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
            if not hitbox:
                continue
            if hitbox.colliderect(defender.hurtbox):
                candidates.append((attacker, defender, attacker.attack.definition, attacker.attack.effective_level))
            elif not attacker.attack.logged:
                # In range (horizontal overlap) but the defender's hurtbox
                # geometry (crouch/airborne) moved out of the attack's height
                # band — a genuine dodge, distinct from simply being too far
                # away (which never produces a hitbox in range at all).
                horizontal_overlap = hitbox.right > defender.hurtbox.left and hitbox.left < defender.hurtbox.right
                if horizontal_overlap:
                    attacker.attack.logged = True
                    distance = abs(attacker.x - defender.x)
                    action = f"{attacker.attack.definition.kind}_{attacker.attack.effective_level}"
                    self.combat_log.log(self.frame, attacker.name, "attaque", distance, success=False,
                                         detail=f"{action} esquivee (accroupi/saut)")
                    self.combat_log.log(self.frame, defender.name, "esquive", distance, detail=action)

        if not candidates:
            return

        # If both attacks connect on the same frame, both are applied. Otherwise,
        # the first active hit cancels the opponent's pending attack via hitstun.
        for attacker, defender, definition, hit_level in candidates:
            if attacker.attack:
                attacker.attack.already_hit = True
                attacker.attack.logged = True
            distance = abs(attacker.x - defender.x)
            action = f"{definition.kind}_{hit_level}"
            fatigue = attacker.attack.extra_recovery_frames if attacker.attack else 0
            fatigue_note = f" fatigue+{fatigue}f" if fatigue else ""
            result = defender.receive_attack(attacker, definition, hit_level)
            if result.landed:
                self.combat_log.log(self.frame, attacker.name, "attaque", distance,
                                     success=not result.blocked, damage=0 if result.blocked else result.damage,
                                     detail=f"{action} stamina={attacker.stamina:.0f}{fatigue_note}")
            if result.blocked:
                self.combat_log.log(self.frame, defender.name, "blocage", distance, success=True,
                                     detail=f"{action} stamina={defender.stamina:.0f}")
            elif result.landed:
                self.combat_log.log(self.frame, defender.name, "degats_recus", distance, damage=result.damage,
                                     detail=f"{action} hitstun={definition.hitstun_frames / FPS:.2f}s")
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
            if self.player.is_ko and self.enemy.is_ko:
                result_text = "Egalite (double KO)"
            elif self.enemy.is_ko:
                result_text = f"{self.player.name} gagne (KO)"
            else:
                result_text = f"{self.enemy.name} gagne (KO)"
            self._finalize_log(result_text)
            return
        if self.round_time_remaining <= 0:
            self.round_time_remaining = 0
            self.round_over = True
            if self.player.health > self.enemy.health:
                self.enemy.health = 0
                result_text = f"{self.player.name} gagne (temps ecoule)"
            elif self.enemy.health > self.player.health:
                self.player.health = 0
                result_text = f"{self.enemy.name} gagne (temps ecoule)"
            else:
                self.add_message("Temps écoulé : égalité")
                result_text = "Egalite (temps ecoule)"
            self._finalize_log(result_text)

    def add_message(self, message: str) -> None:
        self.messages.append(message)
        if len(self.messages) > 9:
            self.messages = self.messages[-9:]

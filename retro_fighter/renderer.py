"""Rendering helpers for the prototype."""
from __future__ import annotations

import pygame

from .config import (
    BODY_WIDTH,
    COLOR_BG,
    COLOR_BLACK,
    COLOR_FLOOR,
    COLOR_FLOOR_LINE,
    COLOR_GREEN,
    COLOR_HITBOX,
    COLOR_HURTBOX,
    COLOR_MUTED,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_SHADOW,
    COLOR_TEXT,
    COLOR_WHITE,
    COLOR_YELLOW,
    FPS,
    GROUND_Y,
    MAX_HEALTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .fighter import Fighter
from .projectiles import ActiveProjectile
from .sprites import FighterSpriteSet, ProjectileSprite
from .states import FighterState


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 52)
        self.title_font = pygame.font.Font(None, 72)
        self.small_font = pygame.font.Font(None, 19)
        self.sprite_sets = {
            "rose_kunoichi": FighterSpriteSet("rose_kunoichi"),
            "shinobi": FighterSpriteSet("shinobi"),
        }
        self.projectile_sprites = {
            "shuriken": ProjectileSprite("shuriken"),
            "rose_energy_ball": ProjectileSprite("rose_energy_ball"),
        }
        # Tracks (animation_key, elapsed_frames) per fighter, keyed by identity,
        # so a new animation always restarts at frame 0.
        self._anim_progress: dict[int, tuple[str, int]] = {}

    def draw(self, game: "Game") -> None:  # type: ignore[name-defined]
        self.draw_background()
        self.draw_fighter(game.player)
        self.draw_fighter(game.enemy)
        for projectile in game.projectiles:
            self.draw_projectile(projectile)
        if game.debug_hitboxes:
            self.draw_debug_boxes(game.player)
            self.draw_debug_boxes(game.enemy)
            for projectile in game.projectiles:
                self.draw_projectile_debug_box(projectile)
        self.draw_ui(game)
        if game.paused:
            self.draw_center_banner("PAUSE", "P pour reprendre")
        if game.round_over:
            winner = game.player.name if game.enemy.is_ko else game.enemy.name if game.player.is_ko else "Égalité"
            self.draw_center_banner(f"{winner} gagne", "R pour recommencer | 1-4 pour changer l'IA")

    def draw_menu(self, selected_index: int) -> None:
        self.draw_background()
        title = self.title_font.render("RETRO FIGHTER", True, COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 96)))

        subtitle = self.font.render("Prototype Python/Pygame - combat 2D à trois hauteurs", True, COLOR_MUTED)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 148)))

        modes = [
            ("1", "Sparring", "l'adversaire reste immobile"),
            ("2", "Facile", "lent, attaques prévisibles, mauvais blocages"),
            ("3", "Moyen", "gère la distance et bloque parfois juste"),
            ("4", "Difficile", "punit les whiffs, varie haut/milieu/bas"),
        ]
        start_y = 214
        for i, (key, name, desc) in enumerate(modes):
            selected = i == selected_index
            rect = pygame.Rect(244, start_y + i * 58, 536, 42)
            pygame.draw.rect(self.screen, COLOR_PURPLE if selected else (34, 37, 50), rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_WHITE if selected else COLOR_FLOOR_LINE, rect, 2, border_radius=8)
            label = self.font.render(f"{key}. {name}", True, COLOR_WHITE)
            self.screen.blit(label, (rect.x + 18, rect.y + 11))
            desc_surf = self.small_font.render(desc, True, COLOR_TEXT if selected else COLOR_MUTED)
            self.screen.blit(desc_surf, (rect.x + 154, rect.y + 14))

        controls = [
            "Contrôles : ←/→ déplacement | ↑/↓ hauteur | J poing | K pied | L blocage | Espace saut",
            "↓ seul au sol : accroupi | U : attaque à distance | Espace en l'air : salto (double saut)",
            "En match : 1-4 changer IA | R reset | H hitboxes | P pause | Échap quitter",
            "Appuie sur Entrée ou sur 1-4 pour lancer.",
        ]
        for i, line in enumerate(controls):
            surf = self.small_font.render(line, True, COLOR_MUTED)
            self.screen.blit(surf, surf.get_rect(center=(WINDOW_WIDTH // 2, 465 + i * 24)))

    def draw_background(self) -> None:
        self.screen.fill(COLOR_BG)
        # Retro parallax-like decorative panels.
        for i in range(0, WINDOW_WIDTH, 96):
            shade = 25 + (i // 96 % 2) * 8
            pygame.draw.rect(self.screen, (shade, shade + 2, shade + 10), (i, 0, 96, GROUND_Y))
        pygame.draw.circle(self.screen, (58, 48, 84), (WINDOW_WIDTH // 2, 164), 96)
        pygame.draw.rect(self.screen, COLOR_FLOOR, (0, GROUND_Y, WINDOW_WIDTH, WINDOW_HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, COLOR_FLOOR_LINE, (0, GROUND_Y), (WINDOW_WIDTH, GROUND_Y), 4)
        for x in range(-80, WINDOW_WIDTH + 80, 80):
            pygame.draw.line(self.screen, (48, 53, 69), (x, WINDOW_HEIGHT), (x + 120, GROUND_Y), 1)

    def animation_key(self, fighter: Fighter) -> str:
        if fighter.state == FighterState.ATTACK and fighter.attack:
            attack = fighter.attack
            # A low attack started from a crouch keeps the crouched pose
            # instead of popping up to the standing low-attack animation and
            # back down.
            if attack.started_crouching and attack.effective_level == "low" and attack.definition.kind in ("punch", "kick"):
                return f"crouch_{attack.definition.kind}_low"
            return f"{attack.definition.kind}_{attack.effective_level}"
        if fighter.state == FighterState.RANGED_ATTACK and fighter.ranged_attack:
            return "ranged_charge" if fighter.ranged_attack.is_charging else "ranged_throw"
        if fighter.state in (FighterState.BLOCK, FighterState.BLOCKSTUN):
            return f"block_{fighter.block_level}"
        # CROUCH/CROUCH_WALK/DOUBLE_JUMP/idle/walk/jump/hitstun/ko all resolve
        # directly since their enum value already matches the animation key.
        return fighter.state.value

    def draw_fighter(self, fighter: Fighter) -> None:
        rect = fighter.rect
        # Shadow
        shadow = pygame.Rect(0, 0, BODY_WIDTH + 30, 14)
        shadow.center = (rect.centerx, GROUND_Y + 7)
        pygame.draw.ellipse(self.screen, COLOR_SHADOW, shadow)

        anim_key = self.animation_key(fighter)
        tracked_key, elapsed = self._anim_progress.get(id(fighter), (None, 0))
        elapsed = 0 if tracked_key != anim_key else elapsed + 1
        self._anim_progress[id(fighter)] = (anim_key, elapsed)

        sprite_set = self.sprite_sets[fighter.fighter_id]
        frame = sprite_set.get_frame(anim_key, elapsed, FPS, flip=fighter.facing == -1)
        frame_rect = frame.get_rect()
        frame_rect.x = round(fighter.x - sprite_set.anchor[0])
        frame_rect.y = round(fighter.y - sprite_set.anchor[1])
        self.screen.blit(frame, frame_rect)

        # Name/state label above character
        state_text = fighter.state.value
        if fighter.state == FighterState.ATTACK and fighter.attack:
            state_text = fighter.attack.definition.label
        elif fighter.state == FighterState.RANGED_ATTACK and fighter.ranged_attack:
            state_text = fighter.ranged_attack.definition.display_name
        label = self.small_font.render(state_text, True, fighter.color)
        self.screen.blit(label, label.get_rect(center=(frame_rect.centerx, frame_rect.top - 6)))

    def draw_projectile(self, projectile: ActiveProjectile) -> None:
        sprite = self.projectile_sprites[projectile.definition.projectile_id]
        frame = sprite.get_frame(projectile.elapsed, FPS, flip=projectile.facing == -1)
        self.screen.blit(frame, frame.get_rect(center=(round(projectile.x), round(projectile.y))))

    def draw_projectile_debug_box(self, projectile: ActiveProjectile) -> None:
        hitbox = pygame.Rect(0, 0, projectile.definition.hitbox_w, projectile.definition.hitbox_h)
        hitbox.center = (round(projectile.x), round(projectile.y))
        pygame.draw.rect(self.screen, COLOR_HITBOX, hitbox, 2)

    def draw_debug_boxes(self, fighter: Fighter) -> None:
        pygame.draw.rect(self.screen, COLOR_HURTBOX, fighter.hurtbox, 1)
        hitbox = fighter.get_attack_hitbox()
        if hitbox:
            pygame.draw.rect(self.screen, COLOR_HITBOX, hitbox, 2)

    def draw_ui(self, game: "Game") -> None:  # type: ignore[name-defined]
        self.draw_health_bar(game.player, 42, 28, align="left")
        self.draw_health_bar(game.enemy, WINDOW_WIDTH - 42 - 392, 28, align="right")

        timer = max(0, int(game.round_time_remaining))
        timer_surf = self.big_font.render(str(timer), True, COLOR_WHITE)
        pygame.draw.rect(self.screen, COLOR_BLACK, (WINDOW_WIDTH // 2 - 46, 20, 92, 58), border_radius=8)
        self.screen.blit(timer_surf, timer_surf.get_rect(center=(WINDOW_WIDTH // 2, 50)))

        mode_text = f"IA : {game.ai_mode.upper()}"
        mode_surf = self.font.render(mode_text, True, COLOR_YELLOW)
        self.screen.blit(mode_surf, mode_surf.get_rect(center=(WINDOW_WIDTH // 2, 90)))

        controls = "J poing | K pied | L blocage | ↓ accroupi | U distance | Espace saut/salto | H hitboxes"
        control_surf = self.small_font.render(controls, True, COLOR_MUTED)
        self.screen.blit(control_surf, control_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 24)))

        # Event log
        y = 112
        for msg in game.messages[-5:]:
            surf = self.small_font.render(msg, True, COLOR_TEXT)
            self.screen.blit(surf, (42, y))
            y += 20

    def draw_health_bar(self, fighter: Fighter, x: int, y: int, align: str) -> None:
        width = 392
        height = 26
        ratio = max(0.0, fighter.health / MAX_HEALTH)
        outer = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, COLOR_BLACK, outer.inflate(8, 8), border_radius=5)
        pygame.draw.rect(self.screen, (68, 40, 40), outer, border_radius=4)
        fill_w = int(width * ratio)
        if align == "right":
            fill = pygame.Rect(x + width - fill_w, y, fill_w, height)
        else:
            fill = pygame.Rect(x, y, fill_w, height)
        color = COLOR_GREEN if ratio > 0.45 else COLOR_YELLOW if ratio > 0.20 else COLOR_RED
        pygame.draw.rect(self.screen, color, fill, border_radius=4)
        name = self.font.render(f"{fighter.name}  {fighter.health}/{MAX_HEALTH}", True, COLOR_WHITE)
        if align == "right":
            self.screen.blit(name, name.get_rect(topright=(x + width, y + height + 8)))
        else:
            self.screen.blit(name, (x, y + height + 8))

    def draw_center_banner(self, title: str, subtitle: str) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(0, 0, 540, 150)
        box.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        pygame.draw.rect(self.screen, COLOR_BLACK, box, border_radius=14)
        pygame.draw.rect(self.screen, COLOR_WHITE, box, 2, border_radius=14)
        title_surf = self.big_font.render(title, True, COLOR_WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(box.centerx, box.y + 54)))
        sub_surf = self.font.render(subtitle, True, COLOR_MUTED)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(box.centerx, box.y + 103)))

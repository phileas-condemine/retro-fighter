"""Rendering helpers for the prototype."""
from __future__ import annotations

import pygame

from .config import (
    BODY_WIDTH,
    COLOR_BG,
    COLOR_BLACK,
    COLOR_BLUE,
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
    DASH_TRAIL_ALPHA_DECAY,
    DASH_TRAIL_INITIAL_ALPHA,
    DASH_TRAIL_MAX_COPIES,
    FPS,
    GROUND_Y,
    MAX_HEALTH,
    MAX_STAMINA,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .fighter import Fighter
from .projectiles import ActiveProjectile
from .sprites import FIGHTERS_DIR, FighterSpriteSet, ProjectileSprite
from .stages import StageBackgrounds
from .states import FighterState


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 52)
        self.title_font = pygame.font.Font(None, 72)
        self.small_font = pygame.font.Font(None, 19)
        # Full sprite sets are preloaded per variant so switching graphics
        # (see set_graphics_variant) is instant, with no load stutter
        # mid-match. The "hd" packs are an early VLM-generated proof of
        # concept with fewer animations than "ld" (see FighterSpriteSet's
        # docstring); missing keys fall back to idle automatically. "v2"
        # (Blender-rigged, see blender/README.md) is newer still and so far
        # only exists for some fighters -- built conditionally per fighter_id
        # so a character without a v2 pack yet (e.g. shinobi) doesn't crash
        # Renderer construction; draw_fighter falls back to "hd"/"ld" for those.
        self.sprite_sets = {
            "ld": {
                "rose_kunoichi": FighterSpriteSet("rose_kunoichi", "ld"),
                "shinobi": FighterSpriteSet("shinobi", "ld"),
            },
            "hd": {
                "rose_kunoichi": FighterSpriteSet("rose_kunoichi", "hd"),
                "shinobi": FighterSpriteSet("shinobi", "hd"),
            },
            "v2": {
                fighter_id: FighterSpriteSet(fighter_id, "v2")
                for fighter_id in ("rose_kunoichi", "shinobi")
                if (FIGHTERS_DIR / "v2" / fighter_id / "manifest.json").exists()
            },
        }
        # Which sprite_sets key draw_fighter reads from -- "ld", "hd", or
        # "v2". The in-game G key cycles through all three (see
        # Game.cycle_graphics_variant); set_graphics_variant is also the hook
        # a headless script/test uses to force one directly.
        self.graphics_variant = "ld"
        self.projectile_sprites = {
            "shuriken": ProjectileSprite("shuriken"),
            "rose_energy_ball": ProjectileSprite("rose_energy_ball"),
        }
        self.stage_backgrounds = StageBackgrounds()
        self.stage_index = 0
        # Tracks (animation_key, elapsed_frames) per fighter, keyed by identity,
        # so a new animation always restarts at frame 0.
        self._anim_progress: dict[int, tuple[str, int]] = {}
        # Dash kinetic-blur trail: a list of (ghost_surface, topleft_pos) per
        # fighter, keyed by identity. Each ghost is a private alpha-faded
        # copy of a past frame (never the pack's shared/cached surface, so
        # mutating its alpha can't bleed into other draws) -- see
        # _update_dash_trail.
        self._dash_trail: dict[int, list[tuple[pygame.Surface, tuple[int, int]]]] = {}

    def set_stage_index(self, stage_index: int) -> None:
        self.stage_index = self.stage_backgrounds.normalize_index(stage_index)

    def stage_name(self) -> str:
        return self.stage_backgrounds.get_name(self.stage_index)

    def set_graphics_variant(self, variant: str) -> None:
        """Select which sprite_sets key draw_fighter reads from ("ld", "hd",
        or "v2") -- used by both the in-game G-key cycle (Game.
        cycle_graphics_variant) and headless validation/testing scripts."""
        self.graphics_variant = variant

    def draw_backdrop(self, rect: pygame.Rect, alpha: int = 185, color: tuple[int, int, int] = COLOR_BG, radius: int = 10) -> None:
        """Semi-transparent panel behind text, so it stays readable over the
        photographic arena backgrounds (plain colors/gradients underneath the
        old procedural backdrop never needed this)."""
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*color, alpha), panel.get_rect(), border_radius=radius)
        self.screen.blit(panel, rect.topleft)

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

    def draw_menu(self, selected_index: int, demo_mode: bool = False, graphics_variant: str = "ld") -> None:
        self.draw_background()
        title = self.title_font.render("RETRO FIGHTER", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 96))

        subtitle = self.font.render("Prototype Python/Pygame - combat 2D à trois hauteurs", True, COLOR_MUTED)
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 148))

        mode_label = "Démo : IA vs IA" if demo_mode else "Joueur vs IA"
        graphics_label = {"ld": "LD", "hd": "HD (bêta)", "v2": "V2 (bêta)"}.get(graphics_variant, graphics_variant)
        demo_surf = self.font.render(
            f"Mode : {mode_label} (Tab)   |   Graphismes : {graphics_label} (G)",
            True, COLOR_YELLOW if (demo_mode or graphics_variant != "ld") else COLOR_MUTED,
        )
        demo_rect = demo_surf.get_rect(center=(WINDOW_WIDTH // 2, 178))

        header_backdrop = title_rect.union(subtitle_rect).union(demo_rect).inflate(56, 28)
        self.draw_backdrop(header_backdrop)
        self.screen.blit(title, title_rect)
        self.screen.blit(subtitle, subtitle_rect)
        self.screen.blit(demo_surf, demo_rect)

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
            "Contrôles : Gauche/Droite déplacement (double-tap = dash) | Haut/Bas hauteur | Q/A poing | S pied | D blocage | Espace saut",
            "Bas seul au sol : accroupi | F : attaque à distance | Espace en l'air : salto (double saut)",
            "En match : 1-4 changer IA | Tab mode démo | G graphismes HD/LD | C changer perso | R reset | H hitboxes | P pause | Échap quitter",
            "Appuie sur Entrée ou sur 1-4 pour lancer.",
        ]
        control_surfaces = [self.small_font.render(line, True, COLOR_MUTED) for line in controls]
        control_rects = [
            surf.get_rect(center=(WINDOW_WIDTH // 2, 465 + i * 24)) for i, surf in enumerate(control_surfaces)
        ]
        footer_backdrop = control_rects[0].unionall(control_rects[1:]).inflate(40, 20)
        self.draw_backdrop(footer_backdrop)
        for surf, rect in zip(control_surfaces, control_rects):
            self.screen.blit(surf, rect)

    def draw_background(self) -> None:
        if self.stage_backgrounds.draw(self.screen, self.stage_index):
            return

        # Fallback: original procedural backdrop, used if the arena manifest
        # or an arena image is missing (see retro_fighter/stages.py).
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

    def animation_key(self, fighter: Fighter, sprite_set: FighterSpriteSet) -> str:
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
        if fighter.state == FighterState.DASH:
            # Only packs with a real dash pose (v2) get it; LD/HD never had
            # one, so the walk cycle read at normal speed over a fast-moving
            # body (the existing fallback) keeps reading as a dash/slide.
            return "dash" if "dash" in sprite_set.animations else "walk"
        # CROUCH/CROUCH_WALK/DOUBLE_JUMP/idle/walk/jump/hitstun/ko all resolve
        # directly since their enum value already matches the animation key.
        return fighter.state.value

    def draw_fighter(self, fighter: Fighter) -> None:
        rect = fighter.rect
        # Shadow
        shadow = pygame.Rect(0, 0, BODY_WIDTH + 30, 14)
        shadow.center = (rect.centerx, GROUND_Y + 7)
        pygame.draw.ellipse(self.screen, COLOR_SHADOW, shadow)

        # Fall back down the quality chain (v2 -> hd -> ld) for a fighter
        # that doesn't have the requested variant yet (e.g. graphics_variant
        # == "v2" but this fighter has no v2 pack, like shinobi currently).
        for variant in (self.graphics_variant, "hd", "ld"):
            variant_sets = self.sprite_sets[variant]
            if fighter.fighter_id in variant_sets:
                break
        sprite_set = variant_sets[fighter.fighter_id]
        anim_key = self.animation_key(fighter, sprite_set)
        tracked_key, elapsed = self._anim_progress.get(id(fighter), (None, 0))
        elapsed = 0 if tracked_key != anim_key else elapsed + 1
        self._anim_progress[id(fighter)] = (anim_key, elapsed)

        frame = sprite_set.get_frame(anim_key, elapsed, FPS, flip=fighter.facing == -1)
        frame_rect = frame.get_rect()
        frame_rect.x = round(fighter.x - sprite_set.anchor[0])
        frame_rect.y = round(fighter.y - sprite_set.anchor[1])

        self._update_dash_trail(fighter, frame, frame_rect)
        for ghost, pos in self._dash_trail.get(id(fighter), ()):
            self.screen.blit(ghost, pos)

        self.screen.blit(frame, frame_rect)

        # Name/state label above character
        state_text = fighter.state.value
        if fighter.state == FighterState.ATTACK and fighter.attack:
            state_text = fighter.attack.definition.label
        elif fighter.state == FighterState.RANGED_ATTACK and fighter.ranged_attack:
            state_text = fighter.ranged_attack.definition.display_name
        label = self.small_font.render(state_text, True, fighter.color)
        self.screen.blit(label, label.get_rect(center=(frame_rect.centerx, frame_rect.top - 6)))

    def _update_dash_trail(self, fighter: Fighter, frame: pygame.Surface, frame_rect: pygame.Rect) -> None:
        """Kinetic-blur trail: while dashing (grounded or airborne), leave a
        handful of alpha-fading afterimages of the sprite behind. Ghosts keep
        fading and get dropped once fully transparent even after the dash
        itself ends, so the trail tapers off instead of cutting out."""
        ghosts = self._dash_trail.get(id(fighter), [])
        faded: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for ghost, pos in ghosts:
            alpha = ghost.get_alpha() - DASH_TRAIL_ALPHA_DECAY
            if alpha > 0:
                ghost.set_alpha(alpha)
                faded.append((ghost, pos))

        if fighter.state == FighterState.DASH:
            # A private copy, never the pack's shared/cached surface --
            # set_alpha() on a cached frame would mutate it for every other
            # draw that reuses the same cached id() (see sprites.py's
            # _flipped_cache and the crossfade note it mirrors).
            new_ghost = frame.copy()
            new_ghost.set_alpha(DASH_TRAIL_INITIAL_ALPHA)
            faded.append((new_ghost, frame_rect.topleft))

        if len(faded) > DASH_TRAIL_MAX_COPIES:
            faded = faded[-DASH_TRAIL_MAX_COPIES:]

        if faded:
            self._dash_trail[id(fighter)] = faded
        elif id(fighter) in self._dash_trail:
            del self._dash_trail[id(fighter)]

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

        demo_suffix = " | DÉMO (IA vs IA)" if game.demo_mode else ""
        variant_suffix = f" | {game.graphics_variant.upper()}" if game.graphics_variant != "ld" else ""
        mode_text = f"IA : {game.ai_mode.upper()}{demo_suffix}{variant_suffix} | {self.stage_name()}"
        mode_surf = self.font.render(mode_text, True, COLOR_YELLOW)
        mode_rect = mode_surf.get_rect(center=(WINDOW_WIDTH // 2, 90))
        self.draw_backdrop(mode_rect.inflate(28, 14))
        self.screen.blit(mode_surf, mode_rect)

        if game.demo_mode:
            controls = "Mode démo : IA vs IA | Tab repasser en Joueur vs IA | R reset | P pause | H hitboxes"
        else:
            controls = "Q/A poing | S pied | D blocage | Bas accroupi | F distance | Espace saut/salto | C changer perso | H hitboxes"
        control_surf = self.small_font.render(controls, True, COLOR_MUTED)
        control_rect = control_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 24))
        self.draw_backdrop(control_rect.inflate(28, 14))
        self.screen.blit(control_surf, control_rect)

        # Event log (pushed down from its old y=112 to clear the stamina bar
        # added under each health bar).
        messages = game.messages[-5:]
        if messages:
            log_top = 128
            line_surfaces = [self.small_font.render(msg, True, COLOR_TEXT) for msg in messages]
            log_rect = pygame.Rect(42, log_top, max(s.get_width() for s in line_surfaces), len(line_surfaces) * 20 - 4)
            self.draw_backdrop(log_rect.inflate(24, 16))
            y = log_top
            for surf in line_surfaces:
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

        # Stamina bar: thinner, directly under health. Spent by attacking
        # and by absorbing a blocked hit; low stamina doesn't show here as a
        # separate warning color, its effect (slower recovery) is on the
        # fighter that owns it, not something the opponent needs flagged.
        stamina_y = y + height + 6
        stamina_height = 10
        stamina_ratio = max(0.0, fighter.stamina / MAX_STAMINA)
        stamina_outer = pygame.Rect(x, stamina_y, width, stamina_height)
        pygame.draw.rect(self.screen, COLOR_BLACK, stamina_outer.inflate(6, 6), border_radius=4)
        pygame.draw.rect(self.screen, (36, 44, 62), stamina_outer, border_radius=3)
        stamina_fill_w = int(width * stamina_ratio)
        if align == "right":
            stamina_fill = pygame.Rect(x + width - stamina_fill_w, stamina_y, stamina_fill_w, stamina_height)
        else:
            stamina_fill = pygame.Rect(x, stamina_y, stamina_fill_w, stamina_height)
        pygame.draw.rect(self.screen, COLOR_BLUE, stamina_fill, border_radius=3)

        name = self.font.render(f"{fighter.name}  {fighter.health}/{MAX_HEALTH}", True, COLOR_WHITE)
        name_y = stamina_y + stamina_height + 8
        if align == "right":
            self.screen.blit(name, name.get_rect(topright=(x + width, name_y)))
        else:
            self.screen.blit(name, (x, name_y))

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

"""Scripted playthrough that drives the real game loop (same physics/hit/sound
pipeline as Game.update()) with programmatic Command objects instead of a
keyboard, to (re)generate docs/media/screenshot.png and gameplay_demo.gif.

Demonstrates every core mechanic: punch, kick, block (negating a real
incoming hit), crouch, ranged attack, and a double-jump salto crossing over
the opponent.

Usage (from the project root, inside the venv):
    python -m pip install pillow   # one-off, not a runtime dependency
    python scripts/record_demo.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame
from PIL import Image

from retro_fighter.game import Game
from retro_fighter.input_manager import Command
from retro_fighter.config import FPS, ROUND_TIME_SECONDS

game = Game()
game.start_match("sparring")  # enemy AI stays idle; we script both fighters explicitly

frames = []          # PIL Images, sampled every SAMPLE_EVERY sim frames
FRAME_SCALE = (368, 207)   # downscaled for a reasonably small GIF (arena backgrounds compress
SAMPLE_EVERY = 4            # much worse than the old flat-color backdrop, keep this modest)
GIF_COLORS = 160           # shared adaptive palette; photographic arenas need fewer, richer
                           # colors more than a big flat palette to keep the file size sane


def step(player_cmd: "Command", enemy_cmd: "Command" = None) -> None:
    if enemy_cmd is None:
        enemy_cmd = Command()
    game.frame += 1
    game.round_time_remaining = ROUND_TIME_SECONDS - (game.frame - game.round_start_frame) / FPS
    game.player.update(player_cmd, game.enemy)
    game.enemy.update(enemy_cmd, game.player)
    game.play_action_sounds(game.player)
    game.play_action_sounds(game.enemy)
    game.spawn_projectiles()
    game.update_projectiles()
    game.resolve_body_collision()
    game.apply_hits()
    game.check_round_over()


def render_and_capture() -> None:
    game.renderer.draw(game)
    pygame.display.flip()
    if game.frame % SAMPLE_EVERY == 0:
        raw = pygame.image.tostring(game.screen, "RGB")
        img = Image.frombytes("RGB", game.screen.get_size(), raw)
        frames.append(img.resize(FRAME_SCALE, Image.LANCZOS))


def hold(player_cmd: "Command", n_frames: int, enemy_cmd: "Command" = None, label: str = "") -> None:
    for _ in range(n_frames):
        step(player_cmd, enemy_cmd)
        render_and_capture()
    if label:
        print(f"[{game.frame}] {label} health P={game.player.health} E={game.enemy.health} "
              f"state P={game.player.state} E={game.enemy.state}")


def save_screenshot(path: Path) -> None:
    game.renderer.draw(game)
    pygame.display.flip()
    pygame.image.save(game.screen, str(path))
    print("Saved screenshot", path, "at frame", game.frame)


def place(player_x: float, enemy_x: float) -> None:
    """Reposition both fighters (keeping health/round state) so each scripted
    beat starts from a known, reliable distance instead of drifting from
    whatever the previous beat's walking happened to leave behind. Also clears
    any still-in-flight projectile so it can't sneak into a later scene and
    land a surprise hit (e.g. a slow projectile connecting mid-salto)."""
    game.player.x = player_x
    game.enemy.x = enemy_x
    game.player.vel_x = 0.0
    game.enemy.vel_x = 0.0
    game.player.update_facing(game.enemy)
    game.enemy.update_facing(game.player)
    game.projectiles = []


# ---------------------------------------------------------------------------
# Scene setup
game.messages = ["Retro Fighter - demo"]
place(260, 500)
hold(Command(), 20, label="intro idle")

# --- Punch (mid) -------------------------------------------------------------
place(300, 360)  # ~60px gap: within punch mid's 58px range
hold(Command(attack="punch", aim_level="mid"), 1)
hold(Command(), 22, label="punch mid")

# --- Kick (mid) ---------------------------------------------------------------
place(300, 380)  # kick has more range than punch
hold(Command(attack="kick", aim_level="mid"), 1)
hold(Command(), 30, label="kick mid")

# --- Crouch + crouch-walk ----------------------------------------------------
place(260, 700)  # plenty of room, no accidental attack overlap
hold(Command(aim_level="low"), 25, label="crouch idle")
hold(Command(aim_level="low", move_axis=1), 20, label="crouch walk forward")
hold(Command(), 10)  # stand back up (neutral aim releases crouch)

# --- Block: enemy throws a real punch, player blocks mid --------------------
place(300, 360)
game.enemy.start_attack("punch", "mid")  # scripted opponent action (sparring AI is idle otherwise)
hold(Command(block=True, aim_level="mid"), 30, label="block")

# --- Ranged attack ------------------------------------------------------------
# Gap tuned so the projectile actually connects within this scene: it spawns
# 37 frames after the button press (charge_frames=24 + spawn_frame=13, see
# ProjectileDefinition/ActiveRangedAttack), then closes ~220px at 455px/s.
place(400, 620)
hold(Command(ranged_attack=True), 1)
hold(Command(), 40, label="ranged attack charge+throw")  # spawns at frame 37: already in flight here

OUT_DIR = PROJECT_ROOT / "docs" / "media"
OUT_DIR.mkdir(parents=True, exist_ok=True)
save_screenshot(OUT_DIR / "screenshot.png")  # projectile mid-flight

hold(Command(), 25, label="ranged attack flight/impact")

# --- Double jump salto crossing over the opponent ----------------------------
# Gap tuned to what DOUBLE_JUMP_AIR_CONTROL_SPEED reliably clears (see
# SPECIFICATION.md 4.7 / the earlier crossover-fix regression tests).
place(500, 650)
approach = 1
hold(Command(jump=True), 1)          # no lateral input on the jump-press frame itself:
hold(Command(), 14)                  # (mixing move_axis into the same frame as a jump/attack
hold(Command(jump=True), 1)          # trigger races update_movement's on_ground check, per
hold(Command(move_axis=approach), 50, label="salto crossing over")  # Fighter.update()'s fall-through ordering)
hold(Command(), 15, label="settle after crossover")

crossed = (game.player.x > game.enemy.x) if approach == 1 else (game.player.x < game.enemy.x)
print("Final: player.x=%.1f enemy.x=%.1f (crossed=%s)" % (game.player.x, game.enemy.x, crossed))

# ---------------------------------------------------------------------------
# A shared, size-capped palette (built from one representative frame and
# reused for all of them) compresses far better across a whole animation of
# photographic arena backgrounds than PIL's per-call default.
gif_path = OUT_DIR / "gameplay_demo.gif"
palette_source = frames[len(frames) // 2].quantize(colors=GIF_COLORS, method=Image.MEDIANCUT)
quantized = [f.quantize(palette=palette_source, dither=Image.FLOYDSTEINBERG) for f in frames]
quantized[0].save(
    gif_path,
    save_all=True,
    append_images=quantized[1:],
    duration=int(1000 / (FPS / SAMPLE_EVERY)),
    loop=0,
    optimize=True,
)
print("Saved", gif_path, "with", len(frames), "frames")
print("GIF size:", os.path.getsize(gif_path) / 1024, "KB")

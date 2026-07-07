"""Web entrypoint for Pygbag (WebAssembly build).

Pygbag requires a main.py at the project root with an async def main()
containing `await asyncio.sleep(0)` inside the loop, so the browser's event
loop gets control back between frames. All actual game logic lives in
retro_fighter/game.py, shared with the desktop entrypoint (run_game.py) via
Game.tick().
"""
import asyncio

import pygame

from retro_fighter.game import Game


async def main() -> None:
    game = Game()
    while game.tick():
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

"""Chronological per-fight combat log, written to logs/ once a round ends.

One file per fight, named with the wall-clock time it started. Meant to be
read top-to-bottom by a human to reconstruct exactly what happened and when
— not a machine-parsing format, though the key=value-ish fixed-width fields
make it easy enough to grep/parse too.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import FPS

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


@dataclass
class LogEntry:
    frame: int
    time_s: float
    actor: str
    action: str
    distance_px: float
    success: Optional[bool]
    damage: int
    detail: str = ""

    def format(self) -> str:
        success_str = "-" if self.success is None else ("OK" if self.success else "ECHEC")
        line = (
            f"[t={self.time_s:7.2f}s] {self.actor:<8} {self.action:<14} "
            f"distance={self.distance_px:6.1f}px succes={success_str:<6} degats={self.damage:>3}"
        )
        if self.detail:
            line += f"  ({self.detail})"
        return line


class CombatLogger:
    """Collects events for the fight currently in progress.

    start() resets the buffer for a new fight; write() flushes it to a
    timestamped file under logs/. Every public method is a no-op-safe
    wrapper — a fight that never started (e.g. the very first reset_round()
    call from the menu) or a write failure (read-only filesystem, sandboxed
    web build) never raises, it just skips logging.
    """

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []
        self.round_start_frame = 0
        self.meta: dict = {}
        self._file_timestamp = ""

    def start(
        self,
        *,
        ai_mode: str,
        stage_name: str,
        demo_mode: bool,
        player_name: str,
        enemy_name: str,
        player_fighter_id: str,
        enemy_fighter_id: str,
        round_start_frame: int,
    ) -> None:
        self.entries = []
        self.round_start_frame = round_start_frame
        now = datetime.datetime.now()
        self._file_timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.meta = {
            "started_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_mode": ai_mode,
            "stage_name": stage_name,
            "demo_mode": demo_mode,
            "player_name": player_name,
            "enemy_name": enemy_name,
            "player_fighter_id": player_fighter_id,
            "enemy_fighter_id": enemy_fighter_id,
        }

    def log(
        self,
        frame: int,
        actor: str,
        action: str,
        distance_px: float,
        success: Optional[bool] = None,
        damage: int = 0,
        detail: str = "",
    ) -> None:
        if not self.meta:
            return  # no fight in progress (shouldn't normally happen, but stay safe)
        time_s = (frame - self.round_start_frame) / FPS
        self.entries.append(LogEntry(frame, time_s, actor, action, distance_px, success, damage, detail))

    def write(self, *, result_text: str, duration_s: float) -> Optional[Path]:
        if not self.meta or not self.entries:
            return None
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            path = LOGS_DIR / f"combat_{self._file_timestamp}.log"
            header = [
                "=== Retro Fighter - journal de combat ===",
                f"Date               : {self.meta['started_at']}",
                f"Niveau IA          : {self.meta['ai_mode']}",
                f"Mode               : {'Demo (IA vs IA)' if self.meta['demo_mode'] else 'Joueur vs IA'}",
                f"Arene              : {self.meta['stage_name']}",
                f"Combattants        : {self.meta['player_name']} ({self.meta['player_fighter_id']}) "
                f"vs {self.meta['enemy_name']} ({self.meta['enemy_fighter_id']})",
                f"Duree              : {duration_s:.2f}s",
                f"Resultat           : {result_text}",
                "",
            ]
            body = [entry.format() for entry in self.entries]
            path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
            return path
        except Exception as exc:  # noqa: BLE001 - never let a log write crash the game (e.g. read-only FS on web)
            print(f"[combat_log] Impossible d'ecrire le journal de combat: {exc}")
            return None

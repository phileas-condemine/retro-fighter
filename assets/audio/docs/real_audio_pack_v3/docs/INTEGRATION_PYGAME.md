# Intégration Pygame

## Chargement simple

```python
import glob
import json
import random
import pygame
from pathlib import Path

class AudioBank:
    def __init__(self, root: str, mapping_path: str):
        self.root = Path(root)
        self.sounds = {}
        with open(mapping_path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)
        self._load_common()
        self._load_fighters()

    def _load_paths(self, paths):
        loaded = []
        for pattern in paths:
            matches = glob.glob(str(self.root / pattern))
            for path in matches:
                try:
                    loaded.append(pygame.mixer.Sound(path))
                except pygame.error:
                    print(f"Cannot load audio: {path}")
        return loaded

    def _load_common(self):
        self.sounds["common"] = {}
        for event, paths in self.mapping["common"].items():
            self.sounds["common"][event] = self._load_paths(paths)

    def _load_fighters(self):
        self.sounds["fighters"] = {}
        for fighter, events in self.mapping["fighters"].items():
            self.sounds["fighters"][fighter] = {}
            for event, paths in events.items():
                self.sounds["fighters"][fighter][event] = self._load_paths(paths)

    def play_common(self, event, volume=0.7):
        choices = self.sounds["common"].get(event, [])
        if choices:
            sound = random.choice(choices)
            sound.set_volume(volume)
            sound.play()

    def play_voice(self, fighter_id, event, volume=0.75):
        choices = self.sounds["fighters"].get(fighter_id, {}).get(event, [])
        if choices:
            sound = random.choice(choices)
            sound.set_volume(volume)
            sound.play()
```

## Exemples d’appel gameplay

```python
# coup de poing lancé
audio.play_voice(attacker.audio_id, "punch")
audio.play_common("attack_whoosh", volume=0.35)

# coup de poing qui touche
audio.play_common("punch_hit")
audio.play_voice(defender.audio_id, "hurt")

# coup bloqué
audio.play_common("block_impact")
audio.play_voice(defender.audio_id, "block", volume=0.45)

# double saut / salto
audio.play_voice(fighter.audio_id, "double_jump")
audio.play_common("double_jump_whoosh", volume=0.45)

# projectile shinobi
audio.play_voice("shinobi_male", "projectile_throw")
audio.play_common("shuriken_throw")

# projectile rose_kunoichi
audio.play_voice("rose_kunoichi", "projectile_throw")
audio.play_common("rose_energy_charge")
# puis au moment exact de l'émission :
audio.play_common("rose_energy_throw")
```

## Note volume

Pour éviter la fatigue auditive :

- voix : 0.55 à 0.75 ;
- impacts : 0.45 à 0.70 ;
- projectiles énergie : 0.25 à 0.50 ;
- whooshes : 0.25 à 0.45.

# Contrat des packs de sprites (`assets/fighters/`)

Ce document décrit ce que `retro_fighter/sprites.py` (`FighterSpriteSet`)
attend réellement d'un pack, pour que n'importe quelle nouvelle source
(pack HD généré par VLM, pack v2 rendu par Blender, ...) puisse s'y
brancher sans surprise. C'est le contrat à valider avec
`tools/sprites/validate_manifest.py`.

## Layout sur disque

```text
assets/fighters/<variante>/<fighter_id>/
  manifest.json
  frames/
    idle_000.png
    idle_001.png
    ...
  extension_manifest*.json   # optionnel, un ou plusieurs
```

- `<variante>` : `ld` (dessiné à la main, pack complet), `hd` (généré par
  VLM, proof of concept incomplet), `v2` (à venir, pipeline Blender).
- `<fighter_id>` : `rose_kunoichi` ou `shinobi` — **stable entre les
  variantes**. C'est aussi la clé utilisée pour l'audio
  (`AUDIO_CHARACTER_ALIASES` dans `audio.py`) et les projectiles
  (`FIGHTER_PROJECTILE_ID` dans `projectiles.py`) : une nouvelle variante
  graphique d'un personnage existant ne doit jamais introduire un nouveau
  `fighter_id`, seulement un nouveau dossier de variante.
- `sheets/`, `source_sheets/`, `source_cells_chroma/`, `extras/`,
  `previews/`, `docs/` : tolérés à côté (utiles pour la traçabilité/preview),
  mais **jamais lus par le moteur** — seuls `manifest.json`,
  `extension_manifest*.json` et les fichiers listés dans leurs `frames`
  comptent à l'exécution. Les exclure du build web (`pygbag.ini`) si lourds.

## `manifest.json`

```json
{
  "anchor": { "x": 128, "y": 214 },
  "animations": {
    "idle": {
      "frames": ["frames/idle_000.png", "frames/idle_001.png"],
      "fps": 8,
      "loop": true
    }
  }
}
```

Champs lus par le loader (`FighterSpriteSet.__init__`) :

- `anchor.x` / `anchor.y` : point d'ancrage en pixels dans le canevas de
  chaque frame, aligné sur les pieds au sol du personnage. **Doit être
  identique entre toutes les variantes d'un même `fighter_id`** (aujourd'hui
  `128, 214` pour LD et HD) — sinon le personnage saute visuellement en
  hauteur au moment de basculer de variante.
- `animations.<clé>.frames` : liste de chemins relatifs au dossier du pack,
  dans l'ordre de lecture. Toutes les images doivent faire la **même
  taille** entre elles (256×256 aujourd'hui) et être en **RGBA**
  (transparence réelle, pas de fond de couleur).
- `animations.<clé>.fps` : vitesse de lecture propre à cette animation.
- `animations.<clé>.loop` : `true` boucle indéfiniment, `false` se fige sur
  la dernière frame une fois terminée.

Tout autre champ (`gameplay_state_hint`, `startup_frames`, `active_frames`,
`recovery_frames`, `sheet`, ...) est ignoré par le loader — libre à un pack
de les inclure pour la traçabilité/tooling externe, mais ils n'ont aucun
effet en jeu. Les timings de combat réels vivent dans
`retro_fighter/attacks.py`, pas dans le manifest (voir section 10 du plan v2
pour la réconciliation future via `animation_events.json`, pas encore
implémentée).

## `extension_manifest*.json`

Un ou plusieurs fichiers nommés `extension_manifest*.json` (glob, tri
alphabétique si plusieurs) à côté de `manifest.json`, chacun avec :

```json
{
  "animations_to_add": {
    "crouch_idle": { "frames": ["frames/crouch_idle_000.png"], "fps": 6, "loop": true }
  }
}
```

Fusionnés dans le même dict que `manifest.json`'s `animations` — clé en
commun = la dernière lue gagne. Utilisé aujourd'hui par LD (crouch/salto/
distance en un fichier, attaques basses accroupies dans un second) et par
HD shinobi (`extension_manifest_high_actions.json`, actions hautes ajoutées
par-dessus le pack de base).

## Clés d'animation attendues par le moteur

Le jeu appelle `Renderer.animation_key()` pour choisir la clé selon l'état
du combattant. Liste complète actuellement utilisée (voir
`retro_fighter/states.py`, `renderer.py`) :

```text
idle, walk, jump, double_jump_salto,
crouch_idle, crouch_walk,
punch_high, punch_mid, punch_low,
kick_high, kick_mid, kick_low,
crouch_punch_low, crouch_kick_low,
block_high, block_mid, block_low,
hitstun, ko,
ranged_charge, ranged_throw
```

Un pack **n'a pas besoin de toutes les couvrir** : `FighterSpriteSet.get_frame()`
retombe automatiquement sur `idle` pour toute clé absente (voir le pack HD,
qui n'a pas encore `punch_low`/`kick_low`/`block_low`). Un pack incomplet ne
plante donc jamais le jeu — il dégrade juste la lisibilité de l'animation
manquante jusqu'à ce qu'elle soit produite.

`dash` est une 21e clé optionnelle, en dehors des 20 ci-dessus : contrairement
aux autres, elle n'a **pas** de repli automatique via `get_frame()` — c'est
`Renderer.animation_key()` lui-même qui vérifie `"dash" in sprite_set.animations`
avant de la retourner, et retombe sur `walk` sinon. LD n'a toujours pas de
pose de dash dédiée (la marche jouée à vitesse normale sur un corps qui se
déplace vite suffisait à lire comme un dash) ; HD (`rose_kunoichi`) et v2 en
fournissent désormais une réelle.

## Validation

```bash
python tools/sprites/validate_manifest.py assets/fighters/ld/rose_kunoichi
python tools/sprites/validate_manifest.py assets/fighters/hd/shinobi
```

Vérifie : JSON valide, toutes les frames listées existent sur disque, toutes
les frames d'une même animation ont la même taille, `anchor` présent,
`fps`/`loop` du bon type, pas de chemin absolu. Voir `--help` pour les
options (comparaison à un pack de référence pour lister les clés
manquantes, utile pour évaluer la complétude d'un pack HD/v2 face à LD).

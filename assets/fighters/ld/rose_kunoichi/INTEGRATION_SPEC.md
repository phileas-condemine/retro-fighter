# Spécification d'intégration — Rose Kunoichi

## Objectif

Ajouter un deuxième personnage au prototype en conservant exactement la même interface d'animation que le pack `shinobi`.

## Identifiant

```text
rose_kunoichi
```

## Convention de fichiers

Les frames individuelles sont dans :

```text
assets/fighters/rose_kunoichi/frames/
```

Les spritesheets horizontales sont dans :

```text
assets/fighters/rose_kunoichi/sheets/
```

## Mapping d'état recommandé

```python
if fighter.state == "IDLE":
    anim = "idle"
elif fighter.state == "WALK":
    anim = "walk"
elif fighter.state == "JUMP":
    anim = "jump"
elif fighter.state == "ATTACK":
    anim = f"{fighter.attack.kind}_{fighter.attack.height}"
elif fighter.state == "BLOCK":
    anim = f"block_{fighter.block_height}"
elif fighter.state == "HITSTUN":
    anim = "hitstun"
elif fighter.state == "KO":
    anim = "ko"
```

## Ancre

Frame 256 × 256. Ancre au sol :

```json
{"x": 128, "y": 214}
```

Le rendu doit blitter la frame à :

```python
screen_x = fighter.x - anchor_x
screen_y = fighter.ground_y - anchor_y - fighter.vertical_offset
```

## Timings gameplay

Les timings présents dans `manifest.json` sont indicatifs :

- poings : startup 2 frames, actif frames 2–3, recovery 1 frame ;
- pieds : startup 3 frames, actif frames 3–4, recovery 2 frames.

Pour la première intégration, garde les hitboxes abstraites déjà définies dans le moteur.

## Production suivante

Étapes recommandées :

1. brancher ce pack au renderer existant ;
2. tester lisibilité des trois hauteurs d'attaque ;
3. ajuster `anchor_y` si le pied glisse visuellement ;
4. ajouter hurtboxes/hitboxes par frame ;
5. séparer les effets d'attaque en sprites indépendants.

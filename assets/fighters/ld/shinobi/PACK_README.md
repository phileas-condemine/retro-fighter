# Crimson Shinobi — 60-frame sprite pack

Ce dossier contient un premier pack exploitable pour intégrer un personnage `shinobi` dans le prototype Pygame.

## Contenu

- `frames/` : 60 frames PNG transparentes nommées par animation.
- `sheets/` : une spritesheet horizontale par animation.
- `manifest.json` : description des animations, FPS, boucle, ancrage et timings gameplay indicatifs.
- `shinobi_atlas_10x6.png` : atlas transparent de toutes les frames en grille 10 × 6.
- `atlas_index.json` : coordonnées des frames dans l'atlas.
- `preview_contact_sheet.png` : aperçu rapide avec labels.

## Dimensions

- Taille frame : `256 × 256` px
- Fond : transparent
- Orientation source : personnage tourné vers la droite
- Ancre recommandée : `x=128`, `y=214`

## Animations

| Animation | Frames | Boucle | Usage |
|---|---:|---:|---|
| idle | 4 | oui | attente |
| walk | 6 | oui | marche avant/arrière |
| jump | 4 | non | saut |
| punch_high | 5 | non | coup de poing haut |
| punch_mid | 5 | non | coup de poing moyen |
| punch_low | 5 | non | coup de poing bas |
| kick_high | 7 | non | coup de pied haut |
| kick_mid | 7 | non | coup de pied moyen |
| kick_low | 7 | non | coup de pied bas |
| block_high | 1 | oui | garde haute |
| block_mid | 1 | oui | garde moyenne |
| block_low | 1 | oui | garde basse |
| hitstun | 2 | non | personnage touché |
| ko | 5 | non | chute / KO |

## Intégration Pygame

Principe minimal : charger le `manifest.json`, charger les images listées dans `frames`, puis choisir l'animation selon l'état du combattant.

Exemple de mapping :

```python
if fighter.state == "IDLE":
    anim = "idle"
elif fighter.state == "WALK":
    anim = "walk"
elif fighter.state == "JUMP":
    anim = "jump"
elif fighter.state == "ATTACK":
    anim = f"{fighter.attack.kind}_{fighter.attack.height}"  # punch_high, kick_low, etc.
elif fighter.state == "BLOCK":
    anim = f"block_{fighter.block_height}"
elif fighter.state == "HITSTUN":
    anim = "hitstun"
elif fighter.state == "KO":
    anim = "ko"
```

Pour afficher le personnage côté gauche/droite, garde les images source tournées vers la droite et utilise :

```python
frame = pygame.transform.flip(frame, True, False)
```

quand le personnage doit regarder vers la gauche.

## Limite importante

Ce pack est une première base stylisée et cohérente techniquement. Pour atteindre une qualité vraiment proche d'un jeu de combat commercial, il faudra ensuite :

1. redessiner ou régénérer les frames avec un pipeline image dédié plus contrôlé ;
2. harmoniser précisément les volumes du personnage entre frames ;
3. définir les hitboxes/hurtboxes par frame ;
4. ajouter des frames d'anticipation, d'impact et de recovery plus détaillées ;
5. créer des effets séparés pour impacts, poussière, dash et projectiles.

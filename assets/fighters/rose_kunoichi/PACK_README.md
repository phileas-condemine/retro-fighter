# Rose Kunoichi — 60-frame sprite pack

Pack de 60 frames PNG transparentes pour un second personnage jouable/adversaire du prototype Pygame.

## Direction artistique

Personnage original : kunoichi adulte, cheveux roses, allure sportive, tenue de combat inspirée d'un maillot une-pièce / combinaison athlétique, grandes bottes et appuis puissants. Le design vise une évocation arcade fighting game sans reproduire un personnage existant.

## Contenu

- `assets/fighters/rose_kunoichi/frames/` : 60 frames PNG transparentes.
- `assets/fighters/rose_kunoichi/sheets/` : spritesheets horizontales par animation.
- `assets/fighters/rose_kunoichi/manifest.json` : animations, FPS, boucle, ancre, timings gameplay indicatifs.
- `assets/fighters/rose_kunoichi/rose_kunoichi_atlas_10x6.png` : atlas transparent 10 × 6.
- `assets/fighters/rose_kunoichi/atlas_index.json` : coordonnées des frames dans l'atlas.
- `assets/fighters/rose_kunoichi/preview_contact_sheet.png` : aperçu rapide avec labels.
- `docs/INTEGRATION_SPEC.md` : notes d'intégration.

## Dimensions

- Frame : 256 × 256 px
- Fond : transparent
- Orientation source : vers la droite
- Ancre : x=128, y=214

## Animations

| Animation | Frames | Boucle |
|---|---:|---:|
| idle | 4 | oui |
| walk | 6 | oui |
| jump | 4 | non |
| punch_high | 5 | non |
| punch_mid | 5 | non |
| punch_low | 5 | non |
| kick_high | 7 | non |
| kick_mid | 7 | non |
| kick_low | 7 | non |
| block_high | 1 | oui |
| block_mid | 1 | oui |
| block_low | 1 | oui |
| hitstun | 2 | non |
| ko | 5 | non |

## Utilisation dans le jeu

Utilise `fighter_id = "rose_kunoichi"` puis charge le `manifest.json`. La convention d'animation est identique au pack `shinobi`, donc le même renderer peut afficher les deux personnages.

Pour inverser le personnage :

```python
frame = pygame.transform.flip(frame, True, False)
```

## Limite

Ce pack est prêt pour prototypage et intégration gameplay. Pour une qualité commerciale, il faudra un pipeline d'animation plus contrôlé, des retouches frame par frame, puis des hitboxes/hurtboxes dessinées précisément par animation.

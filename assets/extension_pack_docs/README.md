# Retro Fighter — Extension Pack V2: accroupissement, attaque à distance, salto


## V2 — correction importante

Cette V2 corrige les poses accroupies et le salto : les personnages ne sont plus comprimés ou rétrécis. Les frames `crouch_idle`, `crouch_walk` et `double_jump_salto` sont reconstruites avec des poses articulées : genoux pliés pour l'accroupissement, corps regroupé pour le salto. Voir `docs/POSE_CORRECTION_NOTES.md`.

Ce pack ajoute des assets et une documentation pour trois évolutions du prototype Pygame :

1. **Accroupissement** : le personnage divise visuellement sa hauteur par deux et peut se déplacer lentement accroupi.
2. **Attaque à distance** :
   - `shinobi` lance un **shuriken** à hauteur d'épaules ;
   - `rose_kunoichi` lance une **boule d'énergie rose** à hauteur d'épaules.
3. **Double saut / salto** : le second saut est rendu par une animation de salto, suffisamment haute pour passer au-dessus d'un projectile à hauteur d'épaules.

Le pack est conçu comme une **extension** des deux packs de 60 frames déjà intégrés. Il ne remplace pas les frames existantes.

## Structure

```text
assets/
  fighters/
    shinobi/
      extension_frames/
      extension_sheets/
      extension_manifest.json
      extension_preview_contact_sheet.png
    rose_kunoichi/
      extension_frames/
      extension_sheets/
      extension_manifest.json
      extension_preview_contact_sheet.png

  projectiles/
    shuriken/
      frames/
      sheets/
      projectile_manifest.json
    rose_energy_ball/
      frames/
      sheets/
      projectile_manifest.json
    projectiles_preview_contact_sheet.png

code/
  extension_gameplay_patch.py

docs/
  INTEGRATION_GAMEPLAY.md
  MANIFEST_MERGE.md
  ASSET_LIST.md
  TUNING_NOTES.md

extension_pack_manifest.json
```

## Animations ajoutées par personnage

| Animation | Frames | Boucle | Usage |
|---|---:|---:|---|
| `crouch_idle` | 4 | oui | accroupi immobile |
| `crouch_walk` | 6 | oui | petit déplacement accroupi |
| `ranged_charge` | 4 | non | préparation/charge de l'attaque à distance |
| `ranged_throw` | 6 | non | projection à hauteur d'épaules |
| `double_jump_salto` | 6 | non | second saut / salto |

## Projectiles

| Projectile | Personnage | Frames | Vitesse conseillée | Dégâts conseillés |
|---|---|---:|---:|---:|
| `shuriken` | shinobi | 8 | 560 px/s | 8 |
| `rose_energy_ball` | rose_kunoichi | 8 | 455 px/s | 10 |

## Prévisualisations

- `assets/fighters/shinobi/extension_preview_contact_sheet.png`
- `assets/fighters/rose_kunoichi/extension_preview_contact_sheet.png`
- `assets/projectiles/projectiles_preview_contact_sheet.png`

## Intégration rapide

Lis `docs/INTEGRATION_GAMEPLAY.md`, puis ajoute les cas suivants à ton resolver d'animation :

```python
CROUCH                 -> "crouch_idle"
CROUCH_WALK            -> "crouch_walk"
RANGED_STARTUP         -> "ranged_charge"
RANGED_ACTIVE_RECOVERY -> "ranged_throw"
DOUBLE_JUMP            -> "double_jump_salto"
```

Pour le gameplay, le fichier `code/extension_gameplay_patch.py` donne un squelette prêt à adapter.

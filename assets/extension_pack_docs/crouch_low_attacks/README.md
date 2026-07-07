# Retro Fighter — Extension Pack: attaques basses depuis accroupissement

Ce pack ajoute deux animations supplémentaires par personnage :

- `crouch_punch_low` : coup de poing bas lancé depuis la position accroupie ;
- `crouch_kick_low` : coup de pied bas / balayage lancé depuis la position accroupie.

Le but est d'éviter une incohérence visuelle fréquente : si le joueur maintient `↓` et lance une attaque basse, le personnage ne doit pas repasser visuellement en attaque basse debout. Il doit rester compact, genoux pliés, et attaquer depuis la posture accroupie.

## Contenu

```text
assets/fighters/shinobi/
  extension_frames/
  extension_sheets/
  extension_manifest.json
  crouch_low_attacks_preview_contact_sheet.png

assets/fighters/rose_kunoichi/
  extension_frames/
  extension_sheets/
  extension_manifest.json
  crouch_low_attacks_preview_contact_sheet.png

docs/
  INTEGRATION_CROUCH_LOW_ATTACKS.md
  MANIFEST_MERGE.md
  HITBOX_TUNING.md

code/
  crouch_low_attacks_patch.py
```

## Convention graphique

- frame 256 × 256 px ;
- fond transparent ;
- orientation source vers la droite ;
- ancre aux pieds : `x=128`, `y=214` ;
- aucune compression verticale du sprite ;
- les poses sont articulées : genoux pliés, bassin bas, attaque déclenchée depuis le crouch.

## Règle d'intégration

```python
if fighter.is_crouching and attack.height == "low":
    if attack.kind == "punch":
        animation = "crouch_punch_low"
    elif attack.kind == "kick":
        animation = "crouch_kick_low"
```

Pour toutes les autres attaques, tu peux conserver la logique actuelle.

# Retro Fighter — Arena Extension Pack V1

Ce pack ajoute **5 arènes 16:9** prêtes à intégrer dans le repo GitHub `phileas-condemine/retro-fighter`.

Les images sont fournies en deux versions :

- `assets/backgrounds/arenas/*.png` : version **1024 × 576**, directement compatible avec la configuration actuelle du jeu.
- `assets/backgrounds/originals/*.png` : version source **1672 × 941**, utile pour recadrage, retouche, upscale ou futures résolutions.

## Arènes incluses

1. `snow_mountain_temple` — Temple des neiges
2. `haunted_castle_courtyard` — Château hanté
3. `infernal_volcano_gate` — Porte infernale
4. `bamboo_temple_garden` — Jardin du bambou
5. `moonlit_desert_ruins` — Ruines lunaires

## Installation rapide

Depuis la racine du repo `retro-fighter` :

```bash
# 1. Copier les assets
cp -R assets/backgrounds ./assets/

# 2. Ajouter le module optionnel
cp code/stages.py ./retro_fighter/stages.py

# 3. Appliquer les snippets de code
# Voir docs/INTEGRATION_REPO.md
```

Sous Windows, copier simplement le dossier `assets/backgrounds/` dans le dossier `assets/` du repo, puis copier `code/stages.py` dans `retro_fighter/stages.py`.

## Aperçu

Voir :

```text
arena_contact_sheet.png
assets/backgrounds/previews/arena_contact_sheet.png
```

## Licence / usage

Images générées dans la conversation ChatGPT pour le prototype Retro Fighter. Aucune banque d'images tierce n'est incluse. Pour un jeu public/commercial, faire une revue qualité/licence séparée et éviter toute ressemblance trop directe avec une propriété intellectuelle existante.
